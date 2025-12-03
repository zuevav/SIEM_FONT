"""
SNMP Collector - polls network devices and collects metrics
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from pysnmp.hlapi import *
from pysnmp.hlapi.asyncio import *

from config import Config, SNMPDeviceConfig
from device_profiles import get_device_profile, DeviceProfile


logger = logging.getLogger(__name__)


class SNMPCollector:
    """SNMP collector for network devices"""

    def __init__(self, config: Config, event_queue: asyncio.Queue):
        self.config = config
        self.event_queue = event_queue
        self.devices = config.get_enabled_devices()
        self.metrics_cache: Dict[str, Dict[str, Any]] = {}
        self.last_poll_time: Dict[str, float] = {}

    async def start(self):
        """Start SNMP collection"""
        logger.info(f"Starting SNMP collector for {len(self.devices)} devices")

        # Create tasks for each device
        tasks = []
        for device in self.devices:
            task = asyncio.create_task(self._poll_device_loop(device))
            tasks.append(task)

        # Wait for all tasks
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _poll_device_loop(self, device: SNMPDeviceConfig):
        """Poll device in a loop"""
        logger.info(f"Starting polling loop for {device.name} ({device.ip})")

        while True:
            try:
                await self._poll_device(device)
            except Exception as e:
                logger.error(f"Error polling {device.name}: {e}", exc_info=True)
                # Create error event
                await self._create_error_event(device, str(e))

            # Wait for next poll
            await asyncio.sleep(self.config.snmp.poll_interval)

    async def _poll_device(self, device: SNMPDeviceConfig):
        """Poll single device"""
        start_time = time.time()

        # Get device profile
        profile = get_device_profile(device.type)
        oids_to_poll = profile.get_monitoring_oids()

        # Add custom OIDs from config
        if device.oids:
            for i, oid in enumerate(device.oids):
                oids_to_poll[f"custom_{i}"] = oid

        # Poll all OIDs
        metrics = await self._snmp_get_bulk(device, oids_to_poll)

        if not metrics:
            logger.warning(f"No metrics received from {device.name}")
            return

        # Parse metrics using device profile
        parsed_metrics = {}
        for oid, value in metrics.items():
            parsed = profile.parse_value(oid, value)
            parsed_metrics.update(parsed)

        # Store metrics in cache
        self.metrics_cache[device.name] = {
            "device": device.name,
            "ip": device.ip,
            "type": device.type,
            "metrics": parsed_metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "poll_time_ms": int((time.time() - start_time) * 1000)
        }

        self.last_poll_time[device.name] = time.time()

        # Detect anomalies
        anomalies = profile.detect_anomaly(
            parsed_metrics,
            self.config.snmp.anomaly_detection.model_dump()
        )

        # Create events for anomalies
        for anomaly in anomalies:
            await self._create_anomaly_event(device, anomaly, parsed_metrics)

        # Create metric update event (low priority)
        await self._create_metrics_event(device, parsed_metrics)

        logger.debug(f"Polled {device.name}: {len(parsed_metrics)} metrics, "
                     f"{len(anomalies)} anomalies, {int((time.time() - start_time) * 1000)}ms")

    async def _snmp_get_bulk(self, device: SNMPDeviceConfig, oids: Dict[str, str]) -> Dict[str, Any]:
        """Get multiple OIDs from device using SNMP GET"""
        results = {}

        # Determine community string
        community = device.community if device.community else self.config.snmp.community

        # Create SNMP engine
        try:
            for name, oid in oids.items():
                iterator = await getCmd(
                    SnmpEngine(),
                    CommunityData(community, mpModel=1 if self.config.snmp.version == "2c" else 0),
                    await UdpTransportTarget.create((device.ip, 161), timeout=self.config.snmp.timeout, retries=self.config.snmp.retries),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )

                errorIndication, errorStatus, errorIndex, varBinds = iterator

                if errorIndication:
                    logger.warning(f"SNMP error for {device.name} OID {oid}: {errorIndication}")
                    continue

                if errorStatus:
                    logger.warning(f"SNMP error for {device.name} OID {oid}: {errorStatus.prettyPrint()}")
                    continue

                # Extract value
                for varBind in varBinds:
                    value = varBind[1].prettyPrint()
                    results[oid] = value

        except Exception as e:
            logger.error(f"SNMP exception for {device.name}: {e}")

        return results

    async def _create_metrics_event(self, device: SNMPDeviceConfig, metrics: Dict[str, Any]):
        """Create event with device metrics"""
        event = {
            "source_type": "Network Device",
            "event_code": 1000,  # Generic metrics update
            "severity": 1,  # Info
            "computer": device.name,
            "ip_address": device.ip,
            "provider": "SNMP Monitor",
            "channel": "Network",
            "message": f"Metrics update from {device.name}",
            "event_data": {
                "device_type": device.type,
                **metrics
            }
        }

        await self.event_queue.put(event)

    async def _create_anomaly_event(self, device: SNMPDeviceConfig, anomaly: Dict[str, Any], metrics: Dict[str, Any]):
        """Create event for detected anomaly"""
        event = {
            "source_type": "Network Device",
            "event_code": 2000 + anomaly.get("severity", 0),  # 2001-2005 based on severity
            "severity": anomaly.get("severity", 3),
            "computer": device.name,
            "ip_address": device.ip,
            "provider": "SNMP Monitor",
            "channel": "Network",
            "message": f"{device.name}: {anomaly['message']}",
            "event_data": {
                "device_type": device.type,
                "anomaly_type": anomaly["type"],
                "value": anomaly.get("value"),
                "threshold": anomaly.get("threshold"),
                "all_metrics": metrics
            }
        }

        await self.event_queue.put(event)

        logger.warning(f"Anomaly detected on {device.name}: {anomaly['message']}")

    async def _create_error_event(self, device: SNMPDeviceConfig, error_msg: str):
        """Create event for polling error"""
        event = {
            "source_type": "Network Device",
            "event_code": 3000,  # Device unreachable/error
            "severity": 4,  # Error
            "computer": device.name,
            "ip_address": device.ip,
            "provider": "SNMP Monitor",
            "channel": "Network",
            "message": f"Failed to poll {device.name}: {error_msg}",
            "event_data": {
                "device_type": device.type,
                "error": error_msg
            }
        }

        await self.event_queue.put(event)

    def get_device_status(self, device_name: str) -> Optional[Dict[str, Any]]:
        """Get cached status for device"""
        return self.metrics_cache.get(device_name)

    def get_all_device_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached device statuses"""
        return self.metrics_cache.copy()
