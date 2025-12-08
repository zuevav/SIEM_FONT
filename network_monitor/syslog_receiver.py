"""
Syslog Receiver - receives syslog messages from network devices
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime
from syslog_rfc5424_parser import SyslogMessage, ParseError


logger = logging.getLogger(__name__)


class SyslogReceiver:
    """Syslog receiver for network devices"""

    def __init__(self, config, event_queue: asyncio.Queue):
        self.config = config
        self.event_queue = event_queue
        self.servers = []
        self.stats = {
            "messages_received": 0,
            "messages_parsed": 0,
            "messages_dropped": 0,
            "parse_errors": 0
        }

    async def start(self):
        """Start syslog receivers"""
        if not self.config.syslog.enabled:
            logger.info("Syslog receiver disabled")
            return

        logger.info(f"Starting syslog receivers on {len(self.config.syslog.listeners)} listeners")

        tasks = []
        for listener in self.config.syslog.listeners:
            if listener.protocol == "udp":
                task = asyncio.create_task(self._start_udp_server(listener))
            elif listener.protocol == "tcp":
                task = asyncio.create_task(self._start_tcp_server(listener))
            else:
                logger.warning(f"Unknown syslog protocol: {listener.protocol}")
                continue

            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _start_udp_server(self, listener):
        """Start UDP syslog server"""
        logger.info(f"Starting UDP syslog server on {listener.bind}:{listener.port}")

        loop = asyncio.get_event_loop()

        # Create UDP endpoint
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: SyslogUDPProtocol(self),
            local_addr=(listener.bind, listener.port)
        )

        self.servers.append(transport)

        try:
            await asyncio.Future()  # Run forever
        finally:
            transport.close()

    async def _start_tcp_server(self, listener):
        """Start TCP syslog server"""
        logger.info(f"Starting TCP syslog server on {listener.bind}:{listener.port}")

        server = await asyncio.start_server(
            self._handle_tcp_client,
            listener.bind,
            listener.port
        )

        self.servers.append(server)

        async with server:
            await server.serve_forever()

    async def _handle_tcp_client(self, reader, writer):
        """Handle TCP syslog client"""
        addr = writer.get_extra_info('peername')
        logger.debug(f"TCP syslog connection from {addr}")

        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break

                message = data.decode('utf-8', errors='ignore')
                await self._process_syslog_message(message, addr[0], 'tcp')

        except Exception as e:
            logger.error(f"Error handling TCP client {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _process_syslog_message(self, message: str, source_ip: str, protocol: str):
        """Process received syslog message"""
        self.stats["messages_received"] += 1

        # Check if source is allowed
        if not self._is_source_allowed(source_ip):
            logger.warning(f"Syslog message from blocked source: {source_ip}")
            self.stats["messages_dropped"] += 1
            return

        # Parse syslog message
        parsed = self._parse_syslog(message, source_ip)

        if not parsed:
            self.stats["parse_errors"] += 1
            return

        self.stats["messages_parsed"] += 1

        # Get device info
        device = self.config.get_device_by_ip(source_ip)

        # Create event
        event = {
            "source_type": "Network Device",
            "event_code": 4000,  # Syslog message
            "severity": self._map_syslog_severity(parsed.get("severity", 6)),
            "computer": device.name if device else source_ip,
            "ip_address": source_ip,
            "provider": "Syslog",
            "channel": "Network",
            "message": parsed.get("message", ""),
            "event_data": {
                "device_type": device.type if device else "unknown",
                "syslog_facility": parsed.get("facility"),
                "syslog_severity": parsed.get("severity"),
                "syslog_tag": parsed.get("tag"),
                "protocol": protocol,
                **parsed.get("structured_data", {})
            }
        }

        await self.event_queue.put(event)

        if self.config.logging.log_syslog_messages:
            logger.debug(f"Syslog from {source_ip}: {parsed.get('message', '')[:100]}")

    def _parse_syslog(self, message: str, source_ip: str) -> Optional[Dict[str, Any]]:
        """Parse syslog message (RFC 3164 or RFC 5424)"""
        try:
            # Try RFC 5424 first
            if "rfc5424" in self.config.syslog.formats:
                try:
                    msg = SyslogMessage.parse(message)
                    return {
                        "severity": msg.severity,
                        "facility": msg.facility,
                        "timestamp": msg.timestamp.isoformat() if msg.timestamp else datetime.utcnow().isoformat(),
                        "hostname": msg.hostname,
                        "appname": msg.appname,
                        "procid": msg.procid,
                        "msgid": msg.msgid,
                        "message": msg.msg,
                        "structured_data": msg.sd or {}
                    }
                except ParseError:
                    pass

            # Fallback to RFC 3164
            if "rfc3164" in self.config.syslog.formats:
                return self._parse_rfc3164(message, source_ip)

        except Exception as e:
            logger.error(f"Error parsing syslog message: {e}")

        return None

    def _parse_rfc3164(self, message: str, source_ip: str) -> Optional[Dict[str, Any]]:
        """Parse RFC 3164 (BSD syslog) message"""
        # Pattern: <PRI>Mmm dd hh:mm:ss hostname tag: message
        pattern = r'^<(\d+)>(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\S+)\s+([^:]+):\s*(.*)$'

        match = re.match(pattern, message)
        if not match:
            # Try simpler pattern without timestamp
            pattern = r'^<(\d+)>([^:]+):\s*(.*)$'
            match = re.match(pattern, message)
            if not match:
                # Fallback: just extract message
                return {
                    "severity": 6,  # Info
                    "facility": 1,  # User
                    "timestamp": datetime.utcnow().isoformat(),
                    "hostname": source_ip,
                    "tag": "unknown",
                    "message": message
                }

            pri, tag, msg = match.groups()
            timestamp = datetime.utcnow().isoformat()
            hostname = source_ip
        else:
            pri, timestamp_str, hostname, tag, msg = match.groups()
            timestamp = datetime.utcnow().isoformat()  # Simplified, should parse timestamp_str

        # Extract facility and severity from PRI
        pri = int(pri)
        facility = pri >> 3
        severity = pri & 0x07

        return {
            "severity": severity,
            "facility": facility,
            "timestamp": timestamp,
            "hostname": hostname,
            "tag": tag.strip(),
            "message": msg.strip()
        }

    def _is_source_allowed(self, source_ip: str) -> bool:
        """Check if source IP is allowed"""
        # Check if source is in blocked list
        if source_ip in self.config.syslog.sources.get("blocked_ips", []):
            return False

        # If use_snmp_devices is enabled, allow all SNMP devices
        if self.config.syslog.sources.get("use_snmp_devices", True):
            device = self.config.get_device_by_ip(source_ip)
            if device:
                return True

        # Check allowed IPs (CIDR support would require netaddr)
        allowed_ips = self.config.syslog.sources.get("allowed_ips", [])
        if allowed_ips:
            # Simple IP check (no CIDR for now)
            return source_ip in allowed_ips

        # SECURITY: Default deny policy - block unknown sources
        # To allow all sources, explicitly set allowed_ips to ["*"] in config
        logger.warning(f"Syslog from unknown source {source_ip} blocked (default deny policy)")
        return False

    def _map_syslog_severity(self, syslog_severity: int) -> int:
        """Map syslog severity (0-7) to SIEM severity (1-5)"""
        # Syslog: 0=Emergency, 1=Alert, 2=Critical, 3=Error, 4=Warning, 5=Notice, 6=Info, 7=Debug
        # SIEM: 1=Info, 2=Low, 3=Medium, 4=High, 5=Critical
        severity_map = {
            0: 5,  # Emergency -> Critical
            1: 5,  # Alert -> Critical
            2: 5,  # Critical -> Critical
            3: 4,  # Error -> High
            4: 3,  # Warning -> Medium
            5: 2,  # Notice -> Low
            6: 1,  # Info -> Info
            7: 1,  # Debug -> Info
        }
        return severity_map.get(syslog_severity, 1)

    def get_stats(self) -> Dict[str, int]:
        """Get receiver statistics"""
        return self.stats.copy()


class SyslogUDPProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for syslog"""

    def __init__(self, receiver: SyslogReceiver):
        self.receiver = receiver
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode('utf-8', errors='ignore')
        asyncio.create_task(
            self.receiver._process_syslog_message(message, addr[0], 'udp')
        )
