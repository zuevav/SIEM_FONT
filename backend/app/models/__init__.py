"""
SQLAlchemy models
Import all models here for easy access
"""

from app.models.user import User, Session
from app.models.agent import (
    Agent,
    SoftwareCategory,
    SoftwareRegistry,
    InstalledSoftware,
    WindowsService,
    AssetChange
)
from app.models.event import Event
from app.models.incident import DetectionRule, Alert, Incident
from app.models.settings import SystemSettings

__all__ = [
    # User models
    "User",
    "Session",
    # Agent models
    "Agent",
    "SoftwareCategory",
    "SoftwareRegistry",
    "InstalledSoftware",
    "WindowsService",
    "AssetChange",
    # Event models
    "Event",
    # Incident models
    "DetectionRule",
    "Alert",
    "Incident",
    # Settings models
    "SystemSettings",
]
