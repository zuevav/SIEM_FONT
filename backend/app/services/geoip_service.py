"""
GeoIP Enrichment Service
Uses MaxMind GeoLite2 database for IP geolocation
"""

import logging
from typing import Optional, Dict
import geoip2.database
import geoip2.errors
import os

logger = logging.getLogger(__name__)


class GeoIPService:
    """GeoIP lookup service using MaxMind GeoLite2"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize GeoIP service
        db_path: Path to GeoLite2-City.mmdb file
        """
        if db_path is None:
            # Default paths to check
            possible_paths = [
                '/usr/share/GeoIP/GeoLite2-City.mmdb',
                '/var/lib/GeoIP/GeoLite2-City.mmdb',
                './GeoLite2-City.mmdb',
                '/app/data/GeoLite2-City.mmdb'
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    db_path = path
                    break

        self.db_path = db_path
        self.reader = None

        if db_path and os.path.exists(db_path):
            try:
                self.reader = geoip2.database.Reader(db_path)
                logger.info(f"GeoIP database loaded from {db_path}")
            except Exception as e:
                logger.error(f"Failed to load GeoIP database: {e}")
        else:
            logger.warning("GeoIP database not found. IP geolocation will not be available.")
            logger.info("To enable GeoIP, download GeoLite2-City.mmdb from https://dev.maxmind.com/geoip/geolite2-free-geolocation-data")

    def lookup_ip(self, ip_address: str) -> Optional[Dict]:
        """
        Lookup IP address geolocation
        Returns dict with country, city, lat/lon, etc.
        """
        if not self.reader:
            return None

        try:
            response = self.reader.city(ip_address)

            result = {
                'ip': ip_address,
                'country_code': response.country.iso_code,
                'country_name': response.country.name,
                'city': response.city.name,
                'latitude': response.location.latitude,
                'longitude': response.location.longitude,
                'timezone': response.location.time_zone,
                'continent': response.continent.name,
                'continent_code': response.continent.code,
                'accuracy_radius': response.location.accuracy_radius
            }

            # Add subdivision (state/province) if available
            if response.subdivisions.most_specific:
                result['subdivision'] = response.subdivisions.most_specific.name
                result['subdivision_code'] = response.subdivisions.most_specific.iso_code

            # Add postal code if available
            if response.postal.code:
                result['postal_code'] = response.postal.code

            logger.debug(f"GeoIP lookup for {ip_address}: {result.get('country_name')}, {result.get('city')}")
            return result

        except geoip2.errors.AddressNotFoundError:
            logger.debug(f"IP {ip_address} not found in GeoIP database (private/reserved IP)")
            return None
        except Exception as e:
            logger.error(f"Error looking up IP {ip_address}: {e}")
            return None

    def is_available(self) -> bool:
        """Check if GeoIP service is available"""
        return self.reader is not None

    def close(self):
        """Close GeoIP database reader"""
        if self.reader:
            self.reader.close()

    def __del__(self):
        """Cleanup on deletion"""
        self.close()


# Singleton instance
_geoip_service: Optional[GeoIPService] = None


def get_geoip_service(db_path: Optional[str] = None) -> GeoIPService:
    """Get or create GeoIP service instance"""
    global _geoip_service

    if _geoip_service is None:
        _geoip_service = GeoIPService(db_path)

    return _geoip_service
