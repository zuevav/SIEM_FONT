"""
SQLAlchemy models for Integrations
FreeScout tickets, Email notifications, Threat Intelligence
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, NVARCHAR
from sqlalchemy.sql import func
from app.database import Base


class FreeScoutTicket(Base):
    """FreeScout Ticket model - incidents.FreeScoutTickets table"""

    __tablename__ = "FreeScoutTickets"
    __table_args__ = {'schema': 'incidents'}

    TicketId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    FreeScoutConversationId = Column(Integer, nullable=False, unique=True, index=True)
    FreeScoutConversationNumber = Column(Integer, nullable=False)
    AlertId = Column(Integer, ForeignKey('incidents.alerts.alert_id'), nullable=True, index=True)
    IncidentId = Column(Integer, ForeignKey('incidents.incidents.incident_id'), nullable=True, index=True)
    TicketUrl = Column(String(500))
    TicketStatus = Column(String(20))  # active, closed, spam
    TicketSubject = Column(String(500))
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, onupdate=func.now())
    LastSyncedAt = Column(DateTime)

    def __repr__(self):
        return f"<FreeScoutTicket(id={self.TicketId}, conversation={self.FreeScoutConversationNumber}, alert={self.AlertId})>"


class EmailNotification(Base):
    """Email Notification model - config.EmailNotifications table"""

    __tablename__ = "EmailNotifications"
    __table_args__ = {'schema': 'config'}

    NotificationId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    RecipientEmail = Column(String(255), nullable=False)
    Subject = Column(String(500))
    Body = Column(Text)
    AlertId = Column(Integer, ForeignKey('incidents.alerts.alert_id'), nullable=True, index=True)
    IncidentId = Column(Integer, ForeignKey('incidents.incidents.incident_id'), nullable=True, index=True)
    NotificationType = Column(String(50))  # alert, incident, system, test
    Status = Column(String(20), index=True)  # sent, failed, pending
    ErrorMessage = Column(Text)
    SentAt = Column(DateTime)
    CreatedAt = Column(DateTime, server_default=func.now(), index=True)

    def __repr__(self):
        return f"<EmailNotification(id={self.NotificationId}, to='{self.RecipientEmail}', status='{self.Status}')>"


class ThreatIntelligence(Base):
    """Threat Intelligence cache model - enrichment.ThreatIntelligence table"""

    __tablename__ = "ThreatIntelligence"
    __table_args__ = {'schema': 'enrichment'}

    IntelId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Indicator = Column(String(500), nullable=False, index=True)
    IndicatorType = Column(String(50), index=True)  # ip, domain, file_hash, url
    Source = Column(String(50))  # virustotal, abuseipdb, alienvault, etc.
    IsMalicious = Column(Boolean, index=True)
    ThreatScore = Column(Integer)  # 0-100
    Categories = Column(Text)  # JSON array
    Tags = Column(Text)  # JSON array
    RawData = Column(Text)  # JSON with full response
    FirstSeen = Column(DateTime, server_default=func.getutcdate())
    LastChecked = Column(DateTime, server_default=func.getutcdate(), index=True)
    CheckCount = Column(Integer, default=1)
    CacheExpiresAt = Column(DateTime)

    def __repr__(self):
        return f"<ThreatIntelligence(indicator='{self.Indicator}', type='{self.IndicatorType}', malicious={self.IsMalicious})>"
