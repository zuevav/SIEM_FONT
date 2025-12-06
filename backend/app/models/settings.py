"""
SQLAlchemy model for System Settings
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class SystemSettings(Base):
    """System Settings model - config.SystemSettings table"""

    __tablename__ = "SystemSettings"
    __table_args__ = {'schema': 'config'}

    SettingId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    SettingKey = Column(String(100), unique=True, nullable=False, index=True)
    SettingValue = Column(Text)  # JSON or plain text
    SettingType = Column(String(50))  # string, boolean, integer, json
    Category = Column(String(50))  # freescout, email, ai, system
    Description = Column(Text)
    IsEncrypted = Column(Boolean, default=False)
    CreatedAt = Column(DateTime, server_default=func.getutcdate())
    UpdatedAt = Column(DateTime, onupdate=func.getutcdate())

    def __repr__(self):
        return f"<SystemSettings(key='{self.SettingKey}', category='{self.Category}')>"
