"""
Pydantic schemas for Settings and System Update
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


# ============================================================================
# SETTINGS SCHEMAS
# ============================================================================

class SettingsResponse(BaseModel):
    """Response with all system settings"""

    # FreeScout Integration
    freescout_enabled: bool = False
    freescout_url: Optional[str] = None
    freescout_api_key: Optional[str] = None
    freescout_mailbox_id: Optional[int] = None
    freescout_auto_create_on_alert: bool = False
    freescout_auto_create_severity_min: int = 3
    freescout_webhook_secret: Optional[str] = None

    # Email Notifications
    smtp_enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_use_tls: bool = True

    # AI Configuration
    ai_provider: str = "deepseek"  # deepseek, yandex_gpt, none
    deepseek_api_key: Optional[str] = None
    yandex_gpt_api_key: Optional[str] = None
    yandex_gpt_folder_id: Optional[str] = None
    ai_auto_analyze_alerts: bool = True
    ai_auto_analyze_severity_min: int = 3

    # Threat Intelligence
    virustotal_api_key: Optional[str] = None
    abuseipdb_api_key: Optional[str] = None
    threat_intel_enabled: bool = False

    # Active Directory
    ad_enabled: bool = False
    ad_server: Optional[str] = None
    ad_base_dn: Optional[str] = None
    ad_bind_user: Optional[str] = None
    ad_bind_password: Optional[str] = None
    ad_sync_enabled: bool = False
    ad_sync_interval_hours: int = 24

    # System
    system_version: Optional[str] = None
    system_git_branch: Optional[str] = None
    system_git_commit: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "freescout_enabled": True,
                "freescout_url": "https://helpdesk.example.com",
                "freescout_mailbox_id": 1,
                "smtp_enabled": True,
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "ai_provider": "deepseek"
            }
        }


class SettingsUpdate(BaseModel):
    """Update system settings"""

    # FreeScout Integration
    freescout_enabled: Optional[bool] = None
    freescout_url: Optional[str] = None
    freescout_api_key: Optional[str] = None
    freescout_mailbox_id: Optional[int] = None
    freescout_auto_create_on_alert: Optional[bool] = None
    freescout_auto_create_severity_min: Optional[int] = Field(None, ge=0, le=4)
    freescout_webhook_secret: Optional[str] = None

    # Email Notifications
    smtp_enabled: Optional[bool] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_use_tls: Optional[bool] = None

    # AI Configuration
    ai_provider: Optional[str] = Field(None, pattern="^(deepseek|yandex_gpt|none)$")
    deepseek_api_key: Optional[str] = None
    yandex_gpt_api_key: Optional[str] = None
    yandex_gpt_folder_id: Optional[str] = None
    ai_auto_analyze_alerts: Optional[bool] = None
    ai_auto_analyze_severity_min: Optional[int] = Field(None, ge=0, le=4)

    # Threat Intelligence
    virustotal_api_key: Optional[str] = None
    abuseipdb_api_key: Optional[str] = None
    threat_intel_enabled: Optional[bool] = None

    # Active Directory
    ad_enabled: Optional[bool] = None
    ad_server: Optional[str] = None
    ad_base_dn: Optional[str] = None
    ad_bind_user: Optional[str] = None
    ad_bind_password: Optional[str] = None
    ad_sync_enabled: Optional[bool] = None
    ad_sync_interval_hours: Optional[int] = Field(None, ge=1, le=168)


class TestEmailRequest(BaseModel):
    """Test email configuration"""
    smtp_host: str
    smtp_port: int = Field(ge=1, le=65535)
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_use_tls: bool = True
    recipient_email: str


class TestEmailResponse(BaseModel):
    """Test email result"""
    success: bool
    message: str
    error: Optional[str] = None


class TestFreeScoutRequest(BaseModel):
    """Test FreeScout connection"""
    url: str
    api_key: str

    @validator('url')
    def validate_url(cls, v):
        """Validate URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v.rstrip('/')


