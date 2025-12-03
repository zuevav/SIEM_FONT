"""
SNMP Traps Receiver - receives asynchronous notifications from network devices
Supports SNMPv2c and SNMPv3 traps
"""

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime
from pysnmp.hlapi import *
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.carrier.asyncio.dgram import udp


logger = logging.getLogger(__name__)


class SNMPTrapsReceiver:
    """SNMP Traps receiver"""

    def __init__(self, cfg, event_queue: asyncio.Queue):
        self.config = cfg
        self.event_queue = event_queue
        self.snmp_engine = None
        self.stats = {
            "traps_received": 0,
            "traps_processed": 0,
            "parse_errors": 0
        }

        # Well-known trap OIDs
        self.trap_oids = {
            '1.3.6.1.6.3.1.1.5.1': 'coldStart',
            '1.3.6.1.6.3.1.1.5.2': 'warmStart',
            '1.3.6.1.6.3.1.1.5.3': 'linkDown',
            '1.3.6.1.6.3.1.1.5.4': 'linkUp',
            '1.3.6.1.6.3.1.1.5.5': 'authenticationFailure',
            '1.3.6.1.6.3.1.1.5.6': 'egpNeighborLoss',
        }

    async def start(self):
        """Start SNMP traps receiver"""
        logger.info(f"Starting SNMP Traps receiver on UDP port 162")

        try:
            # Create SNMP engine
            self.snmp_engine = engine.SnmpEngine()

            # UDP transport
            config.addTransport(
                self.snmp_engine,
                udp.domainName,
                udp.UdpTransport().openServerMode(('0.0.0.0', 162))
            )

            # Configure SNMPv2c community
            config.addV1System(
                self.snmp_engine,
                'my-area',
                self.config.snmp.community
            )

            # Configure SNMPv3 user if enabled
            if self.config.snmp.version == "3":
                config.addV3User(
                    self.snmp_engine,
                    self.config.snmp.v3.username,
                    config.usmHMACMD5AuthProtocol if self.config.snmp.v3.auth_protocol == "MD5" else config.usmHMACSHAAuthProtocol,
                    self.config.snmp.v3.auth_password,
                    config.usmDESPrivProtocol if self.config.snmp.v3.priv_protocol == "DES" else config.usmAesCfb128Protocol,
                    self.config.snmp.v3.priv_password
                )

            # Register callback
            ntfrcv.NotificationReceiver(
                self.snmp_engine,
                self._trap_callback
            )

            # Run SNMP engine
            self.snmp_engine.transportDispatcher.jobStarted(1)

            try:
                # Run dispatcher in asyncio loop
                while True:
                    self.snmp_engine.transportDispatcher.runDispatcher(timeout=0.5)
                    await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                pass
            finally:
                self.snmp_engine.transportDispatcher.jobFinished(1)

        except Exception as e:
            logger.error(f"Error starting SNMP traps receiver: {e}")

    def _trap_callback(self, snmpEngine, stateReference, contextEngineId, contextName,
                      varBinds, cbCtx):
        """Callback for received SNMP traps"""
        self.stats["traps_received"] += 1

        try:
            # Get source address
            transportDomain, transportAddress = snmpEngine.msgAndPduDsp.getTransportInfo(stateReference)
            source_ip = transportAddress[0]

            # Parse trap variables
            trap_data = {}
            trap_oid = None

            for oid, val in varBinds:
                oid_str = str(oid)
                val_str = str(val)

                # snmpTrapOID
                if oid_str == '1.3.6.1.6.3.1.1.4.1.0':
                    trap_oid = val_str

                trap_data[oid_str] = val_str

            # Get trap type
            trap_type = self.trap_oids.get(trap_oid, trap_oid or 'unknown')

            # Create event
            asyncio.create_task(
                self._create_trap_event(source_ip, trap_type, trap_oid, trap_data)
            )

            self.stats["traps_processed"] += 1

        except Exception as e:
            logger.error(f"Error processing SNMP trap: {e}")
            self.stats["parse_errors"] += 1

    async def _create_trap_event(self, source_ip: str, trap_type: str,
                                 trap_oid: str, trap_data: Dict[str, str]):
        """Create SIEM event from SNMP trap"""
        # Get device info
        device = self.config.get_device_by_ip(source_ip)

        # Determine severity based on trap type
        severity = self._get_trap_severity(trap_type)

        event = {
            "source_type": "SNMP Trap",
            "event_code": 6000 + severity,  # 6001-6005
            "severity": severity,
            "computer": device.name if device else source_ip,
            "ip_address": source_ip,
            "provider": "SNMP Traps",
            "channel": "Network",
            "message": self._generate_trap_message(trap_type, trap_data),
            "event_data": {
                "device_type": device.type if device else "unknown",
                "trap_type": trap_type,
                "trap_oid": trap_oid,
                **trap_data
            }
        }

        await self.event_queue.put(event)

        logger.info(f"SNMP Trap from {source_ip}: {trap_type}")

    def _get_trap_severity(self, trap_type: str) -> int:
        """Determine severity based on trap type"""
        critical_traps = ['authenticationFailure', 'linkDown']
        warning_traps = ['linkUp', 'warmStart']

        if trap_type in critical_traps:
            return 4  # High
        elif trap_type in warning_traps:
            return 3  # Medium
        else:
            return 2  # Low

    def _generate_trap_message(self, trap_type: str, trap_data: Dict[str, str]) -> str:
        """Generate human-readable message from trap"""
        messages = {
            'coldStart': 'Device cold start (reboot)',
            'warmStart': 'Device warm start (restart)',
            'linkDown': 'Network interface down',
            'linkUp': 'Network interface up',
            'authenticationFailure': 'SNMP authentication failure',
            'egpNeighborLoss': 'EGP neighbor loss',
        }

        message = messages.get(trap_type, f'SNMP Trap: {trap_type}')

        # Add additional info if available
        if '1.3.6.1.2.1.2.2.1.1' in trap_data:  # ifIndex
            message += f" (Interface {trap_data['1.3.6.1.2.1.2.2.1.1']})"

        return message

    def get_stats(self) -> Dict[str, int]:
        """Get receiver statistics"""
        return self.stats.copy()
