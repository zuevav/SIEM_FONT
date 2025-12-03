"""
NetFlow/sFlow Collector - collects and analyzes network traffic flows
Supports NetFlow v5, v9, and IPFIX (v10)
"""

import asyncio
import logging
import struct
from typing import Dict, Any, Optional, List
from datetime import datetime
import socket


logger = logging.getLogger(__name__)


class NetFlowCollector:
    """NetFlow/IPFIX collector"""

    def __init__(self, config, event_queue: asyncio.Queue):
        self.config = config
        self.event_queue = event_queue
        self.transport = None
        self.stats = {
            "packets_received": 0,
            "flows_processed": 0,
            "bytes_total": 0,
            "parse_errors": 0
        }
        # Template cache for NetFlow v9 / IPFIX
        self.templates: Dict[str, Dict[int, Any]] = {}

    async def start(self):
        """Start NetFlow collector"""
        if not self.config.netflow.enabled:
            logger.info("NetFlow collector disabled")
            return

        logger.info(f"Starting NetFlow collector on port {self.config.netflow.port}")

        loop = asyncio.get_event_loop()

        # Create UDP endpoint for NetFlow
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: NetFlowProtocol(self),
            local_addr=('0.0.0.0', self.config.netflow.port)
        )

        self.transport = transport

        try:
            await asyncio.Future()  # Run forever
        finally:
            transport.close()

    async def process_netflow_packet(self, data: bytes, addr: tuple):
        """Process received NetFlow packet"""
        self.stats["packets_received"] += 1

        try:
            # Parse NetFlow version
            if len(data) < 2:
                return

            version = struct.unpack('!H', data[0:2])[0]

            if version == 5:
                await self._process_netflow_v5(data, addr)
            elif version == 9:
                await self._process_netflow_v9(data, addr)
            elif version == 10:
                await self._process_ipfix(data, addr)
            else:
                logger.warning(f"Unsupported NetFlow version: {version} from {addr[0]}")

        except Exception as e:
            logger.error(f"Error processing NetFlow packet from {addr[0]}: {e}")
            self.stats["parse_errors"] += 1

    async def _process_netflow_v5(self, data: bytes, addr: tuple):
        """Process NetFlow v5 packet"""
        if len(data) < 24:
            return

        # Parse NetFlow v5 header
        header = struct.unpack('!HHIIIIBBH', data[0:24])
        version, count, sys_uptime, unix_secs, unix_nsecs, flow_sequence, engine_type, engine_id, sampling = header

        # Process flows
        offset = 24
        flow_size = 48

        for i in range(count):
            if offset + flow_size > len(data):
                break

            flow_data = data[offset:offset + flow_size]
            flow = self._parse_netflow_v5_record(flow_data, addr[0], unix_secs)

            if flow:
                await self._create_flow_event(flow, addr[0])
                self.stats["flows_processed"] += 1

            offset += flow_size

    def _parse_netflow_v5_record(self, data: bytes, source_ip: str, timestamp: int) -> Optional[Dict[str, Any]]:
        """Parse NetFlow v5 flow record"""
        try:
            # NetFlow v5 record structure (48 bytes)
            unpacked = struct.unpack('!IIIHHIIIIHH' + 'BBHHHBBHBB', data)

            flow = {
                'version': 5,
                'source_device': source_ip,
                'src_addr': socket.inet_ntoa(struct.pack('!I', unpacked[0])),
                'dst_addr': socket.inet_ntoa(struct.pack('!I', unpacked[1])),
                'next_hop': socket.inet_ntoa(struct.pack('!I', unpacked[2])),
                'input_interface': unpacked[3],
                'output_interface': unpacked[4],
                'packets': unpacked[5],
                'bytes': unpacked[6],
                'first_switched': unpacked[7],
                'last_switched': unpacked[8],
                'src_port': unpacked[9],
                'dst_port': unpacked[10],
                'tcp_flags': unpacked[12],
                'protocol': unpacked[13],
                'tos': unpacked[14],
                'src_as': unpacked[15],
                'dst_as': unpacked[16],
                'src_mask': unpacked[17],
                'dst_mask': unpacked[18],
                'timestamp': datetime.fromtimestamp(timestamp)
            }

            self.stats["bytes_total"] += flow['bytes']

            return flow

        except Exception as e:
            logger.error(f"Error parsing NetFlow v5 record: {e}")
            return None

    async def _process_netflow_v9(self, data: bytes, addr: tuple):
        """Process NetFlow v9 packet (template-based)"""
        if len(data) < 20:
            return

        # Parse header
        version, count, sys_uptime, unix_secs, sequence, source_id = struct.unpack('!HHIIII', data[0:20])

        source_key = f"{addr[0]}:{source_id}"
        offset = 20

        # Process FlowSets
        for i in range(count):
            if offset + 4 > len(data):
                break

            flowset_id, flowset_length = struct.unpack('!HH', data[offset:offset + 4])

            if flowset_length < 4:
                break

            flowset_data = data[offset + 4:offset + flowset_length]

            if flowset_id == 0:
                # Template FlowSet
                self._process_template_flowset(flowset_data, source_key)
            elif flowset_id == 1:
                # Options Template FlowSet
                pass
            elif flowset_id > 255:
                # Data FlowSet
                await self._process_data_flowset(flowset_id, flowset_data, source_key, addr[0], unix_secs)

            offset += flowset_length

    def _process_template_flowset(self, data: bytes, source_key: str):
        """Process NetFlow v9 Template FlowSet"""
        offset = 0

        while offset + 4 <= len(data):
            template_id, field_count = struct.unpack('!HH', data[offset:offset + 4])
            offset += 4

            fields = []
            for _ in range(field_count):
                if offset + 4 > len(data):
                    break

                field_type, field_length = struct.unpack('!HH', data[offset:offset + 4])
                fields.append({
                    'type': field_type,
                    'length': field_length
                })
                offset += 4

            # Store template
            if source_key not in self.templates:
                self.templates[source_key] = {}

            self.templates[source_key][template_id] = fields
            logger.debug(f"Stored template {template_id} from {source_key} with {len(fields)} fields")

    async def _process_data_flowset(self, template_id: int, data: bytes, source_key: str,
                                     source_ip: str, timestamp: int):
        """Process NetFlow v9 Data FlowSet"""
        if source_key not in self.templates or template_id not in self.templates[source_key]:
            logger.debug(f"Template {template_id} not found for {source_key}")
            return

        template = self.templates[source_key][template_id]

        # Calculate record length
        record_length = sum(field['length'] for field in template)

        offset = 0
        while offset + record_length <= len(data):
            record_data = data[offset:offset + record_length]
            flow = self._parse_netflow_v9_record(record_data, template, source_ip, timestamp)

            if flow:
                await self._create_flow_event(flow, source_ip)
                self.stats["flows_processed"] += 1

            offset += record_length

    def _parse_netflow_v9_record(self, data: bytes, template: List[Dict],
                                  source_ip: str, timestamp: int) -> Optional[Dict[str, Any]]:
        """Parse NetFlow v9 record using template"""
        try:
            flow = {
                'version': 9,
                'source_device': source_ip,
                'timestamp': datetime.fromtimestamp(timestamp)
            }

            offset = 0
            for field in template:
                field_type = field['type']
                field_length = field['length']

                if offset + field_length > len(data):
                    break

                field_data = data[offset:offset + field_length]

                # Parse common fields
                if field_type == 8:  # IPv4 Source Address
                    flow['src_addr'] = socket.inet_ntoa(field_data[:4])
                elif field_type == 12:  # IPv4 Destination Address
                    flow['dst_addr'] = socket.inet_ntoa(field_data[:4])
                elif field_type == 7:  # Source Port
                    flow['src_port'] = struct.unpack('!H', field_data)[0]
                elif field_type == 11:  # Destination Port
                    flow['dst_port'] = struct.unpack('!H', field_data)[0]
                elif field_type == 4:  # Protocol
                    flow['protocol'] = struct.unpack('!B', field_data)[0]
                elif field_type == 1:  # Bytes
                    if field_length == 4:
                        flow['bytes'] = struct.unpack('!I', field_data)[0]
                    elif field_length == 8:
                        flow['bytes'] = struct.unpack('!Q', field_data)[0]
                elif field_type == 2:  # Packets
                    if field_length == 4:
                        flow['packets'] = struct.unpack('!I', field_data)[0]
                    elif field_length == 8:
                        flow['packets'] = struct.unpack('!Q', field_data)[0]

                offset += field_length

            if 'bytes' in flow:
                self.stats["bytes_total"] += flow['bytes']

            return flow

        except Exception as e:
            logger.error(f"Error parsing NetFlow v9 record: {e}")
            return None

    async def _process_ipfix(self, data: bytes, addr: tuple):
        """Process IPFIX (NetFlow v10) packet"""
        # IPFIX is similar to NetFlow v9 but with some differences
        # For now, reuse NetFlow v9 logic
        await self._process_netflow_v9(data, addr)

    async def _create_flow_event(self, flow: Dict[str, Any], source_ip: str):
        """Create SIEM event from flow"""
        # Get device info
        device = self.config.get_device_by_ip(source_ip)

        # Determine if flow is suspicious
        is_suspicious = self._is_suspicious_flow(flow)

        event = {
            "source_type": "NetFlow",
            "event_code": 5000 if not is_suspicious else 5001,  # 5000=normal, 5001=suspicious
            "severity": 1 if not is_suspicious else 3,
            "computer": device.name if device else source_ip,
            "ip_address": source_ip,
            "provider": "NetFlow Collector",
            "channel": "Network",
            "message": self._generate_flow_message(flow),
            "event_data": {
                "device_type": device.type if device else "unknown",
                "netflow_version": flow.get('version'),
                "src_addr": flow.get('src_addr'),
                "dst_addr": flow.get('dst_addr'),
                "src_port": flow.get('src_port'),
                "dst_port": flow.get('dst_port'),
                "protocol": flow.get('protocol'),
                "bytes": flow.get('bytes'),
                "packets": flow.get('packets'),
                "is_suspicious": is_suspicious
            }
        }

        await self.event_queue.put(event)

    def _is_suspicious_flow(self, flow: Dict[str, Any]) -> bool:
        """Detect suspicious network flows"""
        # Large data transfer (> 100 MB)
        if flow.get('bytes', 0) > 100 * 1024 * 1024:
            return True

        # Known malicious ports
        malicious_ports = {22, 23, 3389, 445, 139, 1433, 3306}  # SSH, Telnet, RDP, SMB, SQL
        dst_port = flow.get('dst_port', 0)
        if dst_port in malicious_ports:
            return True

        # Port scanning detection (many packets, few bytes)
        packets = flow.get('packets', 0)
        bytes_total = flow.get('bytes', 1)
        if packets > 100 and (bytes_total / packets) < 100:
            return True

        return False

    def _generate_flow_message(self, flow: Dict[str, Any]) -> str:
        """Generate human-readable message from flow"""
        src = flow.get('src_addr', 'unknown')
        dst = flow.get('dst_addr', 'unknown')
        src_port = flow.get('src_port', 0)
        dst_port = flow.get('dst_port', 0)
        bytes_total = flow.get('bytes', 0)
        packets = flow.get('packets', 0)

        protocol_map = {1: 'ICMP', 6: 'TCP', 17: 'UDP'}
        protocol = protocol_map.get(flow.get('protocol', 0), 'Unknown')

        return f"Flow: {src}:{src_port} -> {dst}:{dst_port} ({protocol}), " \
               f"{packets} packets, {bytes_total} bytes"

    def get_stats(self) -> Dict[str, int]:
        """Get collector statistics"""
        return self.stats.copy()


class NetFlowProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for NetFlow"""

    def __init__(self, collector: NetFlowCollector):
        self.collector = collector
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        asyncio.create_task(
            self.collector.process_netflow_packet(data, addr)
        )
