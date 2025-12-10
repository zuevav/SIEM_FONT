"""
Pydantic schemas for Alerts and Detection Rules
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# DETECTION RULES
# ============================================================================

class DetectionRuleCreate(BaseModel):
    """Schema for creating a detection rule"""
    rule_name: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_enabled: bool = Field(default=True)

    # Priority
    severity: int = Field(default=2, ge=0, le=4)
    priority: int = Field(default=50, ge=1, le=100)

    # Rule Type
    rule_type: str = Field(..., pattern="^(simple|threshold|correlation|sigma|ml)$")
    rule_logic: str  # JSON or YAML

    # Time Parameters
    time_window_minutes: Optional[int] = Field(None, ge=1)
    threshold_count: Optional[int] = Field(None, ge=1)
    group_by_fields: Optional[List[str]]

    # Conditions
    source_types: Optional[List[str]]
    event_codes: Optional[List[int]]
    categories: Optional[List[str]]

    # Actions
    actions: Optional[Dict[str, Any]]
    auto_escalate: bool = Field(default=False)

    # MITRE ATT&CK
    mitre_attack_tactic: Optional[str]
    mitre_attack_technique: Optional[str]
    mitre_attack_subtechnique: Optional[str]

    # Exceptions
    exceptions: Optional[Dict[str, Any]]

    tags: Optional[List[str]]


class DetectionRuleUpdate(BaseModel):
    """Schema for updating a detection rule"""
    rule_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_enabled: Optional[bool]
    severity: Optional[int] = Field(None, ge=0, le=4)
    priority: Optional[int] = Field(None, ge=1, le=100)
    rule_logic: Optional[str]
    time_window_minutes: Optional[int]
    threshold_count: Optional[int]
    auto_escalate: Optional[bool]
    tags: Optional[List[str]]


class DetectionRuleResponse(BaseModel):
    """Detection rule response schema"""
    rule_id: int
    rule_name: str
    description: Optional[str]
    is_enabled: bool
    severity: int
    priority: int
    rule_type: str
    mitre_attack_tactic: Optional[str]
    mitre_attack_technique: Optional[str]
    total_matches: int
    false_positives: int
    last_match: Optional[datetime]
    created_at: datetime
    tags: Optional[List[str]]

    class Config:
        orm_mode = True
        from_attributes = True


class DetectionRuleDetail(DetectionRuleResponse):
    """Detailed detection rule information"""
    rule_logic: str
    time_window_minutes: Optional[int]
    threshold_count: Optional[int]
    group_by_fields: Optional[List[str]]
    source_types: Optional[List[str]]
    event_codes: Optional[List[int]]
    categories: Optional[List[str]]
    actions: Optional[Dict[str, Any]]
    auto_escalate: bool
    mitre_attack_subtechnique: Optional[str]
    exceptions: Optional[Dict[str, Any]]
    created_by: Optional[int]
    updated_by: Optional[int]
    updated_at: Optional[datetime]


# ============================================================================
# ALERTS
# ============================================================================

class AlertCreate(BaseModel):
    """Schema for creating an alert (usually from detection engine)"""
    rule_id: Optional[int]
    severity: int = Field(..., ge=0, le=4)
    title: str = Field(..., max_length=500)
    description: Optional[str]
    category: Optional[str] = Field(None, max_length=50)

    # Related Events
    event_ids: List[int]
    first_event_time: Optional[datetime]
    last_event_time: Optional[datetime]

    # Context
    agent_id: Optional[UUID]
    hostname: Optional[str]
    username: Optional[str]
    source_ip: Optional[str]
    target_ip: Optional[str]
    process_name: Optional[str]

    # MITRE ATT&CK
    mitre_attack_tactic: Optional[str]
    mitre_attack_technique: Optional[str]
    mitre_attack_subtechnique: Optional[str]

    # AI Analysis
    ai_analysis: Optional[Dict[str, Any]]
    ai_recommendations: Optional[str]
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=100.0)


class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    status: Optional[str] = Field(None, pattern="^(new|acknowledged|investigating|resolved|false_positive)$")
    assigned_to: Optional[int]
    priority: Optional[int] = Field(None, ge=1, le=4)
    incident_id: Optional[int]

    # Comments
    comment: Optional[str]
    action_taken: Optional[str]

    # CBR Compliance
    operational_risk_category: Optional[str]
    estimated_damage_rub: Optional[float]
    is_reportable: Optional[bool]


class AlertResponse(BaseModel):
    """Alert response schema"""
    alert_id: int
    alert_guid: UUID
    rule_id: Optional[int]
    severity: int
    title: str
    description: Optional[str]
    category: Optional[str]
    event_count: int
    first_event_time: Optional[datetime]
    last_event_time: Optional[datetime]
    hostname: Optional[str]
    username: Optional[str]
    source_ip: Optional[str]
    target_ip: Optional[str]
    status: str
    assigned_to: Optional[int]
    priority: int
    incident_id: Optional[int]
    created_at: datetime
    mitre_attack_tactic: Optional[str]
    mitre_attack_technique: Optional[str]

    class Config:
        orm_mode = True
        from_attributes = True


class AlertDetail(AlertResponse):
    """Detailed alert information"""
    alert_guid: UUID
    event_ids: Optional[List[int]]
    agent_id: Optional[UUID]
    process_name: Optional[str]
    mitre_attack_subtechnique: Optional[str]
    ai_analysis: Optional[Dict[str, Any]]
    ai_recommendations: Optional[str]
    ai_confidence: Optional[float]
    comments: Optional[List[Dict[str, Any]]]
    actions_taken: Optional[List[Dict[str, Any]]]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    updated_at: Optional[datetime]
    operational_risk_category: Optional[str]
    estimated_damage_rub: Optional[float]
    is_reportable: bool


class AlertStatistics(BaseModel):
    """Alert statistics"""
    total_alerts: int
    new_alerts: int
    acknowledged_alerts: int
    investigating_alerts: int
    resolved_alerts: int
    false_positives: int
    alerts_by_severity: Dict[str, int]
    alerts_by_category: Dict[str, int]
    alerts_by_status: Dict[str, int]
    top_rules: List[Dict[str, Any]]
    recent_alerts: List[AlertResponse]


class AlertFilter(BaseModel):
    """Schema for filtering alerts"""
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    min_severity: Optional[int] = Field(None, ge=0, le=4)
    status: Optional[str]
    category: Optional[str]
    rule_id: Optional[int]
    assigned_to: Optional[int]
    incident_id: Optional[int]
    hostname: Optional[str]
    username: Optional[str]
    source_ip: Optional[str]
    mitre_tactic: Optional[str]
    is_reportable: Optional[bool]
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# ============================================================================
# ALERT ACTIONS
# ============================================================================

class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert"""
    comment: Optional[str]


class AlertResolve(BaseModel):
    """Schema for resolving an alert"""
    resolution: str = Field(..., pattern="^(resolved|false_positive)$")
    comment: Optional[str]
    lessons_learned: Optional[str]


class AlertEscalate(BaseModel):
    """Schema for escalating alert to incident"""
    incident_id: Optional[int] = Field(None, description="Existing incident ID, or null to create new")
    comment: Optional[str]


class AlertAssign(BaseModel):
    """Schema for assigning alert to user"""
    user_id: int
    comment: Optional[str]


class AlertComment(BaseModel):
    """Schema for adding comment to alert"""
    comment: str = Field(..., max_length=2000)
    action_taken: Optional[str]
