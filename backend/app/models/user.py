"""
SQLAlchemy models for Users and Sessions
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User model - config.users table"""

    __tablename__ = "users"
    __table_args__ = {'schema': 'config'}

    # Column names match PostgreSQL schema (snake_case)
    user_id = Column('user_id', Integer, primary_key=True, index=True, autoincrement=True)
    username = Column('username', String(100), unique=True, nullable=False, index=True)
    email = Column('email', String(255))
    password_hash = Column('password_hash', String(255))  # NULL for AD users
    role = Column('role', String(20), nullable=False, default='viewer')  # admin, analyst, viewer
    is_ad_user = Column('is_ad_user', Boolean, default=False)
    is_active = Column('is_active', Boolean, default=True)
    created_at = Column('created_at', DateTime, server_default=func.now())
    last_login = Column('last_login', DateTime)
    settings = Column('settings', JSONB)  # JSONB for PostgreSQL

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    created_rules = relationship("DetectionRule", foreign_keys="DetectionRule.CreatedBy", back_populates="creator")
    assigned_alerts = relationship("Alert", back_populates="assigned_user")
    assigned_incidents = relationship("Incident", back_populates="assigned_user")
    saved_searches = relationship("SavedSearch", back_populates="user", cascade="all, delete-orphan")

    # Aliases for backward compatibility with existing code
    @property
    def UserId(self):
        return self.user_id

    @property
    def Username(self):
        return self.username

    @property
    def Email(self):
        return self.email

    @property
    def PasswordHash(self):
        return self.password_hash

    @property
    def Role(self):
        return self.role

    @property
    def IsADUser(self):
        return self.is_ad_user

    @property
    def IsActive(self):
        return self.is_active

    @property
    def CreatedAt(self):
        return self.created_at

    @property
    def LastLogin(self):
        return self.last_login

    @LastLogin.setter
    def LastLogin(self, value):
        self.last_login = value

    def __repr__(self):
        return f"<User(id={self.user_id}, username='{self.username}', role='{self.role}')>"

    @property
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == 'admin'

    @property
    def is_analyst(self) -> bool:
        """Check if user is analyst or admin"""
        return self.role in ('admin', 'analyst')

    @property
    def can_write(self) -> bool:
        """Check if user can write data"""
        return self.role in ('admin', 'analyst')


class Session(Base):
    """Session model - config.sessions table"""

    __tablename__ = "sessions"
    __table_args__ = {'schema': 'config'}

    session_id = Column('session_id', String(36), primary_key=True)  # GUID
    user_id = Column('user_id', Integer, ForeignKey('config.users.user_id'), nullable=False)
    token = Column('token', String(500), nullable=False, unique=True, index=True)
    ip_address = Column('ip_address', String(45))
    user_agent = Column('user_agent', String(500))
    created_at = Column('created_at', DateTime, server_default=func.now())
    expires_at = Column('expires_at', DateTime, nullable=False, index=True)
    is_active = Column('is_active', Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Aliases for backward compatibility
    @property
    def SessionId(self):
        return self.session_id

    @SessionId.setter
    def SessionId(self, value):
        self.session_id = value

    @property
    def UserId(self):
        return self.user_id

    @UserId.setter
    def UserId(self, value):
        self.user_id = value

    @property
    def Token(self):
        return self.token

    @Token.setter
    def Token(self, value):
        self.token = value

    @property
    def IPAddress(self):
        return self.ip_address

    @IPAddress.setter
    def IPAddress(self, value):
        self.ip_address = value

    @property
    def UserAgent(self):
        return self.user_agent

    @UserAgent.setter
    def UserAgent(self, value):
        self.user_agent = value

    @property
    def ExpiresAt(self):
        return self.expires_at

    @ExpiresAt.setter
    def ExpiresAt(self, value):
        self.expires_at = value

    @property
    def IsActive(self):
        return self.is_active

    @IsActive.setter
    def IsActive(self, value):
        self.is_active = value

    def __repr__(self):
        return f"<Session(id='{self.session_id}', user_id={self.user_id}, active={self.is_active})>"

    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        from datetime import datetime
        return self.expires_at < datetime.utcnow()
