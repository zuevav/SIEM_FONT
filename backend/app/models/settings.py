"""
SQLAlchemy model for System Settings
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class SystemSettings(Base):
    """System Settings model - config.system_settings table (PostgreSQL snake_case)"""

    __tablename__ = "system_settings"
    __table_args__ = {'schema': 'config'}

    # Column names match PostgreSQL schema (snake_case)
    setting_id = Column('setting_id', Integer, primary_key=True, index=True, autoincrement=True)
    setting_key = Column('setting_key', String(100), unique=True, nullable=False, index=True)
    setting_value = Column('setting_value', Text)  # JSON or plain text
    setting_type = Column('setting_type', String(50))  # string, boolean, integer, json
    category = Column('category', String(50))  # freescout, email, ai, system
    description = Column('description', Text)
    is_encrypted = Column('is_encrypted', Boolean, default=False)
    created_at = Column('created_at', DateTime, server_default=func.now())
    updated_at = Column('updated_at', DateTime, onupdate=func.now())

    # PascalCase aliases for backward compatibility
    @property
    def SettingId(self):
        return self.setting_id

    @property
    def SettingKey(self):
        return self.setting_key

    @property
    def SettingValue(self):
        return self.setting_value

    @property
    def SettingType(self):
        return self.setting_type

    @property
    def Category(self):
        return self.category

    @property
    def Description(self):
        return self.description

    @property
    def IsEncrypted(self):
        return self.is_encrypted

    def __repr__(self):
        return f"<SystemSettings(key='{self.SettingKey}', category='{self.Category}')>"
