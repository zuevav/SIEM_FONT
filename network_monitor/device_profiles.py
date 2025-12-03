"""
Device profiles for different network equipment types
Contains SNMP OIDs and monitoring logic for each device type
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class OIDMapping:
    """SNMP OID mapping"""
    name: str
    oid: str
    description: str
    value_type: str = "string"  # string, int, gauge, counter
    unit: str = ""


class DeviceProfile:
    """Base device profile"""

    def __init__(self):
        self.base_oids = {
            # System information (RFC 1213)
            "sysDescr": "1.3.6.1.2.1.1.1.0",
            "sysObjectID": "1.3.6.1.2.1.1.2.0",
            "sysUpTime": "1.3.6.1.2.1.1.3.0",
            "sysContact": "1.3.6.1.2.1.1.4.0",
            "sysName": "1.3.6.1.2.1.1.5.0",
            "sysLocation": "1.3.6.1.2.1.1.6.0",
        }

    def get_monitoring_oids(self) -> Dict[str, str]:
        """Get list of OIDs to monitor for this device type"""
        return self.base_oids.copy()

    def parse_value(self, oid: str, value: Any) -> Dict[str, Any]:
        """Parse SNMP value and return structured data"""
        return {"oid": oid, "value": value}

    def detect_anomaly(self, metrics: Dict[str, Any], thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect anomalies in metrics"""
        return []


