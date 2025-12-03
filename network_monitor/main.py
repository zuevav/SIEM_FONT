#!/usr/bin/env python3
"""
SIEM Network Monitor
Monitors network devices (printers, switches, routers, firewalls, UPS) via SNMP and syslog
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from config import Config
from snmp_collector import SNMPCollector
from syslog_receiver import SyslogReceiver
from netflow_collector import NetFlowCollector
from snmp_traps import SNMPTrapsReceiver
from device_discovery import DeviceDiscovery
from api_client import SIEMAPIClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/siem/network_monitor.log')
    ]
)

logger = logging.getLogger(__name__)


class NetworkMonitor:
    """Main network monitor application"""

    def __init__(self, config_path: str):
        self.config = Config.load(config_path)
        self.event_queue = asyncio.Queue(maxsize=self.config.performance.max_queue_size)
        self.running = False

        # Components
        self.snmp_collector = None
        self.syslog_receiver = None
        self.netflow_collector = None
        self.snmp_traps = None
        self.device_discovery = None
        self.api_client = None

        # Tasks
        self.tasks = []

    async def start(self):
        """Start network monitor"""
        logger.info("=" * 60)
        logger.info("SIEM Network Monitor Starting")
        logger.info("=" * 60)

        self.running = True

        # Initialize components
        self.api_client = SIEMAPIClient(self.config)
        await self.api_client.start()

        if self.config.snmp.enabled:
            self.snmp_collector = SNMPCollector(self.config, self.event_queue)

        if self.config.syslog.enabled:
            self.syslog_receiver = SyslogReceiver(self.config, self.event_queue)

        if self.config.netflow.enabled:
            self.netflow_collector = NetFlowCollector(self.config, self.event_queue)

        # Always enable SNMP traps (listens on port 162)
        self.snmp_traps = SNMPTrapsReceiver(self.config, self.event_queue)

        # Device discovery
        self.device_discovery = DeviceDiscovery(self.config)

        # Start background tasks
        self.tasks = [
            asyncio.create_task(self._event_sender()),
            asyncio.create_task(self._heartbeat_sender()),
            asyncio.create_task(self._stats_logger()),
        ]

        if self.snmp_collector:
            self.tasks.append(asyncio.create_task(self.snmp_collector.start()))

        if self.syslog_receiver:
            self.tasks.append(asyncio.create_task(self.syslog_receiver.start()))

        if self.netflow_collector:
            self.tasks.append(asyncio.create_task(self.netflow_collector.start()))

        if self.snmp_traps:
            self.tasks.append(asyncio.create_task(self.snmp_traps.start()))

        logger.info("Network Monitor started successfully")
        logger.info(f"SNMP: {'Enabled' if self.config.snmp.enabled else 'Disabled'} "
                    f"({len(self.config.snmp.devices)} devices)")
        logger.info(f"Syslog: {'Enabled' if self.config.syslog.enabled else 'Disabled'}")
        logger.info(f"NetFlow: {'Enabled' if self.config.netflow.enabled else 'Disabled'}")
        logger.info(f"SNMP Traps: Enabled (port 162)")
        logger.info(f"SIEM Backend: {self.config.siem.server_url}")

        # Wait for shutdown signal
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass

    async def stop(self):
        """Stop network monitor"""
        logger.info("Stopping Network Monitor...")
        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # Stop API client
        if self.api_client:
            await self.api_client.stop()

        logger.info("Network Monitor stopped")

    async def _event_sender(self):
        """Send events from queue to SIEM"""
        batch = []
        last_send = asyncio.get_event_loop().time()

        while self.running:
            try:
                # Try to get event from queue (with timeout)
                try:
                    event = await asyncio.wait_for(
                        self.event_queue.get(),
                        timeout=5.0
                    )
                    batch.append(event)
                except asyncio.TimeoutError:
                    pass

                # Send batch if full or timeout
                current_time = asyncio.get_event_loop().time()
                should_send = (
                    len(batch) >= self.config.siem.batch_size or
                    (batch and current_time - last_send >= 30)  # 30 second timeout
                )

                if should_send:
                    success = await self.api_client.send_events(batch)
                    if success:
                        batch.clear()
                        last_send = current_time
                    else:
                        # Keep batch for retry
                        logger.warning(f"Failed to send batch, will retry ({len(batch)} events)")

            except Exception as e:
                logger.error(f"Error in event sender: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _heartbeat_sender(self):
        """Send periodic heartbeat to SIEM"""
        while self.running:
            try:
                # Collect stats
                stats = {
                    "queue_size": self.event_queue.qsize(),
                    "queue_max": self.config.performance.max_queue_size,
                }

                # Add SNMP stats
                if self.snmp_collector:
                    devices = self.config.get_enabled_devices()
                    stats["snmp_devices_monitored"] = len(devices)
                    stats["snmp_last_poll"] = len(self.snmp_collector.metrics_cache)

                # Add syslog stats
                if self.syslog_receiver:
                    stats["syslog"] = self.syslog_receiver.get_stats()

                # Add NetFlow stats
                if self.netflow_collector:
                    stats["netflow"] = self.netflow_collector.get_stats()

                # Add SNMP traps stats
                if self.snmp_traps:
                    stats["snmp_traps"] = self.snmp_traps.get_stats()

                # Send heartbeat
                await self.api_client.send_heartbeat(stats)

            except Exception as e:
                logger.error(f"Error in heartbeat sender: {e}")

            await asyncio.sleep(self.config.siem.heartbeat_interval)

    async def _stats_logger(self):
        """Log statistics periodically"""
        while self.running:
            await asyncio.sleep(300)  # Every 5 minutes

            try:
                logger.info("=" * 60)
                logger.info("Network Monitor Statistics")
                logger.info(f"Event Queue: {self.event_queue.qsize()}/{self.config.performance.max_queue_size}")

                if self.snmp_collector:
                    devices = self.snmp_collector.get_all_device_statuses()
                    logger.info(f"SNMP Devices: {len(devices)} monitored")
                    for name, status in devices.items():
                        logger.info(f"  - {name}: {status.get('metrics', {}).get('sysName', 'N/A')} "
                                    f"(polled {status.get('poll_time_ms', 0)}ms ago)")

                if self.syslog_receiver:
                    stats = self.syslog_receiver.get_stats()
                    logger.info(f"Syslog: {stats['messages_received']} received, "
                                f"{stats['messages_parsed']} parsed, "
                                f"{stats['messages_dropped']} dropped")

                if self.netflow_collector:
                    stats = self.netflow_collector.get_stats()
                    logger.info(f"NetFlow: {stats['packets_received']} packets, "
                                f"{stats['flows_processed']} flows, "
                                f"{stats['bytes_total']} bytes")

                if self.snmp_traps:
                    stats = self.snmp_traps.get_stats()
                    logger.info(f"SNMP Traps: {stats['traps_received']} received, "
                                f"{stats['traps_processed']} processed")

                if self.device_discovery:
                    devices = self.device_discovery.get_discovered_devices()
                    logger.info(f"Device Discovery: {len(devices)} devices discovered")

                logger.info("=" * 60)

            except Exception as e:
                logger.error(f"Error in stats logger: {e}")


async def main():
    """Main entry point"""
    # Default config path
    config_path = "config.yaml"

    # Check if config exists
    if not Path(config_path).exists():
        logger.error(f"Configuration file not found: {config_path}")
        logger.info("Please copy config.yaml.example to config.yaml and configure it")
        sys.exit(1)

    # Create monitor
    monitor = NetworkMonitor(config_path)

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(monitor.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Start monitor
    try:
        await monitor.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
