"""
SQLAlchemy models for Alerts and Incidents
"""

from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Boolean, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class DetectionRule(Base):
    """Detection Rule model - config.DetectionRules table"""

    __tablename__ = "DetectionRules"
    __table_args__ = {'schema': 'config'}

    RuleId = Column(Integer, primary_key=True, autoincrement=True)
    RuleName = Column(String(200), nullable=False, unique=True)
    Description = Column(String(1000))
    IsEnabled = Column(Boolean, default=True, index=True)

    # Priority
    Severity = Column(Integer, default=2)  # 0-4
    Priority = Column(Integer, default=50)  # Execution order

    # Rule Type
    RuleType = Column(String(20), nullable=False)  # simple, threshold, correlation, sigma, ml
    RuleLogic = Column(Text, nullable=False)  # JSON or YAML

    # Time Parameters
    TimeWindowMinutes = Column(Integer)
    ThresholdCount = Column(Integer)
    GroupByFields = Column(String(500))  # JSON

    # Conditions
    SourceTypes = Column(String(500))  # JSON
    EventCodes = Column(String(500))  # JSON
    Categories = Column(String(500))  # JSON

    # Actions
    Actions = Column(Text)  # JSON
    AutoEscalate = Column(Boolean, default=False)

    # MITRE ATT&CK
    MitreAttackTactic = Column(String(50))
    MitreAttackTechnique = Column(String(20))
    MitreAttackSubtechnique = Column(String(30))

    # Exceptions
    Exceptions = Column(Text)  # JSON

    # Statistics
    TotalMatches = Column(BigInteger, default=0)
    FalsePositives = Column(Integer, default=0)
    LastMatch = Column(DateTime)

    # Metadata
    CreatedBy = Column(Integer, ForeignKey('config.Users.UserId'))
    CreatedAt = Column(DateTime, server_default=func.getutcdate())
    UpdatedBy = Column(Integer, ForeignKey('config.Users.UserId'))
    UpdatedAt = Column(DateTime)
    Tags = Column(String(500))  # JSON

    # Relationships
    creator = relationship("User", foreign_keys=[CreatedBy], back_populates="created_rules")
    alerts = relationship("Alert", back_populates="rule")

    def __repr__(self):
        return f"<DetectionRule(id={self.RuleId}, name='{self.RuleName}', enabled={self.IsEnabled})>"


class Alert(Base):
    """Alert model - incidents.Alerts table"""

    __tablename__ = "Alerts"
    __table_args__ = {'schema': 'incidents'}

    AlertId = Column(BigInteger, primary_key=True, autoincrement=True)
    AlertGuid = Column(String(36), unique=True, index=True, server_default=func.newid())
    RuleId = Column(Integer, ForeignKey('config.DetectionRules.RuleId'))

    # Classification
    Severity = Column(Integer, nullable=False, index=True)
    Title = Column(String(500), nullable=False)
    Description = Column(Text)
    Category = Column(String(50))  # intrusion, malware, policy_violation, anomaly, recon

    # Related Events
    EventIds = Column(Text)  # JSON array
    EventCount = Column(Integer, default=1)
    FirstEventTime = Column(DateTime)
    LastEventTime = Column(DateTime)

    # Context
    AgentId = Column(String(36), ForeignKey('assets.Agents.AgentId'), index=True)
    Hostname = Column(String(255))
    Username = Column(String(200))
    SourceIP = Column(String(45))
    TargetIP = Column(String(45))
    ProcessName = Column(String(500))

    # MITRE ATT&CK
    MitreAttackTactic = Column(String(50))
    MitreAttackTechnique = Column(String(20))
    MitreAttackSubtechnique = Column(String(30))

    # Status
    Status = Column(String(20), default='new', index=True)
    # new, acknowledged, investigating, resolved, false_positive
    AssignedTo = Column(Integer, ForeignKey('config.Users.UserId'))
    Priority = Column(Integer, default=2)  # 1-4

    # AI Analysis
    AIAnalysis = Column(Text)  # JSON
    AIRecommendations = Column(Text)
    AIConfidence = Column(Numeric(5, 2))

    # Incident
    IncidentId = Column(Integer, ForeignKey('incidents.Incidents.IncidentId'))

    # Timestamps
    CreatedAt = Column(DateTime, server_default=func.getutcdate(), index=True)
    AcknowledgedAt = Column(DateTime)
    ResolvedAt = Column(DateTime)
    UpdatedAt = Column(DateTime)

    # Comments and History
    Comments = Column(Text)  # JSON
    ActionsTaken = Column(Text)  # JSON

    # CBR Compliance
    OperationalRiskCategory = Column(String(100))
    EstimatedDamage_RUB = Column(Numeric(15, 2))
    IsReportable = Column(Boolean, default=True)

    # Relationships
    rule = relationship("DetectionRule", back_populates="alerts")
    agent = relationship("Agent", back_populates="alerts")
    assigned_user = relationship("User", back_populates="assigned_alerts")
    incident = relationship("Incident", back_populates="alerts")

    def __repr__(self):
        return f"<Alert(id={self.AlertId}, title='{self.Title}', severity={self.Severity})>"

    @property
    def is_new(self) -> bool:
        """Check if alert is new"""
        return self.Status == 'new'

    @property
    def is_resolved(self) -> bool:
        """Check if alert is resolved"""
        return self.Status in ('resolved', 'false_positive')


