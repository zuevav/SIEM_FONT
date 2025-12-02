"""
SQLAlchemy models for Security Events
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Boolean, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Event(Base):
    """Security Event model - security_events.Events table"""

    __tablename__ = "Events"
    __table_args__ = {'schema': 'security_events'}

    EventId = Column(BigInteger, primary_key=True, autoincrement=True)
    EventGuid = Column(String(36), unique=True, index=True, server_default=func.newid())
    AgentId = Column(String(36), ForeignKey('assets.Agents.AgentId'), nullable=False, index=True)

    # Timestamps
    EventTime = Column(DateTime, nullable=False, index=True)
    ReceivedTime = Column(DateTime, server_default=func.getutcdate())
    ProcessedTime = Column(DateTime)

    # Source
    SourceType = Column(String(50), nullable=False, index=True)
    EventCode = Column(Integer, index=True)
    Channel = Column(String(100))
    Provider = Column(String(100))
    Computer = Column(String(255))

    # Normalized fields
    Severity = Column(Integer, default=0, index=True)  # 0-4
    Category = Column(String(50), index=True)
    Action = Column(String(50))
    Outcome = Column(String(20))

    # Subject (who)
    SubjectUser = Column(String(200), index=True)
    SubjectDomain = Column(String(100))
    SubjectSid = Column(String(100))
    SubjectLogonId = Column(String(50))

    # Target (what)
    TargetUser = Column(String(200), index=True)
    TargetDomain = Column(String(100))
    TargetHost = Column(String(255))
    TargetIP = Column(String(45), index=True)
    TargetPort = Column(Integer)

    # Process
    ProcessName = Column(String(500), index=True)
    ProcessId = Column(Integer)
    ProcessPath = Column(String(1000))
    ProcessCommandLine = Column(Text)
    ProcessHash = Column(String(128))

    # Parent Process
    ParentProcessName = Column(String(500))
    ParentProcessId = Column(Integer)
    ParentProcessPath = Column(String(1000))
    ParentProcessCommandLine = Column(Text)

    # Network
    SourceIP = Column(String(45), index=True)
    SourcePort = Column(Integer)
    SourceHostname = Column(String(255))
    DestinationIP = Column(String(45), index=True)
    DestinationPort = Column(Integer)
    DestinationHostname = Column(String(255))
    Protocol = Column(String(20))

    # DNS
    DNSQuery = Column(String(500))
    DNSResponse = Column(Text)  # JSON

    # File
    FilePath = Column(String(1000))
    FileName = Column(String(255))
    FileHash = Column(String(128))
    FileExtension = Column(String(20))
    FileSize = Column(BigInteger)

    # Registry
    RegistryPath = Column(String(1000))
    RegistryKey = Column(String(500))
    RegistryValue = Column(Text)
    RegistryValueType = Column(String(50))

    # Additional
    Message = Column(Text)
    RawEvent = Column(Text)  # JSON
    Tags = Column(String(500))  # JSON

    # MITRE ATT&CK
    MitreAttackTactic = Column(String(50), index=True)
    MitreAttackTechnique = Column(String(20), index=True)
    MitreAttackSubtechnique = Column(String(30))

    # AI Analysis
    AIProcessed = Column(Boolean, default=False, index=True)
    AIScore = Column(Numeric(5, 2))
    AICategory = Column(String(100))
    AIDescription = Column(String(1000))
    AIConfidence = Column(Numeric(5, 2))
    AIIsAttack = Column(Boolean)

    # GeoIP
    GeoCountry = Column(String(2))
    GeoCity = Column(String(100))

    # Relationships
    agent = relationship("Agent", back_populates="events")

    def __repr__(self):
        return f"<Event(id={self.EventId}, type='{self.SourceType}', severity={self.Severity})>"

    @property
    def is_critical(self) -> bool:
        """Check if event is critical"""
        return self.Severity >= 4

    @property
    def is_high_severity(self) -> bool:
        """Check if event is high severity"""
        return self.Severity >= 3
