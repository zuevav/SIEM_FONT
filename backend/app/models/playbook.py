"""
SOAR Playbook Models
Automated response workflows for security incidents
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, ARRAY, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import json

from app.core.database import Base


class PlaybookStatus(str, enum.Enum):
    """Playbook execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class ActionType(str, enum.Enum):
    """Types of actions that can be executed"""
    # Network actions
    BLOCK_IP = "block_ip"
    BLOCK_DOMAIN = "block_domain"
    ISOLATE_HOST = "isolate_host"

    # Process actions
    KILL_PROCESS = "kill_process"
    QUARANTINE_FILE = "quarantine_file"

    # User actions
    DISABLE_USER_ACCOUNT = "disable_user_account"
    RESET_PASSWORD = "reset_password"

    # Communication actions
    SEND_EMAIL = "send_email"
    CREATE_TICKET = "create_ticket"
    NOTIFY_SLACK = "notify_slack"
    NOTIFY_TELEGRAM = "notify_telegram"

    # System actions
    RUN_SCRIPT = "run_script"
    COLLECT_FORENSICS = "collect_forensics"
    SNAPSHOT_VM = "snapshot_vm"
    BACKUP_LOGS = "backup_logs"
    UPDATE_ALERT = "update_alert"
    ESCALATE_INCIDENT = "escalate_incident"
    ADD_TO_BLACKLIST = "add_to_blacklist"

    # Control flow
    WAIT = "wait"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    PARALLEL = "parallel"


