"""
SQLAlchemy models for Alerts and Incidents
Updated for PostgreSQL compatibility
"""

from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Boolean, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class DetectionRule(Base):
    """Detection Rule model - config.detection_rules table"""

    __tablename__ = "detection_rules"
    __table_args__ = {'schema': 'config'}

    # Map Python attributes to PostgreSQL column names
    RuleId = Column('rule_id', Integer, primary_key=True, autoincrement=True)
    RuleName = Column('rule_name', String(200), nullable=False, unique=True)
    Description = Column('description', String(1000))
    IsEnabled = Column('is_enabled', Boolean, default=True, index=True)

    # Priority
    Severity = Column('severity', Integer, default=2)  # 0-4
    Priority = Column('priority', Integer, default=50)  # Execution order

    # Rule Type
    RuleType = Column('rule_type', String(20), nullable=False)
    RuleLogic = Column('rule_logic', Text, nullable=False)

    # Time Parameters
    TimeWindowMinutes = Column('time_window_minutes', Integer)
    ThresholdCount = Column('threshold_count', Integer)
    GroupByFields = Column('group_by_fields', JSONB)

    # Conditions
    SourceTypes = Column('source_types', JSONB)
    EventCodes = Column('event_codes', JSONB)
    Categories = Column('categories', JSONB)

    # Actions
    Actions = Column('actions', JSONB)
    AutoEscalate = Column('auto_escalate', Boolean, default=False)

    # MITRE ATT&CK
    MitreAttackTactic = Column('mitre_attack_tactic', String(50))
    MitreAttackTechnique = Column('mitre_attack_technique', String(20))
    MitreAttackSubtechnique = Column('mitre_attack_subtechnique', String(30))

    # Exceptions
    Exceptions = Column('exceptions', JSONB)

    # Statistics
    TotalMatches = Column('total_matches', BigInteger, default=0)
    FalsePositives = Column('false_positives', Integer, default=0)
    LastMatch = Column('last_match', DateTime)

    # Metadata
    CreatedBy = Column('created_by', Integer, ForeignKey('config.users.user_id'))
    CreatedAt = Column('created_at', DateTime, server_default=func.now())
    UpdatedBy = Column('updated_by', Integer, ForeignKey('config.users.user_id'))
    UpdatedAt = Column('updated_at', DateTime)
    Tags = Column('tags', JSONB)

    # Relationships
    creator = relationship("User", foreign_keys=[CreatedBy], back_populates="created_rules")
    alerts = relationship("Alert", back_populates="rule")

    # Lowercase aliases for compatibility
    @property
    def rule_id(self):
        return self.RuleId

    @property
    def rule_name(self):
        return self.RuleName

    @property
    def is_enabled(self):
        return self.IsEnabled

    def __repr__(self):
        return f"<DetectionRule(id={self.RuleId}, name='{self.RuleName}', enabled={self.IsEnabled})>"


class Alert(Base):
    """Alert model - incidents.alerts table"""

    __tablename__ = "alerts"
    __table_args__ = {'schema': 'incidents'}

    AlertId = Column('alert_id', BigInteger, primary_key=True, autoincrement=True)
    AlertGuid = Column('alert_guid', UUID(as_uuid=True), unique=True, index=True, server_default=func.gen_random_uuid())
    RuleId = Column('rule_id', Integer, ForeignKey('config.detection_rules.rule_id'))

    # Classification
    Severity = Column('severity', Integer, nullable=False, index=True)
    Title = Column('title', String(500), nullable=False)
    Description = Column('description', Text)
    Category = Column('category', String(50))

    # Related Events
    EventIds = Column('event_ids', JSONB)
    EventCount = Column('event_count', Integer, default=1)
    FirstEventTime = Column('first_event_time', DateTime)
    LastEventTime = Column('last_event_time', DateTime)

    # Context
    AgentId = Column('agent_id', UUID(as_uuid=True), ForeignKey('assets.agents.agent_id'), index=True)
    Hostname = Column('hostname', String(255))
    Username = Column('username', String(200))
    SourceIP = Column('source_ip', String(45))
    TargetIP = Column('target_ip', String(45))
    ProcessName = Column('process_name', String(500))

    # MITRE ATT&CK
    MitreAttackTactic = Column('mitre_attack_tactic', String(50))
    MitreAttackTechnique = Column('mitre_attack_technique', String(20))
    MitreAttackSubtechnique = Column('mitre_attack_subtechnique', String(30))

    # Status
    Status = Column('status', String(20), default='new', index=True)
    AssignedTo = Column('assigned_to', Integer, ForeignKey('config.users.user_id'))
    Priority = Column('priority', Integer, default=2)

    # AI Analysis
    AIAnalysis = Column('ai_analysis', JSONB)
    AIRecommendations = Column('ai_recommendations', Text)
    AIConfidence = Column('ai_confidence', Numeric(5, 2))

    # Incident
    IncidentId = Column('incident_id', Integer, ForeignKey('incidents.incidents.incident_id'))

    # Timestamps
    CreatedAt = Column('created_at', DateTime, server_default=func.now(), index=True)
    AcknowledgedAt = Column('acknowledged_at', DateTime)
    ResolvedAt = Column('resolved_at', DateTime)
    UpdatedAt = Column('updated_at', DateTime)

    # Comments and History
    Comments = Column('comments', JSONB)
    ActionsTaken = Column('actions_taken', JSONB)

    # CBR Compliance
    OperationalRiskCategory = Column('operational_risk_category', String(100))
    EstimatedDamage_RUB = Column('estimated_damage_rub', Numeric(15, 2))
    IsReportable = Column('is_reportable', Boolean, default=True)

    # Relationships
    rule = relationship("DetectionRule", back_populates="alerts")
    agent = relationship("Agent", back_populates="alerts")
    assigned_user = relationship("User", back_populates="assigned_alerts")
    incident = relationship("Incident", back_populates="alerts")

    def __repr__(self):
        return f"<Alert(id={self.AlertId}, title='{self.Title}', severity={self.Severity})>"

    @property
    def is_new(self) -> bool:
        return self.Status == 'new'

    @property
    def is_resolved(self) -> bool:
        return self.Status in ('resolved', 'false_positive')


