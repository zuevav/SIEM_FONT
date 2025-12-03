"""
API Client - sends events to SIEM backend
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
import aiohttp


logger = logging.getLogger(__name__)


class SIEMAPIClient:
    """API client for SIEM backend"""

    def __init__(self, config):
        self.config = config
        self.session: aiohttp.ClientSession = None
        self.registered = False
        self.monitor_id = None

    async def start(self):
        """Start API client"""
        # Create HTTP session
        connector = aiohttp.TCPConnector(
            limit=10,
            ssl=not self.config.siem.insecure_skip_verify
        )

        timeout = aiohttp.ClientTimeout(total=self.config.siem.send_timeout)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.config.siem.api_key,
                "User-Agent": "SIEM-NetworkMonitor/1.0"
            }
        )

        # Register monitor
        if self.config.siem.register_on_startup:
            await self.register()

    async def stop(self):
        """Stop API client"""
        if self.session:
            await self.session.close()

    async def register(self):
        """Register network monitor with SIEM"""
        try:
            import socket
            hostname = socket.gethostname()

            data = {
                "agent_id": f"netmon-{hostname}",
                "hostname": hostname,
                "agent_type": "network_monitor",
                "version": "1.0.0",
                "capabilities": {
                    "snmp": self.config.snmp.enabled,
                    "syslog": self.config.syslog.enabled,
                    "netflow": self.config.netflow.enabled,
                    "devices_count": len(self.config.snmp.devices)
                }
            }

            url = f"{self.config.siem.server_url}/api/v1/agents/register"

            async with self.session.post(url, json=data) as resp:
                if resp.status == 200 or resp.status == 201:
                    result = await resp.json()
                    self.monitor_id = data["agent_id"]
                    self.registered = True
                    logger.info(f"Network monitor registered: {self.monitor_id}")
                else:
                    error = await resp.text()
                    logger.error(f"Failed to register: HTTP {resp.status}: {error}")

        except Exception as e:
            logger.error(f"Registration failed: {e}")

    async def send_heartbeat(self, stats: Dict[str, Any]):
        """Send heartbeat to SIEM"""
        if not self.registered:
            return

        try:
            import socket
            import psutil

            data = {
                "agent_id": self.monitor_id,
                "hostname": socket.gethostname(),
                "status": "online",
                "timestamp": datetime.utcnow().isoformat(),
                "stats": stats,
                "system": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                }
            }

            url = f"{self.config.siem.server_url}/api/v1/agents/heartbeat"

            async with self.session.post(url, json=data) as resp:
                if resp.status != 200:
                    logger.warning(f"Heartbeat failed: HTTP {resp.status}")

        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

    async def send_events(self, events: List[Dict[str, Any]]) -> bool:
        """Send batch of events to SIEM"""
        if not events:
            return True

        # Add agent_id to events
        for event in events:
            event["agent_id"] = self.monitor_id
            event["event_time"] = event.get("event_time", datetime.utcnow().isoformat())
            event["collected_at"] = datetime.utcnow().isoformat()

        # Send with retry
        for attempt in range(self.config.siem.retry_attempts + 1):
            try:
                url = f"{self.config.siem.server_url}/api/v1/events/batch"

                async with self.session.post(url, json=events) as resp:
                    if resp.status == 200 or resp.status == 201:
                        logger.debug(f"Sent {len(events)} events to SIEM")
                        return True
                    else:
                        error = await resp.text()
                        logger.warning(f"Failed to send events: HTTP {resp.status}: {error}")

            except Exception as e:
                logger.error(f"Error sending events (attempt {attempt + 1}): {e}")

            # Wait before retry
            if attempt < self.config.siem.retry_attempts:
                await asyncio.sleep(self.config.siem.retry_delay * (2 ** attempt))

        return False
