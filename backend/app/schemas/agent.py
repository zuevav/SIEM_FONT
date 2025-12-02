"""
Pydantic schemas for Agents and Assets
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID


class AgentRegister(BaseModel):
    """Schema for agent registration"""
    hostname: str = Field(..., min_length=1, max_length=255)
    fqdn: Optional[str]
    ip_address: Optional[str]
    mac_address: Optional[str]
    os_version: Optional[str]
    os_build: Optional[str]
    os_architecture: Optional[str]
    domain: Optional[str]
    organizational_unit: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]
    cpu_model: Optional[str]
    cpu_cores: Optional[int]
    total_ram_mb: Optional[int]
    total_disk_gb: Optional[int]
    agent_version: str
    last_reboot: Optional[datetime]
    tags: Optional[List[str]]
    location: Optional[str]
    owner: Optional[str]

    class Config:
        schema_extra = {
            "example": {
                "hostname": "WS-001",
                "fqdn": "ws-001.company.local",
                "ip_address": "192.168.1.100",
                "os_version": "Windows 11 Pro",
                "agent_version": "1.0.0",
                "domain": "company.local"
            }
        }


class AgentHeartbeat(BaseModel):
    """Schema for agent heartbeat"""
    agent_id: UUID
    status: str = "online"
    agent_version: Optional[str]


class AgentUpdate(BaseModel):
    """Schema for agent update"""
    fqdn: Optional[str]
    ip_address: Optional[str]
    status: Optional[str]
    location: Optional[str]
    owner: Optional[str]
    criticality_level: Optional[str]
    tags: Optional[List[str]]

    @validator('status')
    def validate_status(cls, v):
        if v and v not in ['online', 'offline', 'error', 'installing']:
            raise ValueError('Invalid status')
        return v

    @validator('criticality_level')
    def validate_criticality(cls, v):
        if v and v not in ['critical', 'high', 'medium', 'low']:
            raise ValueError('Invalid criticality level')
        return v


class AgentResponse(BaseModel):
    """Agent response schema"""
    agent_id: UUID
    hostname: str
    fqdn: Optional[str]
    ip_address: Optional[str]
    os_version: Optional[str]
    domain: Optional[str]
    agent_version: Optional[str]
    status: str
    last_seen: datetime
    last_inventory: Optional[datetime]
    registered_at: datetime
    location: Optional[str]
    owner: Optional[str]
    criticality_level: str

    class Config:
        orm_mode = True
        from_attributes = True


class AgentDetail(AgentResponse):
    """Detailed agent information"""
    mac_address: Optional[str]
    os_build: Optional[str]
    os_architecture: Optional[str]
    organizational_unit: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]
    cpu_model: Optional[str]
    cpu_cores: Optional[int]
    total_ram_mb: Optional[int]
    total_disk_gb: Optional[int]
    last_reboot: Optional[datetime]
    configuration: Optional[Dict[str, Any]]
    tags: Optional[List[str]]


class SoftwareItem(BaseModel):
    """Installed software item"""
    name: str
    version: Optional[str]
    publisher: Optional[str]
    install_date: Optional[date]
    install_location: Optional[str]
    uninstall_string: Optional[str]
    estimated_size_kb: Optional[int]


class SoftwareInventory(BaseModel):
    """Software inventory update"""
    agent_id: UUID
    software_list: List[SoftwareItem]


class InstalledSoftwareResponse(BaseModel):
    """Installed software response"""
    install_id: int
    agent_id: UUID
    name: str
    version: Optional[str]
    publisher: Optional[str]
    install_date: Optional[date]
    is_active: bool
    first_seen_at: datetime
    last_seen_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class WindowsServiceItem(BaseModel):
    """Windows service item"""
    service_name: str
    display_name: Optional[str]
    status: Optional[str]
    start_type: Optional[str]
    service_account: Optional[str]
    executable_path: Optional[str]


class ServicesInventory(BaseModel):
    """Services inventory update"""
    agent_id: UUID
    services: List[WindowsServiceItem]


class AgentStatistics(BaseModel):
    """Agent statistics"""
    total_agents: int
    online_agents: int
    offline_agents: int
    error_agents: int
    agents_by_os: Dict[str, int]
    agents_by_domain: Dict[str, int]
    agents_by_location: Dict[str, int]


class AssetChangeResponse(BaseModel):
    """Asset change response"""
    change_id: int
    agent_id: UUID
    change_type: str
    change_details: Dict[str, Any]
    detected_at: datetime
    severity: int

    class Config:
        orm_mode = True
        from_attributes = True