class TestFreeScoutResponse(BaseModel):
    """Test FreeScout connection result"""
    success: bool
    message: str
    mailbox_name: Optional[str] = None
    mailbox_id: Optional[int] = None
    error: Optional[str] = None


class TestADRequest(BaseModel):
    """Test Active Directory connection"""
    server: str
    base_dn: str
    bind_user: str
    bind_password: str

    @validator('server')
    def validate_server(cls, v):
        """Validate LDAP server URL format"""
        if not v.startswith(('ldap://', 'ldaps://')):
            raise ValueError('Server must start with ldap:// or ldaps://')
        return v


class TestADResponse(BaseModel):
    """Test Active Directory connection result"""
    success: bool
    message: str
    server_type: Optional[str] = None
    domain_info: Optional[str] = None
    user_count: Optional[int] = None
    error: Optional[str] = None


# ============================================================================
# SYSTEM UPDATE SCHEMAS
# ============================================================================

class SystemInfo(BaseModel):
    """System information"""
    version: str
    git_branch: str
    git_commit: str
    git_commit_short: str
    docker_compose_version: str
    last_update: Optional[datetime] = None
    update_available: bool = False

    class Config:
        schema_extra = {
            "example": {
                "version": "1.0.0",
                "git_branch": "main",
                "git_commit": "a1b2c3d4e5f6...",
                "git_commit_short": "a1b2c3d",
                "docker_compose_version": "2.23.0",
                "last_update": "2024-01-15T10:30:00",
                "update_available": False
            }
        }


class UpdateCheckResponse(BaseModel):
    """Check for updates response"""
    update_available: bool
    current_version: str
    current_commit: str
    latest_version: str
    latest_commit: str
    changelog: List[str] = []
    commits_behind: int = 0

    class Config:
        schema_extra = {
            "example": {
                "update_available": True,
                "current_version": "1.0.0",
                "current_commit": "a1b2c3d",
                "latest_version": "1.1.0",
                "latest_commit": "f6e5d4c",
                "changelog": [
                    "feat: Add FreeScout integration",
                    "fix: Fix alert correlation"
                ],
                "commits_behind": 5
            }
        }


class UpdateStartResponse(BaseModel):
    """Start system update response"""
    success: bool
    message: str
    update_id: str  # For tracking update progress

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "System update started",
                "update_id": "update-2024-01-15-103000"
            }
        }


class UpdateProgress(BaseModel):
    """Update progress message (for WebSocket)"""
    type: str  # progress, log, error, complete
    progress: int = Field(ge=0, le=100)
    message: str
    timestamp: datetime

    class Config:
        schema_extra = {
            "example": {
                "type": "progress",
                "progress": 50,
                "message": "Pulling latest changes from GitHub...",
                "timestamp": "2024-01-15T10:30:00"
            }
        }


# ============================================================================
# FREESCOUT INTEGRATION SCHEMAS
# ============================================================================

class FreeScoutTicketCreate(BaseModel):
    """Create FreeScout ticket from alert"""
    alert_id: int
    note: Optional[str] = None


class FreeScoutTicketResponse(BaseModel):
    """FreeScout ticket creation response"""
    success: bool
    ticket_number: int
    ticket_url: str
    freescout_id: int
    message: str


class FreeScoutWebhookPayload(BaseModel):
    """FreeScout webhook payload (simplified)"""
    event: str  # conversation.created, conversation.status_changed, etc.
    conversation_id: int
    conversation_number: int
    status: str  # active, closed, spam
    subject: str
    preview: Optional[str] = None
    customer_email: Optional[str] = None
    assignee_id: Optional[int] = None

    # Custom fields
    alert_id: Optional[int] = None
    incident_id: Optional[int] = None


class FreeScoutSyncResponse(BaseModel):
    """Sync FreeScout ticket status response"""
    success: bool
    message: str
    synced_tickets: int = 0
    errors: List[str] = []
