"""
Pydantic schemas for SOAR Playbooks
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.playbook import ActionType, ActionStatus, PlaybookStatus


# ============================================================================
# Playbook Schemas
# ============================================================================

class PlaybookBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_on_severity: Optional[List[int]] = None
    trigger_on_mitre_tactic: Optional[List[str]] = None
    action_ids: Optional[List[int]] = None
    requires_approval: bool = False
    is_enabled: bool = True


class PlaybookCreate(PlaybookBase):
    pass


class PlaybookUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_on_severity: Optional[List[int]] = None
    trigger_on_mitre_tactic: Optional[List[str]] = None
    action_ids: Optional[List[int]] = None
    requires_approval: Optional[bool] = None
    is_enabled: Optional[bool] = None


class PlaybookResponse(PlaybookBase):
    playbook_id: int
    execution_count: int
    success_count: int
    failure_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Playbook Action Schemas
# ============================================================================

class PlaybookActionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    action_type: ActionType
    config: Dict[str, Any] = Field(..., description="Action configuration (JSON)")
    timeout_seconds: int = Field(300, ge=1, le=3600)
    retry_count: int = Field(0, ge=0, le=5)


class PlaybookActionCreate(PlaybookActionBase):
    pass


class PlaybookActionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    action_type: Optional[ActionType] = None
    config: Optional[Dict[str, Any]] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=3600)
    retry_count: Optional[int] = Field(None, ge=0, le=5)


class PlaybookActionResponse(PlaybookActionBase):
    action_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Playbook Execution Schemas
# ============================================================================

class PlaybookExecutionBase(BaseModel):
    playbook_id: int
    alert_id: Optional[int] = None
    incident_id: Optional[int] = None


class PlaybookExecutionCreate(PlaybookExecutionBase):
    pass


class PlaybookExecutionResponse(PlaybookExecutionBase):
    execution_id: int
    status: PlaybookStatus
    started_at: datetime
    completed_at: Optional[datetime]
    execution_log: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class PlaybookExecutionApprove(BaseModel):
    approved: bool
    comment: Optional[str] = None


# ============================================================================
# Action Result Schemas
# ============================================================================

class ActionResultResponse(BaseModel):
    result_id: int
    execution_id: int
    action_id: int
    status: ActionStatus
    started_at: datetime
    completed_at: Optional[datetime]
    output: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: Optional[int]

    class Config:
        from_attributes = True


# ============================================================================
# List Responses
# ============================================================================

class PlaybookListResponse(BaseModel):
    items: List[PlaybookResponse]
    total: int
    page: int
    page_size: int


class PlaybookActionListResponse(BaseModel):
    items: List[PlaybookActionResponse]
    total: int
    page: int
    page_size: int


class PlaybookExecutionListResponse(BaseModel):
    items: List[PlaybookExecutionResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Statistics Schemas
# ============================================================================

class PlaybookStats(BaseModel):
    total_playbooks: int
    enabled_playbooks: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    pending_approvals: int
    avg_execution_time_seconds: Optional[float]


class ActionTypeStats(BaseModel):
    action_type: ActionType
    total_executions: int
    successful: int
    failed: int
    avg_duration_seconds: Optional[float]