class ActionStatus(str, enum.Enum):
    """Action execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class Playbook(Base):
    """
    SOAR Playbook - Automated response workflow
    """
    __tablename__ = "playbooks"
    __table_args__ = {'schema': 'automation'}

    # Primary Key
    playbook_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Basic Info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Trigger Conditions
    trigger_on_severity = Column(ARRAY(Integer), nullable=True)  # [3, 4] = High and Critical
    trigger_on_mitre_tactic = Column(ARRAY(String(100)), nullable=True)  # ['TA0001']
    trigger_on_rule_name = Column(ARRAY(String(255)), nullable=True)  # Specific rule names
    trigger_conditions = Column(JSONB, nullable=True)  # Advanced JSON conditions

    # Actions (array of action IDs in execution order)
    action_ids = Column(ARRAY(Integer), nullable=True)

    # Approval Workflow
    requires_approval = Column(Boolean, default=False, nullable=False)
    auto_approve_for_severity = Column(ARRAY(Integer), nullable=True)  # Auto-approve for Critical

    # Status
    is_enabled = Column(Boolean, default=True, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    # Metadata
    created_by = Column(Integer, ForeignKey('config.users.user_id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    last_executed_at = Column(DateTime, nullable=True)

    # Statistics
    execution_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)

    # Tags
    tags = Column(ARRAY(String(50)), nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    executions = relationship("PlaybookExecution", back_populates="playbook", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Playbook(id={self.playbook_id}, name='{self.name}', enabled={self.is_enabled})>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "playbook_id": self.playbook_id,
            "name": self.name,
            "description": self.description,
            "trigger_on_severity": self.trigger_on_severity,
            "trigger_on_mitre_tactic": self.trigger_on_mitre_tactic,
            "trigger_on_rule_name": self.trigger_on_rule_name,
            "trigger_conditions": self.trigger_conditions,
            "action_ids": self.action_ids,
            "requires_approval": self.requires_approval,
            "auto_approve_for_severity": self.auto_approve_for_severity,
            "is_enabled": self.is_enabled,
            "is_deleted": self.is_deleted,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "tags": self.tags,
        }


class PlaybookAction(Base):
    """
    Playbook Action - Individual step in a playbook
    """
    __tablename__ = "playbook_actions"
    __table_args__ = {'schema': 'automation'}

    # Primary Key
    action_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Basic Info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Action Type
    action_type = Column(String(50), nullable=False, index=True)

    # Configuration (JSON with type-specific params)
    config = Column(JSONB, nullable=False)

    # Execution Settings
    timeout_seconds = Column(Integer, default=300, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    retry_delay_seconds = Column(Integer, default=60, nullable=False)
    continue_on_failure = Column(Boolean, default=False, nullable=False)

    # Rollback
    rollback_action_id = Column(Integer, ForeignKey('automation.playbook_actions.action_id'), nullable=True)

    # Status
    is_enabled = Column(Boolean, default=True, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    # Metadata
    created_by = Column(Integer, ForeignKey('config.users.user_id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    rollback_action = relationship("PlaybookAction", remote_side=[action_id])
    results = relationship("ActionResult", back_populates="action", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PlaybookAction(id={self.action_id}, name='{self.name}', type='{self.action_type}')>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "action_type": self.action_type,
            "config": self.config,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "retry_delay_seconds": self.retry_delay_seconds,
            "continue_on_failure": self.continue_on_failure,
            "rollback_action_id": self.rollback_action_id,
            "is_enabled": self.is_enabled,
            "is_deleted": self.is_deleted,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PlaybookExecution(Base):
    """
    Playbook Execution - History of playbook runs
    """
    __tablename__ = "playbook_executions"
    __table_args__ = {'schema': 'automation'}

    # Primary Key
    execution_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Playbook
    playbook_id = Column(Integer, ForeignKey('automation.playbooks.playbook_id'), nullable=False, index=True)

    # Trigger Source
    alert_id = Column(Integer, ForeignKey('incidents.alerts.alert_id'), nullable=True, index=True)
    incident_id = Column(Integer, ForeignKey('incidents.incidents.incident_id'), nullable=True, index=True)
    triggered_by_user_id = Column(Integer, ForeignKey('config.users.user_id'), nullable=True)

    # Status
    status = Column(String(20), default='pending', nullable=False, index=True)

    # Timeline
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Approval Workflow
    requires_approval = Column(Boolean, default=False, nullable=False)
    approved_by_user_id = Column(Integer, ForeignKey('config.users.user_id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_comment = Column(Text, nullable=True)

    # Results
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_log = Column(JSONB, nullable=True)

    # Rollback
    rolled_back = Column(Boolean, default=False, nullable=False)
    rollback_execution_id = Column(Integer, ForeignKey('automation.playbook_executions.execution_id'), nullable=True)
    rollback_reason = Column(Text, nullable=True)

    # Relationships
    playbook = relationship("Playbook", back_populates="executions")
    alert = relationship("Alert", foreign_keys=[alert_id])
    incident = relationship("Incident", foreign_keys=[incident_id])
    triggered_by_user = relationship("User", foreign_keys=[triggered_by_user_id])
    approved_by_user = relationship("User", foreign_keys=[approved_by_user_id])
    action_results = relationship("ActionResult", back_populates="execution", cascade="all, delete-orphan")
    rollback_execution = relationship("PlaybookExecution", remote_side=[execution_id])

    def __repr__(self):
        return f"<PlaybookExecution(id={self.execution_id}, playbook_id={self.playbook_id}, status='{self.status}')>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "execution_id": self.execution_id,
            "playbook_id": self.playbook_id,
            "alert_id": self.alert_id,
            "incident_id": self.incident_id,
            "triggered_by_user_id": self.triggered_by_user_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "requires_approval": self.requires_approval,
            "approved_by_user_id": self.approved_by_user_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approval_comment": self.approval_comment,
            "success": self.success,
            "error_message": self.error_message,
            "execution_log": self.execution_log,
            "rolled_back": self.rolled_back,
            "rollback_execution_id": self.rollback_execution_id,
            "rollback_reason": self.rollback_reason,
        }


class ActionResult(Base):
    """
    Action Result - Result of individual action execution
    """
    __tablename__ = "action_results"
    __table_args__ = {'schema': 'automation'}

    # Primary Key
    result_id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # References
    execution_id = Column(Integer, ForeignKey('automation.playbook_executions.execution_id'), nullable=False, index=True)
    action_id = Column(Integer, ForeignKey('automation.playbook_actions.action_id'), nullable=False, index=True)

    # Execution Order
    sequence_number = Column(Integer, nullable=False)

    # Status
    status = Column(String(20), nullable=False, index=True)

    # Timeline
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Results
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Output Variables (for chaining actions)
    output_variables = Column(JSONB, nullable=True)

    # Relationships
    execution = relationship("PlaybookExecution", back_populates="action_results")
    action = relationship("PlaybookAction", back_populates="results")

    def __repr__(self):
        return f"<ActionResult(id={self.result_id}, execution_id={self.execution_id}, action_id={self.action_id}, status='{self.status}')>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "result_id": self.result_id,
            "execution_id": self.execution_id,
            "action_id": self.action_id,
            "sequence_number": self.sequence_number,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "result": self.result,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "output_variables": self.output_variables,
        }
