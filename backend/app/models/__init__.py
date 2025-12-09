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
from app.models.integrations import FreeScoutTicket, EmailNotification, ThreatIntelligence
from app.models.saved_search import SavedSearch
from app.models.playbook import Playbook, PlaybookAction, PlaybookExecution, ActionResult
from app.models.ad import ADUser, ADComputer, ADGroup, ADSyncLog, SoftwareInstallRequest, RemoteSession

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
    # Integration models
    "FreeScoutTicket",
    "EmailNotification",
    "ThreatIntelligence",
    # Search models
    "SavedSearch",
    # SOAR models
    "Playbook",
    "PlaybookAction",
    "PlaybookExecution",
    "ActionResult",
    # AD models
    "ADUser",
    "ADComputer",
    "ADGroup",
    "ADSyncLog",
    "SoftwareInstallRequest",
    "RemoteSession",
]
