"""
SQLAlchemy models for Integrations
FreeScout tickets, Email notifications, Threat Intelligence
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class FreeScoutTicket(Base):
    """FreeScout Ticket model - incidents.freescout_tickets table (PostgreSQL snake_case)"""

    __tablename__ = "freescout_tickets"
    __table_args__ = {'schema': 'incidents'}

    # Column names match PostgreSQL schema (snake_case)
    ticket_id = Column('ticket_id', Integer, primary_key=True, index=True, autoincrement=True)
    freescout_conversation_id = Column('freescout_conversation_id', Integer, nullable=False, unique=True, index=True)
    freescout_conversation_number = Column('freescout_conversation_number', Integer, nullable=False)
    alert_id = Column('alert_id', Integer, ForeignKey('incidents.alerts.alert_id'), nullable=True, index=True)
    incident_id = Column('incident_id', Integer, ForeignKey('incidents.incidents.incident_id'), nullable=True, index=True)
    ticket_url = Column('ticket_url', String(500))
    ticket_status = Column('ticket_status', String(20))  # active, closed, spam
    ticket_subject = Column('ticket_subject', String(500))
    created_at = Column('created_at', DateTime, server_default=func.now())
    updated_at = Column('updated_at', DateTime, onupdate=func.now())
    last_synced_at = Column('last_synced_at', DateTime)

    # PascalCase aliases for backward compatibility
    @property
    def TicketId(self):
        return self.ticket_id

    @property
    def FreeScoutConversationId(self):
        return self.freescout_conversation_id

    @property
    def FreeScoutConversationNumber(self):
        return self.freescout_conversation_number

    @property
    def AlertId(self):
        return self.alert_id

    @property
    def IncidentId(self):
        return self.incident_id

    def __repr__(self):
        return f"<FreeScoutTicket(id={self.ticket_id}, conversation={self.freescout_conversation_number}, alert={self.alert_id})>"


class EmailNotification(Base):
    """Email Notification model - config.email_notifications table (PostgreSQL snake_case)"""

    __tablename__ = "email_notifications"
    __table_args__ = {'schema': 'config'}

    # Column names match PostgreSQL schema (snake_case)
    notification_id = Column('notification_id', Integer, primary_key=True, index=True, autoincrement=True)
    recipient_email = Column('recipient_email', String(255), nullable=False)
    subject = Column('subject', String(500))
    body = Column('body', Text)
    alert_id = Column('alert_id', Integer, ForeignKey('incidents.alerts.alert_id'), nullable=True, index=True)
    incident_id = Column('incident_id', Integer, ForeignKey('incidents.incidents.incident_id'), nullable=True, index=True)
    sent_at = Column('sent_at', DateTime, server_default=func.now())
    status = Column('status', String(20), default='pending', index=True)  # pending, sent, failed
    error_message = Column('error_message', Text)
    smtp_message_id = Column('smtp_message_id', String(255))

    # PascalCase aliases for backward compatibility
    @property
    def NotificationId(self):
        return self.notification_id

    @property
    def RecipientEmail(self):
        return self.recipient_email

    @property
    def Subject(self):
        return self.subject

    @property
    def Status(self):
        return self.status

    def __repr__(self):
        return f"<EmailNotification(id={self.notification_id}, to='{self.recipient_email}', status='{self.status}')>"


class ThreatIntelligence(Base):
    """Threat Intelligence cache model - enrichment.threat_intelligence table (PostgreSQL snake_case)"""

    __tablename__ = "threat_intelligence"
    __table_args__ = {'schema': 'enrichment'}

    # Column names match PostgreSQL schema (snake_case)
    intel_id = Column('intel_id', Integer, primary_key=True, index=True, autoincrement=True)
    lookup_type = Column('lookup_type', String(20), nullable=False, index=True)  # ip, file_hash, domain, url
    lookup_value = Column('lookup_value', String(255), nullable=False, index=True)
    source = Column('source', String(50), nullable=False)  # virustotal, abuseipdb, etc.
    result = Column('result', JSONB, nullable=False)  # JSON with full response
    created_at = Column('created_at', DateTime, server_default=func.now(), nullable=False)
    expires_at = Column('expires_at', DateTime, nullable=False)  # cache expiration

    # PascalCase aliases for backward compatibility
    @property
    def IntelId(self):
        return self.intel_id

    @property
    def LookupType(self):
        return self.lookup_type

    @property
    def LookupValue(self):
        return self.lookup_value

    @property
    def Source(self):
        return self.source

    def __repr__(self):
        return f"<ThreatIntelligence(type='{self.lookup_type}', value='{self.lookup_value}', source='{self.source}')>"
