"""
Threat Intelligence Service
Integration with VirusTotal, AbuseIPDB, and other threat intel sources
"""

import logging
import requests
import hashlib
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json

from app.models.integrations import ThreatIntelligence

logger = logging.getLogger(__name__)


class ThreatIntelService:
    """Unified Threat Intelligence Service"""

    def __init__(
        self,
        virustotal_api_key: Optional[str] = None,
        abuseipdb_api_key: Optional[str] = None,
        cache_ttl_hours: int = 24
    ):
        self.virustotal_api_key = virustotal_api_key
        self.abuseipdb_api_key = abuseipdb_api_key
        self.cache_ttl_hours = cache_ttl_hours

        self.virustotal_enabled = bool(virustotal_api_key)
        self.abuseipdb_enabled = bool(abuseipdb_api_key)

    # ========================================================================
    # VIRUSTOTAL INTEGRATION
    # ========================================================================

    def check_ip_virustotal(self, ip_address: str, db: Session) -> Optional[Dict]:
        """
        Check IP address reputation with VirusTotal
        Returns cached result or fetches fresh data
        """
        if not self.virustotal_enabled:
            return None

        try:
            # Check cache first
            cached = self._get_cached_intel(ip_address, 'ip', 'virustotal', db)
            if cached:
                return cached

            # Fetch from VirusTotal API
            url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip_address}"
            headers = {
                'x-apikey': self.virustotal_api_key
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Parse results
                stats = data.get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                malicious_count = stats.get('malicious', 0)
                suspicious_count = stats.get('suspicious', 0)

                is_malicious = malicious_count > 0
                threat_score = min(100, (malicious_count + suspicious_count) * 10)

                # Extract categories
                categories = []
                categories_data = data.get('data', {}).get('attributes', {}).get('categories', {})
                for vendor, category in categories_data.items():
                    if category and category not in categories:
                        categories.append(category)

                # Cache result
                intel_data = {
                    'is_malicious': is_malicious,
                    'threat_score': threat_score,
                    'malicious_count': malicious_count,
                    'suspicious_count': suspicious_count,
                    'categories': categories,
                    'raw': data
                }

                self._cache_intel(
                    indicator=ip_address,
                    indicator_type='ip',
                    source='virustotal',
                    is_malicious=is_malicious,
                    threat_score=threat_score,
                    categories=categories,
                    raw_data=data,
                    db=db
                )

                logger.info(f"VirusTotal: IP {ip_address} - Malicious: {is_malicious}, Score: {threat_score}")
                return intel_data

            elif response.status_code == 404:
                # IP not found in VT database - not necessarily bad
                intel_data = {
                    'is_malicious': False,
                    'threat_score': 0,
                    'message': 'IP not found in VirusTotal database'
                }
                return intel_data

            else:
                logger.warning(f"VirusTotal API returned {response.status_code}: {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"VirusTotal API timeout for IP {ip_address}")
            return None
        except Exception as e:
            logger.error(f"Error checking IP with VirusTotal: {e}", exc_info=True)
            return None

    def check_file_hash_virustotal(self, file_hash: str, db: Session) -> Optional[Dict]:
        """
        Check file hash reputation with VirusTotal
        Supports MD5, SHA1, SHA256
        """
        if not self.virustotal_enabled:
            return None

        try:
            # Check cache
            cached = self._get_cached_intel(file_hash, 'file_hash', 'virustotal', db)
            if cached:
                return cached

            # Fetch from VirusTotal API
            url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
            headers = {
                'x-apikey': self.virustotal_api_key
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                stats = data.get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                malicious_count = stats.get('malicious', 0)
                suspicious_count = stats.get('suspicious', 0)

                is_malicious = malicious_count > 0
                threat_score = min(100, (malicious_count + suspicious_count) * 10)

                # Extract malware families
                tags = data.get('data', {}).get('attributes', {}).get('tags', [])

                intel_data = {
                    'is_malicious': is_malicious,
                    'threat_score': threat_score,
                    'malicious_count': malicious_count,
                    'suspicious_count': suspicious_count,
                    'tags': tags,
                    'raw': data
                }

                self._cache_intel(
                    indicator=file_hash,
                    indicator_type='file_hash',
                    source='virustotal',
                    is_malicious=is_malicious,
                    threat_score=threat_score,
                    tags=tags,
                    raw_data=data,
                    db=db
                )

                logger.info(f"VirusTotal: Hash {file_hash[:16]}... - Malicious: {is_malicious}, Score: {threat_score}")
                return intel_data

            elif response.status_code == 404:
                intel_data = {
                    'is_malicious': False,
                    'threat_score': 0,
                    'message': 'File hash not found in VirusTotal database'
                }
                return intel_data

            else:
                logger.warning(f"VirusTotal API returned {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error checking file hash with VirusTotal: {e}", exc_info=True)
            return None

    # ========================================================================
    # ABUSEIPDB INTEGRATION
    # ========================================================================

    def check_ip_abuseipdb(self, ip_address: str, db: Session) -> Optional[Dict]:
        """
        Check IP address reputation with AbuseIPDB
        """
        if not self.abuseipdb_enabled:
            return None

        try:
            # Check cache
            cached = self._get_cached_intel(ip_address, 'ip', 'abuseipdb', db)
            if cached:
                return cached

            # Fetch from AbuseIPDB API
            url = "https://api.abuseipdb.com/api/v2/check"
            headers = {
                'Key': self.abuseipdb_api_key,
                'Accept': 'application/json'
            }
            params = {
                'ipAddress': ip_address,
                'maxAgeInDays': 90,
                'verbose': True
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                result_data = data.get('data', {})
                abuse_confidence_score = result_data.get('abuseConfidenceScore', 0)
                total_reports = result_data.get('totalReports', 0)
                is_whitelisted = result_data.get('isWhitelisted', False)

                # AbuseIPDB considers score > 25 as suspicious, > 75 as highly malicious
                is_malicious = abuse_confidence_score > 25 and not is_whitelisted

                # Extract categories
                categories = []
                reports = result_data.get('reports', [])
                for report in reports[:5]:  # Last 5 reports
                    report_categories = report.get('categories', [])
                    categories.extend(report_categories)

                categories = list(set(categories))  # Unique categories

                intel_data = {
                    'is_malicious': is_malicious,
                    'threat_score': abuse_confidence_score,
                    'total_reports': total_reports,
                    'is_whitelisted': is_whitelisted,
                    'categories': categories,
                    'raw': data
                }

                self._cache_intel(
                    indicator=ip_address,
                    indicator_type='ip',
                    source='abuseipdb',
                    is_malicious=is_malicious,
                    threat_score=abuse_confidence_score,
                    categories=categories,
                    raw_data=data,
                    db=db
                )

                logger.info(f"AbuseIPDB: IP {ip_address} - Score: {abuse_confidence_score}, Reports: {total_reports}")
                return intel_data

            else:
                logger.warning(f"AbuseIPDB API returned {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"AbuseIPDB API timeout for IP {ip_address}")
            return None
        except Exception as e:
            logger.error(f"Error checking IP with AbuseIPDB: {e}", exc_info=True)
            return None

    # ========================================================================
    # UNIFIED LOOKUP
    # ========================================================================

    def check_ip(self, ip_address: str, db: Session) -> Dict:
        """
        Check IP address with all available threat intel sources
        Returns combined results
        """
        results = {
            'ip': ip_address,
            'is_malicious': False,
            'max_threat_score': 0,
            'sources': {}
        }

        # Check VirusTotal
        if self.virustotal_enabled:
            vt_result = self.check_ip_virustotal(ip_address, db)
            if vt_result:
                results['sources']['virustotal'] = vt_result
                if vt_result.get('is_malicious'):
                    results['is_malicious'] = True
                if vt_result.get('threat_score', 0) > results['max_threat_score']:
                    results['max_threat_score'] = vt_result.get('threat_score', 0)

        # Check AbuseIPDB
        if self.abuseipdb_enabled:
            abuse_result = self.check_ip_abuseipdb(ip_address, db)
            if abuse_result:
                results['sources']['abuseipdb'] = abuse_result
                if abuse_result.get('is_malicious'):
                    results['is_malicious'] = True
                if abuse_result.get('threat_score', 0) > results['max_threat_score']:
                    results['max_threat_score'] = abuse_result.get('threat_score', 0)

        return results

    def check_file_hash(self, file_hash: str, db: Session) -> Dict:
        """
        Check file hash with all available threat intel sources
        """
        results = {
            'hash': file_hash,
            'is_malicious': False,
            'max_threat_score': 0,
            'sources': {}
        }

        # Check VirusTotal (only source that supports file hashes for now)
        if self.virustotal_enabled:
            vt_result = self.check_file_hash_virustotal(file_hash, db)
            if vt_result:
                results['sources']['virustotal'] = vt_result
                if vt_result.get('is_malicious'):
                    results['is_malicious'] = True
                if vt_result.get('threat_score', 0) > results['max_threat_score']:
                    results['max_threat_score'] = vt_result.get('threat_score', 0)

        return results

    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================

    def _get_cached_intel(
        self,
        indicator: str,
        indicator_type: str,
        source: str,
        db: Session
    ) -> Optional[Dict]:
        """Get cached threat intelligence data"""
        try:
            cache_entry = db.query(ThreatIntelligence).filter(
                ThreatIntelligence.Indicator == indicator,
                ThreatIntelligence.Source == source
            ).first()

            if cache_entry:
                # Check if cache is still valid
                if cache_entry.CacheExpiresAt and cache_entry.CacheExpiresAt > datetime.utcnow():
                    logger.debug(f"Cache HIT for {indicator} ({source})")

                    # Update check count
                    cache_entry.CheckCount += 1
                    db.commit()

                    # Parse cached data
                    raw_data = json.loads(cache_entry.RawData) if cache_entry.RawData else {}
                    categories = json.loads(cache_entry.Categories) if cache_entry.Categories else []
                    tags = json.loads(cache_entry.Tags) if cache_entry.Tags else []

                    return {
                        'is_malicious': cache_entry.IsMalicious,
                        'threat_score': cache_entry.ThreatScore,
                        'categories': categories,
                        'tags': tags,
                        'cached': True,
                        'cache_age_hours': (datetime.utcnow() - cache_entry.LastChecked).total_seconds() / 3600
                    }
                else:
                    logger.debug(f"Cache EXPIRED for {indicator} ({source})")

            return None

        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None

    def _cache_intel(
        self,
        indicator: str,
        indicator_type: str,
        source: str,
        is_malicious: bool,
        threat_score: int,
        categories: Optional[List] = None,
        tags: Optional[List] = None,
        raw_data: Optional[Dict] = None,
        db: Session = None
    ):
        """Cache threat intelligence data"""
        try:
            # Check if entry exists
            cache_entry = db.query(ThreatIntelligence).filter(
                ThreatIntelligence.Indicator == indicator,
                ThreatIntelligence.Source == source
            ).first()

            cache_expires = datetime.utcnow() + timedelta(hours=self.cache_ttl_hours)

            if cache_entry:
                # Update existing entry
                cache_entry.IndicatorType = indicator_type
                cache_entry.IsMalicious = is_malicious
                cache_entry.ThreatScore = threat_score
                cache_entry.Categories = json.dumps(categories) if categories else None
                cache_entry.Tags = json.dumps(tags) if tags else None
                cache_entry.RawData = json.dumps(raw_data) if raw_data else None
                cache_entry.LastChecked = datetime.utcnow()
                cache_entry.CheckCount += 1
                cache_entry.CacheExpiresAt = cache_expires
            else:
                # Create new entry
                cache_entry = ThreatIntelligence(
                    Indicator=indicator,
                    IndicatorType=indicator_type,
                    Source=source,
                    IsMalicious=is_malicious,
                    ThreatScore=threat_score,
                    Categories=json.dumps(categories) if categories else None,
                    Tags=json.dumps(tags) if tags else None,
                    RawData=json.dumps(raw_data) if raw_data else None,
                    FirstSeen=datetime.utcnow(),
                    LastChecked=datetime.utcnow(),
                    CheckCount=1,
                    CacheExpiresAt=cache_expires
                )
                db.add(cache_entry)

            db.commit()
            logger.debug(f"Cached threat intel for {indicator} ({source})")

        except Exception as e:
            logger.error(f"Error caching threat intel: {e}", exc_info=True)
            db.rollback()


# Singleton instance
_threat_intel_service: Optional[ThreatIntelService] = None


def get_threat_intel_service(
    virustotal_api_key: Optional[str] = None,
    abuseipdb_api_key: Optional[str] = None,
    cache_ttl_hours: int = 24
) -> ThreatIntelService:
    """Get or create threat intelligence service instance"""
    global _threat_intel_service

    # Always create new instance with current settings
    _threat_intel_service = ThreatIntelService(
        virustotal_api_key=virustotal_api_key,
        abuseipdb_api_key=abuseipdb_api_key,
        cache_ttl_hours=cache_ttl_hours
    )

    return _threat_intel_service
