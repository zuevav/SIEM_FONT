"""
Configuration module for SIEM Network Monitor
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
import yaml


class SIEMConfig(BaseModel):
    """SIEM Backend configuration"""
    server_url: str = Field(default="http://localhost:8000")
    api_key: str = Field(default="")
    register_on_startup: bool = Field(default=True)
    heartbeat_interval: int = Field(default=60, ge=10)
    batch_size: int = Field(default=100, ge=1, le=1000)
    send_timeout: int = Field(default=30, ge=5)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay: int = Field(default=5, ge=1)
    insecure_skip_verify: bool = Field(default=False)


class SNMPv3Config(BaseModel):
    """SNMP v3 authentication config"""
    username: str = Field(default="snmpuser")
    auth_protocol: str = Field(default="SHA")  # MD5 or SHA
    auth_password: str = Field(default="")
    priv_protocol: str = Field(default="AES")  # DES or AES
    priv_password: str = Field(default="")


class SNMPDeviceConfig(BaseModel):
    """SNMP device configuration"""
    name: str
    ip: str
    type: str  # printer, switch, router, firewall, ups
    enabled: bool = Field(default=True)
    community: Optional[str] = None
    oids: List[str] = Field(default_factory=list)
    monitor: List[str] = Field(default_factory=list)


class SNMPAnomalyConfig(BaseModel):
    """Anomaly detection thresholds"""
    enabled: bool = Field(default=True)
    cpu_threshold: int = Field(default=80, ge=0, le=100)
    memory_threshold: int = Field(default=85, ge=0, le=100)
    interface_errors_threshold: int = Field(default=100, ge=0)
    toner_low_threshold: int = Field(default=20, ge=0, le=100)
    battery_low_threshold: int = Field(default=30, ge=0, le=100)


class SNMPConfig(BaseModel):
    """SNMP configuration"""
    enabled: bool = Field(default=True)
    poll_interval: int = Field(default=60, ge=10)
    timeout: int = Field(default=5, ge=1)
    retries: int = Field(default=2, ge=0, le=5)
    version: str = Field(default="2c")  # 2c or 3
    community: str = Field(default="public")
    v3: SNMPv3Config = Field(default_factory=SNMPv3Config)
    devices: List[SNMPDeviceConfig] = Field(default_factory=list)
    anomaly_detection: SNMPAnomalyConfig = Field(default_factory=SNMPAnomalyConfig)


class SyslogListenerConfig(BaseModel):
    """Syslog listener configuration"""
    protocol: str = Field(default="udp")  # udp or tcp
    port: int = Field(default=514, ge=1, le=65535)
    bind: str = Field(default="0.0.0.0")


class SyslogParserConfig(BaseModel):
    """Syslog parser configuration"""
    vendor: str
    pattern: str
    enabled: bool = Field(default=True)


class SyslogConfig(BaseModel):
    """Syslog receiver configuration"""
    enabled: bool = Field(default=True)
    listeners: List[SyslogListenerConfig] = Field(default_factory=list)
    formats: List[str] = Field(default_factory=lambda: ["rfc3164", "rfc5424"])
    sources: Dict[str, Any] = Field(default_factory=dict)
    parsers: List[SyslogParserConfig] = Field(default_factory=list)


class NetFlowConfig(BaseModel):
    """NetFlow/sFlow configuration"""
    enabled: bool = Field(default=False)
    port: int = Field(default=2055, ge=1, le=65535)
    version: int = Field(default=5)


class PerformanceConfig(BaseModel):
    """Performance settings"""
    max_queue_size: int = Field(default=10000, ge=100)
    snmp_workers: int = Field(default=5, ge=1, le=20)
    send_workers: int = Field(default=3, ge=1, le=10)
    max_cpu_percent: int = Field(default=70, ge=10, le=100)
    max_memory_mb: int = Field(default=1024, ge=128)


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="info")
    file: str = Field(default="/var/log/siem/network_monitor.log")
    max_size_mb: int = Field(default=100, ge=10)
    max_backups: int = Field(default=5, ge=1)
    format: str = Field(default="json")  # json or text
    log_snmp_queries: bool = Field(default=False)
    log_syslog_messages: bool = Field(default=False)


class StorageConfig(BaseModel):
    """Local storage configuration"""
    enabled: bool = Field(default=True)
    path: str = Field(default="/var/lib/siem/network_monitor")
    max_size_mb: int = Field(default=500, ge=50)
    event_ttl_hours: int = Field(default=24, ge=1)


class Config(BaseModel):
    """Main configuration"""
    siem: SIEMConfig = Field(default_factory=SIEMConfig)
    snmp: SNMPConfig = Field(default_factory=SNMPConfig)
    syslog: SyslogConfig = Field(default_factory=SyslogConfig)
    netflow: NetFlowConfig = Field(default_factory=NetFlowConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    @classmethod
    def load(cls, path: str) -> "Config":
        """Load configuration from YAML file"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def get_enabled_devices(self) -> List[SNMPDeviceConfig]:
        """Get list of enabled SNMP devices"""
        return [d for d in self.snmp.devices if d.enabled]

    def get_device_by_name(self, name: str) -> Optional[SNMPDeviceConfig]:
        """Get device by name"""
        for device in self.snmp.devices:
            if device.name == name:
                return device
        return None

    def get_device_by_ip(self, ip: str) -> Optional[SNMPDeviceConfig]:
        """Get device by IP address"""
        for device in self.snmp.devices:
            if device.ip == ip:
                return device
        return None

    def get_devices_by_type(self, device_type: str) -> List[SNMPDeviceConfig]:
        """Get all devices of specific type"""
        return [d for d in self.snmp.devices if d.type == device_type and d.enabled]
