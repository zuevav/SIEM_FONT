"""
Pydantic schemas for Incidents
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class IncidentCreate(BaseModel):
    """Schema for creating an incident"""
    title: str = Field(..., max_length=500)
    description: Optional[str]
    severity: int = Field(..., ge=0, le=4)
    category: str = Field(..., max_length=50)  # intrusion, malware, data_breach, policy_violation

    # Related Alerts
    alert_ids: Optional[List[int]]

    # Affected Systems
    affected_agents: Optional[List[str]]  # Agent IDs
    affected_users: Optional[List[str]]

    # Timeline
    start_time: Optional[datetime]
    end_time: Optional[datetime]

    # Assignment
    assigned_to: Optional[int]
    priority: int = Field(default=2, ge=1, le=4)

    # MITRE ATT&CK
    mitre_attack_tactics: Optional[List[str]]
    mitre_attack_techniques: Optional[List[str]]

    # CBR Compliance
    operational_risk_category: Optional[str]
    estimated_damage_rub: Optional[float]


class IncidentUpdate(BaseModel):
    """Schema for updating an incident"""
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str]
    severity: Optional[int] = Field(None, ge=0, le=4)
    category: Optional[str]
    status: Optional[str] = Field(None, regex="^(open|investigating|contained|resolved|closed)$")
    priority: Optional[int] = Field(None, ge=1, le=4)
    assigned_to: Optional[int]
    start_time: Optional[datetime]
    end_time: Optional[datetime]

    # CBR Compliance
    operational_risk_category: Optional[str]
    estimated_damage_rub: Optional[float]
    actual_damage_rub: Optional[float]


class IncidentResponse(BaseModel):
    """Incident response schema"""
    incident_id: int
    incident_guid: UUID
    title: str
    description: Optional[str]
    severity: int
    category: str
    status: str
    priority: int
    alert_count: int
    event_count: int
    affected_assets: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    detected_at: datetime
    assigned_to: Optional[int]
    mitre_attack_tactics: Optional[List[str]]
    mitre_attack_techniques: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True
        from_attributes = True


class IncidentDetail(IncidentResponse):
    """Detailed incident information"""
    affected_agents: Optional[List[str]]
    affected_users: Optional[List[str]]
    ai_summary: Optional[str]
    ai_timeline: Optional[Dict[str, Any]]
    ai_root_cause: Optional[str]
    ai_recommendations: Optional[str]
    ai_impact_assessment: Optional[str]
    attack_chain: Optional[Dict[str, Any]]
    containment_actions: Optional[List[Dict[str, Any]]]
    remediation_actions: Optional[List[Dict[str, Any]]]
    lessons_learned: Optional[str]
    work_log: Optional[List[Dict[str, Any]]]
    operational_risk_category: Optional[str]
    estimated_damage_rub: Optional[float]
    actual_damage_rub: Optional[float]
    is_reported_to_cbr: bool
    cbr_report_date: Optional[datetime]
    cbr_incident_number: Optional[str]
    closed_at: Optional[datetime]


class IncidentStatistics(BaseModel):
    """Incident statistics"""
    total_incidents: int
    open_incidents: int
    investigating_incidents: int
    contained_incidents: int
    resolved_incidents: int
    closed_incidents: int
    critical_incidents: int
    incidents_by_severity: Dict[str, int]
    incidents_by_category: Dict[str, int]
    incidents_by_status: Dict[str, int]
    avg_resolution_time_hours: Optional[float]
    incidents_this_month: int
    incidents_last_month: int


class IncidentFilter(BaseModel):
    """Schema for filtering incidents"""
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    min_severity: Optional[int] = Field(None, ge=0, le=4)
    status: Optional[str]
    category: Optional[str]
    assigned_to: Optional[int]
    mitre_tactic: Optional[str]
    is_reported_to_cbr: Optional[bool]
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class IncidentWorkLogEntry(BaseModel):
    """Schema for adding work log entry"""
    entry: str = Field(..., max_length=5000)
    entry_type: str = Field(default="note", regex="^(note|action|milestone)$")


class IncidentContainmentAction(BaseModel):
    """Schema for adding containment action"""
    action: str = Field(..., max_length=1000)
    timestamp: Optional[datetime]
    performed_by: Optional[str]
    result: Optional[str]


class IncidentRemediationAction(BaseModel):
    """Schema for adding remediation action"""
    action: str = Field(..., max_length=1000)
    timestamp: Optional[datetime]
    performed_by: Optional[str]
    result: Optional[str]
    verified: bool = Field(default=False)


class IncidentClose(BaseModel):
    """Schema for closing an incident"""
    lessons_learned: Optional[str]
    actual_damage_rub: Optional[float]
    final_notes: Optional[str]


class IncidentCBRReport(BaseModel):
    """Schema for CBR incident reporting"""
    cbr_incident_number: str = Field(..., max_length=100)
    operational_risk_category: str = Field(..., max_length=100)
    actual_damage_rub: Optional[float]
    report_notes: Optional[str]


class IncidentTimelineEntry(BaseModel):
    """Timeline entry for incident visualization"""
    timestamp: datetime
    event_type: str  # alert, containment, remediation, status_change
    title: str
    description: Optional[str]
    severity: Optional[int]
    related_alert_id: Optional[int]


class IncidentTimeline(BaseModel):
    """Incident timeline response"""
    incident_id: int
    timeline: List[IncidentTimelineEntry]
    start_time: datetime
    end_time: Optional[datetime]


class IncidentCorrelation(BaseModel):
    """Incident correlation result"""
    incident_id: int
    related_incidents: List[IncidentResponse]
    correlation_score: float
    correlation_factors: List[str]  # shared_agents, shared_users, shared_tactics, temporal_proximity


class IncidentExport(BaseModel):
    """Schema for incident export (CBR/FinCERT format)"""
    format: str = Field(..., regex="^(json|xml|pdf|xlsx)$")
    include_events: bool = Field(default=False)
    include_alerts: bool = Field(default=True)
    include_timeline: bool = Field(default=True)
    cbr_format: bool = Field(default=False, description="Format according to CBR requirements")
