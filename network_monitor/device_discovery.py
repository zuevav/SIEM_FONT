"""
Device Discovery - automatically discovers network devices
Uses ICMP ping and SNMP to discover and identify devices
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import ipaddress
import subprocess
from pysnmp.hlapi import *


logger = logging.getLogger(__name__)


class DeviceDiscovery:
    """Automatic network device discovery"""

    def __init__(self, config):
        self.config = config
        self.discovered_devices: Dict[str, Dict[str, Any]] = {}

    async def discover_network(self, network: str) -> List[Dict[str, Any]]:
        """
        Discover devices in network
        Args:
            network: CIDR notation (e.g., "192.168.1.0/24")
        Returns:
            List of discovered devices
        """
        logger.info(f"Starting network discovery: {network}")

        try:
            net = ipaddress.IPv4Network(network, strict=False)
        except ValueError as e:
            logger.error(f"Invalid network: {network}: {e}")
            return []

        # Ping sweep
        alive_hosts = await self._ping_sweep(net)
        logger.info(f"Found {len(alive_hosts)} alive hosts")

        # SNMP probe
        devices = []
        tasks = []
        for host in alive_hosts:
            task = asyncio.create_task(self._probe_device(host))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, dict) and result:
                devices.append(result)
                self.discovered_devices[result['ip']] = result

        logger.info(f"Discovered {len(devices)} devices with SNMP")

        return devices

    async def _ping_sweep(self, network: ipaddress.IPv4Network) -> List[str]:
        """Ping sweep to find alive hosts"""
        alive_hosts = []
        tasks = []

        # Limit concurrent pings
        semaphore = asyncio.Semaphore(50)

        async def ping_host(ip: str):
            async with semaphore:
                if await self._ping(ip):
                    alive_hosts.append(ip)

        for host in network.hosts():
            task = asyncio.create_task(ping_host(str(host)))
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        return alive_hosts

    async def _ping(self, host: str) -> bool:
        """Ping a single host"""
        try:
            # Use subprocess for ping (cross-platform)
            process = await asyncio.create_subprocess_exec(
                'ping',
                '-c', '1',  # Linux/Mac
                '-W', '1',  # Timeout 1 second
                host,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )

            returncode = await process.wait()
            return returncode == 0

        except Exception as e:
            logger.debug(f"Ping error for {host}: {e}")
            return False

    async def _probe_device(self, ip: str) -> Optional[Dict[str, Any]]:
        """Probe device with SNMP to get device info"""
        try:
            # Try SNMP GET on sysDescr
            sys_descr_oid = '1.3.6.1.2.1.1.1.0'
            sys_object_id_oid = '1.3.6.1.2.1.1.2.0'
            sys_name_oid = '1.3.6.1.2.1.1.5.0'

            iterator = await getCmd(
                SnmpEngine(),
                CommunityData(self.config.snmp.community, mpModel=1),
                await UdpTransportTarget.create((ip, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(sys_descr_oid)),
                ObjectType(ObjectIdentity(sys_object_id_oid)),
                ObjectType(ObjectIdentity(sys_name_oid))
            )

            errorIndication, errorStatus, errorIndex, varBinds = iterator

            if errorIndication or errorStatus:
                return None

            # Parse results
            sys_descr = varBinds[0][1].prettyPrint() if len(varBinds) > 0 else ""
            sys_object_id = varBinds[1][1].prettyPrint() if len(varBinds) > 1 else ""
            sys_name = varBinds[2][1].prettyPrint() if len(varBinds) > 2 else ""

            # Identify device type
            device_type = self._identify_device_type(sys_descr, sys_object_id)

            device = {
                'ip': ip,
                'name': sys_name or ip,
                'type': device_type,
                'sys_descr': sys_descr,
                'sys_object_id': sys_object_id,
                'snmp_enabled': True
            }

            logger.info(f"Discovered {device_type} at {ip}: {sys_name}")

            return device

        except Exception as e:
            logger.debug(f"SNMP probe failed for {ip}: {e}")
            # Device is alive but no SNMP
            return {
                'ip': ip,
                'name': ip,
                'type': 'unknown',
                'snmp_enabled': False
            }

    def _identify_device_type(self, sys_descr: str, sys_object_id: str) -> str:
        """Identify device type from SNMP data"""
        sys_descr_lower = sys_descr.lower()

        # Printers
        if any(keyword in sys_descr_lower for keyword in ['printer', 'laserjet', 'officejet', 'imageclass', 'xerox']):
            return 'printer'

        # Network devices
        if any(keyword in sys_descr_lower for keyword in ['cisco', 'catalyst', 'nexus']):
            if 'router' in sys_descr_lower or 'isr' in sys_descr_lower:
                return 'router'
            return 'switch'

        if any(keyword in sys_descr_lower for keyword in ['juniper', 'junos']):
            if 'srx' in sys_descr_lower:
                return 'firewall'
            return 'router'

        if any(keyword in sys_descr_lower for keyword in ['hp procurve', 'aruba']):
            return 'switch'

        if any(keyword in sys_descr_lower for keyword in ['mikrotik', 'routeros']):
            return 'router'

        # Firewalls
        if any(keyword in sys_descr_lower for keyword in ['fortinet', 'fortigate', 'checkpoint', 'palo alto', 'pfsense']):
            return 'firewall'

        # UPS
        if any(keyword in sys_descr_lower for keyword in ['ups', 'apc', 'eaton', 'cyberpower']):
            return 'ups'

        # Servers
        if any(keyword in sys_descr_lower for keyword in ['linux', 'windows', 'server', 'debian', 'ubuntu', 'centos']):
            return 'server'

        # Check sysObjectID
        if sys_object_id.startswith('1.3.6.1.4.1.11'):  # HP
            return 'printer'
        elif sys_object_id.startswith('1.3.6.1.4.1.9'):  # Cisco
            return 'switch'
        elif sys_object_id.startswith('1.3.6.1.4.1.318'):  # APC
            return 'ups'

        return 'unknown'

    async def discover_single_device(self, ip: str) -> Optional[Dict[str, Any]]:
        """Discover a single device"""
        if await self._ping(ip):
            return await self._probe_device(ip)
        return None

    def get_discovered_devices(self) -> List[Dict[str, Any]]:
        """Get list of discovered devices"""
        return list(self.discovered_devices.values())

    def clear_discovered(self):
        """Clear discovered devices cache"""
        self.discovered_devices.clear()

    async def continuous_discovery(self, networks: List[str], interval: int = 3600):
        """
        Continuously discover devices in specified networks
        Args:
            networks: List of CIDR networks to scan
            interval: Scan interval in seconds (default: 1 hour)
        """
        logger.info(f"Starting continuous discovery for {len(networks)} networks, interval: {interval}s")

        while True:
            try:
                for network in networks:
                    devices = await self.discover_network(network)
                    logger.info(f"Discovery scan of {network} complete: {len(devices)} devices")

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in continuous discovery: {e}")
                await asyncio.sleep(60)
