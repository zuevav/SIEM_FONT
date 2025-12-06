"""
SQLAlchemy models for Users and Sessions
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User model - config.Users table"""

    __tablename__ = "Users"
    __table_args__ = {'schema': 'config'}

    UserId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Username = Column(String(100), unique=True, nullable=False, index=True)
    Email = Column(String(255))
    PasswordHash = Column(String(255))  # NULL for AD users
    Role = Column(String(20), nullable=False, default='viewer')  # admin, analyst, viewer
    IsADUser = Column(Boolean, default=False)
    IsActive = Column(Boolean, default=True)
    CreatedAt = Column(DateTime, server_default=func.getutcdate())
    LastLogin = Column(DateTime)
    Settings = Column(Text)  # JSON

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    created_rules = relationship("DetectionRule", foreign_keys="DetectionRule.CreatedBy", back_populates="creator")
    assigned_alerts = relationship("Alert", back_populates="assigned_user")
    assigned_incidents = relationship("Incident", back_populates="assigned_user")
    saved_searches = relationship("SavedSearch", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.UserId}, username='{self.Username}', role='{self.Role}')>"

    @property
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.Role == 'admin'

    @property
    def is_analyst(self) -> bool:
        """Check if user is analyst or admin"""
        return self.Role in ('admin', 'analyst')

    @property
    def can_write(self) -> bool:
        """Check if user can write data"""
        return self.Role in ('admin', 'analyst')


class Session(Base):
    """Session model - config.Sessions table"""

    __tablename__ = "Sessions"
    __table_args__ = {'schema': 'config'}

    SessionId = Column(String(36), primary_key=True)  # GUID
    UserId = Column(Integer, ForeignKey('config.Users.UserId'), nullable=False)
    Token = Column(String(500), nullable=False, unique=True, index=True)
    IPAddress = Column(String(45))
    UserAgent = Column(String(500))
    CreatedAt = Column(DateTime, server_default=func.getutcdate())
    ExpiresAt = Column(DateTime, nullable=False, index=True)
    IsActive = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session(id='{self.SessionId}', user_id={self.UserId}, active={self.IsActive})>"

    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        from datetime import datetime
        return self.ExpiresAt < datetime.utcnow()