class Incident(Base):
    """Incident model - incidents.incidents table"""

    __tablename__ = "incidents"
    __table_args__ = {'schema': 'incidents'}

    IncidentId = Column('incident_id', Integer, primary_key=True, autoincrement=True)
    IncidentGuid = Column('incident_guid', UUID(as_uuid=True), unique=True, index=True, server_default=func.gen_random_uuid())

    # Basic Info
    Title = Column('title', String(500), nullable=False)
    Description = Column('description', Text)
    Severity = Column('severity', Integer, nullable=False, index=True)
    Category = Column('category', String(50))

    # Related Alerts
    AlertCount = Column('alert_count', Integer, default=0)
    EventCount = Column('event_count', Integer, default=0)

    # Affected Systems
    AffectedAgents = Column('affected_agents', JSONB)
    AffectedUsers = Column('affected_users', JSONB)
    AffectedAssets = Column('affected_assets', Integer, default=0)

    # Timeline
    StartTime = Column('start_time', DateTime)
    EndTime = Column('end_time', DateTime)
    DetectedAt = Column('detected_at', DateTime, server_default=func.now())

    # Status
    Status = Column('status', String(20), default='open', index=True)
    AssignedTo = Column('assigned_to', Integer, ForeignKey('config.users.user_id'))
    Priority = Column('priority', Integer, default=2)

    # AI Analysis
    AISummary = Column('ai_summary', Text)
    AITimeline = Column('ai_timeline', JSONB)
    AIRootCause = Column('ai_root_cause', Text)
    AIRecommendations = Column('ai_recommendations', Text)
    AIImpactAssessment = Column('ai_impact_assessment', Text)

    # MITRE ATT&CK
    MitreAttackTactics = Column('mitre_attack_tactics', JSONB)
    MitreAttackTechniques = Column('mitre_attack_techniques', JSONB)
    AttackChain = Column('attack_chain', JSONB)

    # Response
    ContainmentActions = Column('containment_actions', JSONB)
    RemediationActions = Column('remediation_actions', JSONB)
    LessonsLearned = Column('lessons_learned', Text)

    # CBR Compliance
    OperationalRiskCategory = Column('operational_risk_category', String(100))
    EstimatedDamage_RUB = Column('estimated_damage_rub', Numeric(15, 2))
    ActualDamage_RUB = Column('actual_damage_rub', Numeric(15, 2))
    IsReportedToCBR = Column('is_reported_to_cbr', Boolean, default=False, index=True)
    CBRReportDate = Column('cbr_report_date', DateTime)
    CBRIncidentNumber = Column('cbr_incident_number', String(100))

    # Timestamps
    CreatedAt = Column('created_at', DateTime, server_default=func.now())
    UpdatedAt = Column('updated_at', DateTime)
    ClosedAt = Column('closed_at', DateTime)

    # Work Log
    WorkLog = Column('work_log', JSONB)

    # Relationships
    alerts = relationship("Alert", back_populates="incident")
    assigned_user = relationship("User", back_populates="assigned_incidents")

    def __repr__(self):
        return f"<Incident(id={self.IncidentId}, title='{self.Title}', status='{self.Status}')>"

    @property
    def is_active(self) -> bool:
        return self.Status not in ('resolved', 'closed')

    @property
    def is_critical(self) -> bool:
        return self.Severity >= 4