class PrinterProfile(DeviceProfile):
    """Profile for network printers"""

    def __init__(self):
        super().__init__()
        # Printer MIB (RFC 3805)
        self.printer_oids = {
            # General status
            "hrDeviceStatus": "1.3.6.1.2.1.25.3.2.1.5.1",
            "hrPrinterStatus": "1.3.6.1.2.1.25.3.5.1.1.1",
            "hrPrinterDetectedErrorState": "1.3.6.1.2.1.25.3.5.1.2.1",

            # Page counts
            "prtMarkerLifeCount": "1.3.6.1.2.1.43.10.2.1.4.1.1",

            # Supply levels (toner, ink)
            "prtMarkerSuppliesLevel": "1.3.6.1.2.1.43.11.1.1.9.1",
            "prtMarkerSuppliesMaxCapacity": "1.3.6.1.2.1.43.11.1.1.8.1",

            # Cover status
            "prtCoverStatus": "1.3.6.1.2.1.43.6.1.1.3.1",

            # Input/Output trays
            "prtInputStatus": "1.3.6.1.2.1.43.8.2.1.11.1",
            "prtOutputStatus": "1.3.6.1.2.1.43.9.2.1.8.1",
        }

    def get_monitoring_oids(self) -> Dict[str, str]:
        oids = super().get_monitoring_oids()
        oids.update(self.printer_oids)
        return oids

    def parse_value(self, oid: str, value: Any) -> Dict[str, Any]:
        result = super().parse_value(oid, value)

        # Parse printer status
        if "hrPrinterStatus" in oid:
            status_map = {
                1: "other",
                2: "unknown",
                3: "idle",
                4: "printing",
                5: "warmup",
            }
            result["status"] = status_map.get(int(value), "unknown")

        # Calculate toner percentage
        elif "prtMarkerSuppliesLevel" in oid:
            result["toner_level"] = int(value)

        return result

    def detect_anomaly(self, metrics: Dict[str, Any], thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
        anomalies = []

        # Low toner
        if "toner_level" in metrics:
            toner = metrics["toner_level"]
            threshold = thresholds.get("toner_low_threshold", 20)
            if toner < threshold:
                anomalies.append({
                    "type": "low_toner",
                    "severity": 3,
                    "message": f"Low toner level: {toner}%",
                    "value": toner,
                    "threshold": threshold
                })

        # Printer error state
        if "hrPrinterDetectedErrorState" in metrics:
            error_state = metrics["hrPrinterDetectedErrorState"]
            if error_state != "0":
                anomalies.append({
                    "type": "printer_error",
                    "severity": 4,
                    "message": f"Printer error detected: {error_state}",
                    "value": error_state
                })

        return anomalies


class SwitchProfile(DeviceProfile):
    """Profile for network switches"""

    def __init__(self):
        super().__init__()
        # Interface MIB (RFC 2233)
        self.switch_oids = {
            # CPU and Memory
            "cpmCPUTotal5minRev": "1.3.6.1.4.1.9.9.109.1.1.1.1.8",  # Cisco
            "ciscoMemoryPoolUsed": "1.3.6.1.4.1.9.9.48.1.1.1.5.1",
            "ciscoMemoryPoolFree": "1.3.6.1.4.1.9.9.48.1.1.1.6.1",

            # Interfaces
            "ifNumber": "1.3.6.1.2.1.2.1.0",
            "ifTable": "1.3.6.1.2.1.2.2.1",
            "ifDescr": "1.3.6.1.2.1.2.2.1.2",
            "ifType": "1.3.6.1.2.1.2.2.1.3",
            "ifSpeed": "1.3.6.1.2.1.2.2.1.5",
            "ifPhysAddress": "1.3.6.1.2.1.2.2.1.6",
            "ifAdminStatus": "1.3.6.1.2.1.2.2.1.7",
            "ifOperStatus": "1.3.6.1.2.1.2.2.1.8",
            "ifInOctets": "1.3.6.1.2.1.2.2.1.10",
            "ifOutOctets": "1.3.6.1.2.1.2.2.1.16",
            "ifInErrors": "1.3.6.1.2.1.2.2.1.14",
            "ifOutErrors": "1.3.6.1.2.1.2.2.1.20",
            "ifInDiscards": "1.3.6.1.2.1.2.2.1.13",
            "ifOutDiscards": "1.3.6.1.2.1.2.2.1.19",
        }

    def get_monitoring_oids(self) -> Dict[str, str]:
        oids = super().get_monitoring_oids()
        oids.update(self.switch_oids)
        return oids

    def detect_anomaly(self, metrics: Dict[str, Any], thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
        anomalies = []

        # High CPU
        if "cpu_usage" in metrics:
            cpu = metrics["cpu_usage"]
            threshold = thresholds.get("cpu_threshold", 80)
            if cpu > threshold:
                anomalies.append({
                    "type": "high_cpu",
                    "severity": 3,
                    "message": f"High CPU usage: {cpu}%",
                    "value": cpu,
                    "threshold": threshold
                })

        # High memory
        if "memory_usage" in metrics:
            mem = metrics["memory_usage"]
            threshold = thresholds.get("memory_threshold", 85)
            if mem > threshold:
                anomalies.append({
                    "type": "high_memory",
                    "severity": 3,
                    "message": f"High memory usage: {mem}%",
                    "value": mem,
                    "threshold": threshold
                })

        # Interface errors
        if "interface_errors" in metrics:
            errors = metrics["interface_errors"]
            threshold = thresholds.get("interface_errors_threshold", 100)
            if errors > threshold:
                anomalies.append({
                    "type": "interface_errors",
                    "severity": 4,
                    "message": f"High interface errors: {errors}/min",
                    "value": errors,
                    "threshold": threshold
                })

        # Interface down
        if "interfaces_down" in metrics and metrics["interfaces_down"] > 0:
            anomalies.append({
                "type": "interface_down",
                "severity": 4,
                "message": f"{metrics['interfaces_down']} interface(s) down",
                "value": metrics["interfaces_down"]
            })

        return anomalies


class RouterProfile(SwitchProfile):
    """Profile for routers (extends switch)"""

    def __init__(self):
        super().__init__()
        # Additional router-specific OIDs
        self.router_oids = {
            # Routing table
            "ipRouteTable": "1.3.6.1.2.1.4.21",
            "ipRouteNextHop": "1.3.6.1.2.1.4.21.1.7",

            # IP forwarding
            "ipForwarding": "1.3.6.1.2.1.4.1.0",

            # BGP (if supported)
            "bgpPeerState": "1.3.6.1.2.1.15.3.1.2",
        }

    def get_monitoring_oids(self) -> Dict[str, str]:
        oids = super().get_monitoring_oids()
        oids.update(self.router_oids)
        return oids


class FirewallProfile(DeviceProfile):
    """Profile for firewalls"""

    def __init__(self):
        super().__init__()
        # Firewall-specific OIDs (vendor-dependent)
        self.firewall_oids = {
            # Fortinet
            "fgSysCpuUsage": "1.3.6.1.4.1.12356.101.4.1.3.0",
            "fgSysMemUsage": "1.3.6.1.4.1.12356.101.4.1.4.0",
            "fgSysSesCount": "1.3.6.1.4.1.12356.101.4.1.8.0",

            # Checkpoint (if supported)
            # Palo Alto (if supported)
        }

    def get_monitoring_oids(self) -> Dict[str, str]:
        oids = super().get_monitoring_oids()
        oids.update(self.firewall_oids)
        return oids


class UPSProfile(DeviceProfile):
    """Profile for UPS devices"""

    def __init__(self):
        super().__init__()
        # UPS MIB (RFC 1628)
        self.ups_oids = {
            # Battery
            "upsBatteryStatus": "1.3.6.1.2.1.33.1.2.1.0",
            "upsSecondsOnBattery": "1.3.6.1.2.1.33.1.2.2.0",
            "upsEstimatedMinutesRemaining": "1.3.6.1.2.1.33.1.2.3.0",
            "upsEstimatedChargeRemaining": "1.3.6.1.2.1.33.1.2.4.0",
            "upsBatteryVoltage": "1.3.6.1.2.1.33.1.2.5.0",
            "upsBatteryTemperature": "1.3.6.1.2.1.33.1.2.7.0",

            # Input
            "upsInputLineBads": "1.3.6.1.2.1.33.1.3.1.0",
            "upsInputVoltage": "1.3.6.1.2.1.33.1.3.3.1.3.1",
            "upsInputFrequency": "1.3.6.1.2.1.33.1.3.3.1.2.1",

            # Output
            "upsOutputSource": "1.3.6.1.2.1.33.1.4.1.0",
            "upsOutputVoltage": "1.3.6.1.2.1.33.1.4.4.1.2.1",
            "upsOutputCurrent": "1.3.6.1.2.1.33.1.4.4.1.3.1",
            "upsOutputPower": "1.3.6.1.2.1.33.1.4.4.1.4.1",
            "upsOutputPercentLoad": "1.3.6.1.2.1.33.1.4.4.1.5.1",
        }

    def get_monitoring_oids(self) -> Dict[str, str]:
        oids = super().get_monitoring_oids()
        oids.update(self.ups_oids)
        return oids

    def detect_anomaly(self, metrics: Dict[str, Any], thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
        anomalies = []

        # Battery low
        if "battery_charge" in metrics:
            charge = metrics["battery_charge"]
            threshold = thresholds.get("battery_low_threshold", 30)
            if charge < threshold:
                anomalies.append({
                    "type": "low_battery",
                    "severity": 4,
                    "message": f"Low battery charge: {charge}%",
                    "value": charge,
                    "threshold": threshold
                })

        # On battery
        if "on_battery" in metrics and metrics["on_battery"]:
            anomalies.append({
                "type": "on_battery",
                "severity": 4,
                "message": "UPS is running on battery power",
                "value": True
            })

        # High load
        if "load_percent" in metrics:
            load = metrics["load_percent"]
            if load > 90:
                anomalies.append({
                    "type": "high_load",
                    "severity": 3,
                    "message": f"High UPS load: {load}%",
                    "value": load
                })

        return anomalies


# Profile registry
DEVICE_PROFILES = {
    "printer": PrinterProfile,
    "switch": SwitchProfile,
    "router": RouterProfile,
    "firewall": FirewallProfile,
    "ups": UPSProfile,
}


def get_device_profile(device_type: str) -> DeviceProfile:
    """Get device profile by type"""
    profile_class = DEVICE_PROFILES.get(device_type, DeviceProfile)
    return profile_class()
