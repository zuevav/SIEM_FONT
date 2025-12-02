"""
Pydantic schemas for Events
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class EventCreate(BaseModel):
    """Schema for creating an event"""
    agent_id: UUID
    event_time: datetime
    source_type: str = Field(..., max_length=50)
    event_code: Optional[int]
    channel: Optional[str]
    provider: Optional[str]
    computer: Optional[str]

    # Normalized fields
    severity: int = Field(default=0, ge=0, le=4)
    category: Optional[str]
    action: Optional[str]
    outcome: Optional[str]

    # Subject
    subject_user: Optional[str]
    subject_domain: Optional[str]
    subject_sid: Optional[str]
    subject_logon_id: Optional[str]

    # Target
    target_user: Optional[str]
    target_domain: Optional[str]
    target_host: Optional[str]
    target_ip: Optional[str]
    target_port: Optional[int]

    # Process
    process_name: Optional[str]
    process_id: Optional[int]
    process_path: Optional[str]
    process_command_line: Optional[str]
    process_hash: Optional[str]

    # Parent Process
    parent_process_name: Optional[str]
    parent_process_id: Optional[int]
    parent_process_path: Optional[str]
    parent_process_command_line: Optional[str]

    # Network
    source_ip: Optional[str]
    source_port: Optional[int]
    source_hostname: Optional[str]
    destination_ip: Optional[str]
    destination_port: Optional[int]
    destination_hostname: Optional[str]
    protocol: Optional[str]

    # DNS
    dns_query: Optional[str]
    dns_response: Optional[str]

    # File
    file_path: Optional[str]
    file_name: Optional[str]
    file_hash: Optional[str]
    file_extension: Optional[str]
    file_size: Optional[int]

    # Registry
    registry_path: Optional[str]
    registry_key: Optional[str]
    registry_value: Optional[str]
    registry_value_type: Optional[str]

    # Additional
    message: Optional[str]
    raw_event: Optional[Dict[str, Any]]
    tags: Optional[List[str]]

    # MITRE ATT&CK
    mitre_attack_tactic: Optional[str]
    mitre_attack_technique: Optional[str]
    mitre_attack_subtechnique: Optional[str]

    # GeoIP
    geo_country: Optional[str]
    geo_city: Optional[str]

    @validator('severity')
    def validate_severity(cls, v):
        if v < 0 or v > 4:
            raise ValueError('Severity must be between 0 and 4')
        return v


class EventBatchCreate(BaseModel):
    """Schema for batch event creation"""
    events: List[EventCreate] = Field(..., max_items=1000)


class EventFilter(BaseModel):
    """Schema for filtering events"""
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    agent_id: Optional[UUID]
    min_severity: Optional[int] = Field(None, ge=0, le=4)
    categories: Optional[List[str]]
    source_types: Optional[List[str]]
    subject_user: Optional[str]
    source_ip: Optional[str]
    destination_ip: Optional[str]
    process_name: Optional[str]
    search_text: Optional[str]
    mitre_tactic: Optional[str]
    mitre_technique: Optional[str]
    ai_processed: Optional[bool]
    ai_is_attack: Optional[bool]
    limit: int = Field(default=100, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


class EventResponse(BaseModel):
    """Event response schema"""
    event_id: int
    event_guid: UUID
    agent_id: UUID
    event_time: datetime
    received_time: datetime
    source_type: str
    event_code: Optional[int]
    severity: int
    category: Optional[str]
    action: Optional[str]
    subject_user: Optional[str]
    target_user: Optional[str]
    target_ip: Optional[str]
    process_name: Optional[str]
    source_ip: Optional[str]
    destination_ip: Optional[str]
    message: Optional[str]
    mitre_attack_tactic: Optional[str]
    mitre_attack_technique: Optional[str]
    ai_score: Optional[float]
    ai_category: Optional[str]
    ai_description: Optional[str]

    class Config:
        orm_mode = True
        from_attributes = True


class EventDetail(EventResponse):
    """Detailed event information"""
    channel: Optional[str]
    provider: Optional[str]
    computer: Optional[str]
    outcome: Optional[str]
    subject_domain: Optional[str]
    subject_sid: Optional[str]
    target_domain: Optional[str]
    target_host: Optional[str]
    target_port: Optional[int]
    process_id: Optional[int]
    process_path: Optional[str]
    process_command_line: Optional[str]
    process_hash: Optional[str]
    parent_process_name: Optional[str]
    parent_process_id: Optional[int]
    source_port: Optional[int]
    destination_port: Optional[int]
    protocol: Optional[str]
    dns_query: Optional[str]
    file_path: Optional[str]
    file_hash: Optional[str]
    registry_path: Optional[str]
    raw_event: Optional[Dict[str, Any]]
    tags: Optional[List[str]]
    ai_confidence: Optional[float]
    ai_is_attack: Optional[bool]
    geo_country: Optional[str]
    geo_city: Optional[str]


class EventStatistics(BaseModel):
    """Event statistics"""
    total_events: int
    critical_events: int
    high_events: int
    medium_events: int
    low_events: int
    events_by_severity: Dict[str, int]
    events_by_category: Dict[str, int]
    events_by_source: Dict[str, int]
    top_agents: List[Dict[str, Any]]
    top_users: List[Dict[str, Any]]
    top_processes: List[Dict[str, Any]]


class EventsTimelineData(BaseModel):
    """Events timeline data for charts"""
    timestamp: datetime
    severity: int
    count: int


class EventsTimeline(BaseModel):
    """Events timeline response"""
    data: List[EventsTimelineData]
    start_time: datetime
    end_time: datetime
    interval: str  # hour, day, week
