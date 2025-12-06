"""
Threat Intelligence API Endpoints
Manual lookups and enrichment
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user, require_analyst
from app.schemas.auth import CurrentUser
from app.api.v1.settings import get_setting
from app.services.threat_intelligence import get_threat_intel_service
from app.services.geoip_service import get_geoip_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class IPLookupRequest(BaseModel):
    """IP address lookup request"""
    ip_address: str = Field(..., description="IP address to lookup")


class HashLookupRequest(BaseModel):
    """File hash lookup request"""
    file_hash: str = Field(..., description="File hash (MD5, SHA1, or SHA256)")


class IPLookupResponse(BaseModel):
    """IP address lookup response"""
    ip: str
    is_malicious: bool
    max_threat_score: int
    sources: dict
    geoip: Optional[dict] = None


class HashLookupResponse(BaseModel):
    """File hash lookup response"""
    hash: str
    is_malicious: bool
    max_threat_score: int
    sources: dict


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/lookup/ip", response_model=IPLookupResponse)
async def lookup_ip_address(
    request: IPLookupRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Lookup IP address with threat intelligence sources
    (analyst or admin)
    """
    try:
        # Check if threat intel is enabled
        threat_intel_enabled = get_setting(db, 'threat_intel_enabled', False)
        if not threat_intel_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Threat intelligence is not enabled"
            )

        # Get API keys
        virustotal_api_key = get_setting(db, 'virustotal_api_key')
        abuseipdb_api_key = get_setting(db, 'abuseipdb_api_key')

        if not virustotal_api_key and not abuseipdb_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No threat intelligence API keys configured"
            )

        # Create threat intel service
        threat_intel = get_threat_intel_service(
            virustotal_api_key=virustotal_api_key,
            abuseipdb_api_key=abuseipdb_api_key
        )

        # Lookup IP
        result = threat_intel.check_ip(request.ip_address, db)

        # Add GeoIP information
        geoip_service = get_geoip_service()
        if geoip_service.is_available():
            geoip_data = geoip_service.lookup_ip(request.ip_address)
            result['geoip'] = geoip_data

        logger.info(f"Threat intel lookup for IP {request.ip_address} by {current_user.username}: "
                   f"Malicious={result['is_malicious']}, Score={result['max_threat_score']}")

        return IPLookupResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up IP: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to lookup IP: {str(e)}"
        )


@router.post("/lookup/hash", response_model=HashLookupResponse)
async def lookup_file_hash(
    request: HashLookupRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Lookup file hash with threat intelligence sources
    (analyst or admin)
    """
    try:
        # Check if threat intel is enabled
        threat_intel_enabled = get_setting(db, 'threat_intel_enabled', False)
        if not threat_intel_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Threat intelligence is not enabled"
            )

        # Get VirusTotal API key (primary source for file hashes)
        virustotal_api_key = get_setting(db, 'virustotal_api_key')
        if not virustotal_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VirusTotal API key not configured"
            )

        # Create threat intel service
        threat_intel = get_threat_intel_service(
            virustotal_api_key=virustotal_api_key
        )

        # Lookup hash
        result = threat_intel.check_file_hash(request.file_hash, db)

        logger.info(f"Threat intel lookup for hash {request.file_hash[:16]}... by {current_user.username}: "
                   f"Malicious={result['is_malicious']}, Score={result['max_threat_score']}")

        return HashLookupResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up file hash: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to lookup file hash: {str(e)}"
        )


@router.get("/geoip/{ip_address}")
async def lookup_geoip(
    ip_address: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Lookup IP address geolocation with GeoIP
    """
    try:
        geoip_service = get_geoip_service()

        if not geoip_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GeoIP service is not available. GeoLite2 database not found."
            )

        result = geoip_service.lookup_ip(ip_address)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"IP {ip_address} not found in GeoIP database (possibly private/reserved IP)"
            )

        logger.info(f"GeoIP lookup for {ip_address} by {current_user.username}: "
                   f"{result.get('country_name')}, {result.get('city')}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up GeoIP: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to lookup GeoIP: {str(e)}"
        )


@router.get("/status")
async def get_enrichment_status(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get status of enrichment services
    """
    threat_intel_enabled = get_setting(db, 'threat_intel_enabled', False)
    virustotal_api_key = get_setting(db, 'virustotal_api_key')
    abuseipdb_api_key = get_setting(db, 'abuseipdb_api_key')

    geoip_service = get_geoip_service()

    return {
        'threat_intelligence': {
            'enabled': threat_intel_enabled,
            'virustotal': bool(virustotal_api_key),
            'abuseipdb': bool(abuseipdb_api_key)
        },
        'geoip': {
            'available': geoip_service.is_available(),
            'db_path': geoip_service.db_path if geoip_service.is_available() else None
        }
    }