class Incident(Base):
    """Incident model - incidents.Incidents table"""

    __tablename__ = "Incidents"
    __table_args__ = {'schema': 'incidents'}

    IncidentId = Column(Integer, primary_key=True, autoincrement=True)
    IncidentGuid = Column(String(36), unique=True, index=True, server_default=func.newid())

    # Basic Info
    Title = Column(String(500), nullable=False)
    Description = Column(Text)
    Severity = Column(Integer, nullable=False, index=True)
    Category = Column(String(50))  # intrusion, malware, data_breach, policy_violation

    # Related Alerts
    AlertCount = Column(Integer, default=0)
    EventCount = Column(Integer, default=0)

    # Affected Systems
    AffectedAgents = Column(Text)  # JSON
    AffectedUsers = Column(Text)  # JSON
    AffectedAssets = Column(Integer, default=0)

    # Timeline
    StartTime = Column(DateTime)
    EndTime = Column(DateTime)
    DetectedAt = Column(DateTime, server_default=func.getutcdate())

    # Status
    Status = Column(String(20), default='open', index=True)
    # open, investigating, contained, resolved, closed
    AssignedTo = Column(Integer, ForeignKey('config.Users.UserId'))
    Priority = Column(Integer, default=2)

    # AI Analysis
    AISummary = Column(Text)
    AITimeline = Column(Text)  # JSON
    AIRootCause = Column(Text)
    AIRecommendations = Column(Text)
    AIImpactAssessment = Column(Text)

    # MITRE ATT&CK
    MitreAttackTactics = Column(String(500))  # JSON
    MitreAttackTechniques = Column(String(500))  # JSON
    AttackChain = Column(Text)  # JSON

    # Response
    ContainmentActions = Column(Text)  # JSON
    RemediationActions = Column(Text)  # JSON
    LessonsLearned = Column(Text)

    # CBR Compliance
    OperationalRiskCategory = Column(String(100))
    EstimatedDamage_RUB = Column(Numeric(15, 2))
    ActualDamage_RUB = Column(Numeric(15, 2))
    IsReportedToCBR = Column(Boolean, default=False, index=True)
    CBRReportDate = Column(DateTime)
    CBRIncidentNumber = Column(String(100))

    # Timestamps
    CreatedAt = Column(DateTime, server_default=func.getutcdate())
    UpdatedAt = Column(DateTime)
    ClosedAt = Column(DateTime)

    # Work Log
    WorkLog = Column(Text)  # JSON

    # Relationships
    alerts = relationship("Alert", back_populates="incident")
    assigned_user = relationship("User", back_populates="assigned_incidents")

    def __repr__(self):
        return f"<Incident(id={self.IncidentId}, title='{self.Title}', status='{self.Status}')>"

    @property
    def is_active(self) -> bool:
        """Check if incident is active"""
        return self.Status not in ('resolved', 'closed')

    @property
    def is_critical(self) -> bool:
        """Check if incident is critical"""
        return self.Severity >= 4
