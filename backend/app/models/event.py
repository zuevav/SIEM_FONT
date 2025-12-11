"""
SQLAlchemy models for Security Events
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Boolean, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Event(Base):
    """Security Event model - security_events.events table (PostgreSQL snake_case)"""

    __tablename__ = "events"
    __table_args__ = {'schema': 'security_events'}

    # Column names match PostgreSQL schema (snake_case)
    event_id = Column('event_id', BigInteger, primary_key=True, autoincrement=True)
    event_guid = Column('event_guid', UUID(as_uuid=True), unique=True, index=True, server_default=func.gen_random_uuid())
    agent_id = Column('agent_id', UUID(as_uuid=True), ForeignKey('assets.agents.agent_id'), nullable=False, index=True)

    # PascalCase aliases for backward compatibility
    @property
    def EventId(self):
        return self.event_id

    @property
    def AgentId(self):
        return self.agent_id

    # Timestamps
    event_time = Column('event_time', DateTime, nullable=False, index=True)
    received_time = Column('received_time', DateTime, server_default=func.now())
    processed_time = Column('processed_time', DateTime)

    # Source
    source_type = Column('source_type', String(50), nullable=False, index=True)
    event_code = Column('event_code', Integer, index=True)
    channel = Column('channel', String(100))
    provider = Column('provider', String(100))
    computer = Column('computer', String(255))

    # Normalized fields
    severity = Column('severity', Integer, default=0, index=True)  # 0-4
    category = Column('category', String(50), index=True)
    action = Column('action', String(50))
    outcome = Column('outcome', String(20))

    # Subject (who)
    subject_user = Column('subject_user', String(200), index=True)
    subject_domain = Column('subject_domain', String(100))
    subject_sid = Column('subject_sid', String(100))
    subject_logon_id = Column('subject_logon_id', String(50))

    # Target (what)
    target_user = Column('target_user', String(200), index=True)
    target_domain = Column('target_domain', String(100))
    target_host = Column('target_host', String(255))
    target_ip = Column('target_ip', String(45), index=True)
    target_port = Column('target_port', Integer)

    # Process
    process_name = Column('process_name', String(500), index=True)
    process_id = Column('process_id', Integer)
    process_path = Column('process_path', String(1000))
    process_command_line = Column('process_command_line', Text)
    process_hash = Column('process_hash', String(128))

    # Parent Process
    parent_process_name = Column('parent_process_name', String(500))
    parent_process_id = Column('parent_process_id', Integer)
    parent_process_path = Column('parent_process_path', String(1000))
    parent_process_command_line = Column('parent_process_command_line', Text)

    # Network
    source_ip = Column('source_ip', String(45), index=True)
    source_port = Column('source_port', Integer)
    source_hostname = Column('source_hostname', String(255))
    destination_ip = Column('destination_ip', String(45), index=True)
    destination_port = Column('destination_port', Integer)
    destination_hostname = Column('destination_hostname', String(255))
    protocol = Column('protocol', String(20))

    # DNS
    dns_query = Column('dns_query', String(500))
    dns_response = Column('dns_response', Text)  # JSON

    # File
    file_path = Column('file_path', String(1000))
    file_name = Column('file_name', String(255))
    file_hash = Column('file_hash', String(128))
    file_extension = Column('file_extension', String(20))
    file_size = Column('file_size', BigInteger)

    # Registry
    registry_path = Column('registry_path', String(1000))
    registry_key = Column('registry_key', String(500))
    registry_value = Column('registry_value', Text)
    registry_value_type = Column('registry_value_type', String(50))

    # Additional
    message = Column('message', Text)
    raw_event = Column('raw_event', Text)  # JSON
    tags = Column('tags', Text)  # JSON

    # MITRE ATT&CK
    mitre_attack_tactic = Column('mitre_attack_tactic', String(50), index=True)
    mitre_attack_technique = Column('mitre_attack_technique', String(20), index=True)
    mitre_attack_subtechnique = Column('mitre_attack_subtechnique', String(30))

    # AI Analysis
    ai_processed = Column('ai_processed', Boolean, default=False, index=True)
    ai_score = Column('ai_score', Numeric(5, 2))
    ai_category = Column('ai_category', String(100))
    ai_description = Column('ai_description', String(1000))
    ai_confidence = Column('ai_confidence', Numeric(5, 2))
    ai_is_attack = Column('ai_is_attack', Boolean)

    # GeoIP
    geo_country = Column('geo_country', String(2))
    geo_city = Column('geo_city', String(100))

    # Relationships
    agent = relationship("Agent", back_populates="events")

    # More PascalCase aliases for backward compatibility
    @property
    def Severity(self):
        return self.severity

    @property
    def SourceType(self):
        return self.source_type

    def __repr__(self):
        return f"<Event(id={self.event_id}, type='{self.source_type}', severity={self.severity})>"

    @property
    def is_critical(self) -> bool:
        """Check if event is critical"""
        return self.severity >= 4

    @property
    def is_high_severity(self) -> bool:
        """Check if event is high severity"""
        return self.severity >= 3
