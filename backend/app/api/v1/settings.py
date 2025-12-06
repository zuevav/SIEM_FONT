"""
Settings API Endpoints
Handles system settings, FreeScout, Email, AI configuration
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from cryptography.fernet import Fernet
import os

from app.api.deps import get_db, get_current_user, require_admin
from app.schemas.settings import (
    SettingsResponse,
    SettingsUpdate,
    TestEmailRequest,
    TestEmailResponse,
    TestFreeScoutRequest,
    TestFreeScoutResponse
)
from app.schemas.auth import CurrentUser
from app.models.settings import SystemSettings
from app.config import settings as app_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Encryption key for sensitive settings (should be in env var)
ENCRYPTION_KEY = os.getenv("SETTINGS_ENCRYPTION_KEY", Fernet.generate_key())
cipher = Fernet(ENCRYPTION_KEY)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_setting(db: Session, key: str, default: any = None) -> any:
    """Get a setting value from database"""
    try:
        setting = db.query(SystemSettings).filter(SystemSettings.SettingKey == key).first()
        if not setting:
            return default

        # Decrypt if encrypted
        value = setting.SettingValue
        if setting.IsEncrypted and value:
            try:
                value = cipher.decrypt(value.encode()).decode()
            except Exception as e:
                logger.error(f"Failed to decrypt setting {key}: {e}")
                return default

        # Parse by type
        if setting.SettingType == 'boolean':
            return value.lower() in ('true', '1', 'yes') if value else default
        elif setting.SettingType == 'integer':
            return int(value) if value else default
        elif setting.SettingType == 'json':
            return json.loads(value) if value else default
        else:
            return value if value else default

    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}")
        return default


def set_setting(db: Session, key: str, value: any, category: str = 'general',
                setting_type: str = 'string', encrypt: bool = False):
    """Set a setting value in database"""
    try:
        # Convert value to string
        if setting_type == 'boolean':
            str_value = 'true' if value else 'false'
        elif setting_type == 'integer':
            str_value = str(value) if value is not None else None
        elif setting_type == 'json':
            str_value = json.dumps(value) if value is not None else None
        else:
            str_value = str(value) if value is not None else None

        # Encrypt if needed
        if encrypt and str_value:
            str_value = cipher.encrypt(str_value.encode()).decode()

        # Get or create setting
        setting = db.query(SystemSettings).filter(SystemSettings.SettingKey == key).first()

        if setting:
            setting.SettingValue = str_value
            setting.IsEncrypted = encrypt
        else:
            setting = SystemSettings(
                SettingKey=key,
                SettingValue=str_value,
                SettingType=setting_type,
                Category=category,
                IsEncrypted=encrypt
            )
            db.add(setting)

        db.commit()
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Error setting {key}: {e}")
        return False


# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================

@router.get("", response_model=SettingsResponse)
async def get_settings(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get all system settings (admin only for sensitive data)
    """
    try:
        # Get all settings
        settings_data = SettingsResponse(
            # FreeScout
            freescout_enabled=get_setting(db, 'freescout_enabled', False),
            freescout_url=get_setting(db, 'freescout_url'),
            freescout_api_key=get_setting(db, 'freescout_api_key') if current_user.role == 'admin' else None,
            freescout_mailbox_id=get_setting(db, 'freescout_mailbox_id'),
            freescout_auto_create_on_alert=get_setting(db, 'freescout_auto_create_on_alert', False),
            freescout_auto_create_severity_min=get_setting(db, 'freescout_auto_create_severity_min', 3),
            freescout_webhook_secret=get_setting(db, 'freescout_webhook_secret') if current_user.role == 'admin' else None,

            # Email
            smtp_enabled=get_setting(db, 'smtp_enabled', False),
            smtp_host=get_setting(db, 'smtp_host'),
            smtp_port=get_setting(db, 'smtp_port', 587),
            smtp_username=get_setting(db, 'smtp_username'),
            smtp_password=get_setting(db, 'smtp_password') if current_user.role == 'admin' else None,
            smtp_from_email=get_setting(db, 'smtp_from_email'),
            smtp_use_tls=get_setting(db, 'smtp_use_tls', True),

            # AI
            ai_provider=get_setting(db, 'ai_provider', 'deepseek'),
            deepseek_api_key=get_setting(db, 'deepseek_api_key') if current_user.role == 'admin' else None,
            yandex_gpt_api_key=get_setting(db, 'yandex_gpt_api_key') if current_user.role == 'admin' else None,
            yandex_gpt_folder_id=get_setting(db, 'yandex_gpt_folder_id'),
            ai_auto_analyze_alerts=get_setting(db, 'ai_auto_analyze_alerts', True),
            ai_auto_analyze_severity_min=get_setting(db, 'ai_auto_analyze_severity_min', 3),

            # Threat Intelligence
            virustotal_api_key=get_setting(db, 'virustotal_api_key') if current_user.role == 'admin' else None,
            abuseipdb_api_key=get_setting(db, 'abuseipdb_api_key') if current_user.role == 'admin' else None,
            threat_intel_enabled=get_setting(db, 'threat_intel_enabled', False),

            # System
            system_version=get_setting(db, 'system_version'),
            system_git_branch=get_setting(db, 'system_git_branch'),
            system_git_commit=get_setting(db, 'system_git_commit'),
        )

        return settings_data

    except Exception as e:
        logger.error(f"Error getting settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get settings: {str(e)}"
        )


@router.post("", response_model=SettingsResponse)
async def update_settings(
    updates: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Update system settings (admin only)
    """
    try:
        # Update FreeScout settings
        if updates.freescout_enabled is not None:
            set_setting(db, 'freescout_enabled', updates.freescout_enabled, 'freescout', 'boolean')
        if updates.freescout_url is not None:
            set_setting(db, 'freescout_url', updates.freescout_url, 'freescout')
        if updates.freescout_api_key is not None:
            set_setting(db, 'freescout_api_key', updates.freescout_api_key, 'freescout', encrypt=True)
        if updates.freescout_mailbox_id is not None:
            set_setting(db, 'freescout_mailbox_id', updates.freescout_mailbox_id, 'freescout', 'integer')
        if updates.freescout_auto_create_on_alert is not None:
            set_setting(db, 'freescout_auto_create_on_alert', updates.freescout_auto_create_on_alert, 'freescout', 'boolean')
        if updates.freescout_auto_create_severity_min is not None:
            set_setting(db, 'freescout_auto_create_severity_min', updates.freescout_auto_create_severity_min, 'freescout', 'integer')
        if updates.freescout_webhook_secret is not None:
            set_setting(db, 'freescout_webhook_secret', updates.freescout_webhook_secret, 'freescout', encrypt=True)

        # Update Email settings
        if updates.smtp_enabled is not None:
            set_setting(db, 'smtp_enabled', updates.smtp_enabled, 'email', 'boolean')
        if updates.smtp_host is not None:
            set_setting(db, 'smtp_host', updates.smtp_host, 'email')
        if updates.smtp_port is not None:
            set_setting(db, 'smtp_port', updates.smtp_port, 'email', 'integer')
        if updates.smtp_username is not None:
            set_setting(db, 'smtp_username', updates.smtp_username, 'email')
        if updates.smtp_password is not None:
            set_setting(db, 'smtp_password', updates.smtp_password, 'email', encrypt=True)
        if updates.smtp_from_email is not None:
            set_setting(db, 'smtp_from_email', updates.smtp_from_email, 'email')
        if updates.smtp_use_tls is not None:
            set_setting(db, 'smtp_use_tls', updates.smtp_use_tls, 'email', 'boolean')

        # Update AI settings
        if updates.ai_provider is not None:
            set_setting(db, 'ai_provider', updates.ai_provider, 'ai')
        if updates.deepseek_api_key is not None:
            set_setting(db, 'deepseek_api_key', updates.deepseek_api_key, 'ai', encrypt=True)
        if updates.yandex_gpt_api_key is not None:
            set_setting(db, 'yandex_gpt_api_key', updates.yandex_gpt_api_key, 'ai', encrypt=True)
        if updates.yandex_gpt_folder_id is not None:
            set_setting(db, 'yandex_gpt_folder_id', updates.yandex_gpt_folder_id, 'ai')
        if updates.ai_auto_analyze_alerts is not None:
            set_setting(db, 'ai_auto_analyze_alerts', updates.ai_auto_analyze_alerts, 'ai', 'boolean')
        if updates.ai_auto_analyze_severity_min is not None:
            set_setting(db, 'ai_auto_analyze_severity_min', updates.ai_auto_analyze_severity_min, 'ai', 'integer')

        # Update Threat Intelligence settings
        if updates.virustotal_api_key is not None:
            set_setting(db, 'virustotal_api_key', updates.virustotal_api_key, 'threat_intel', encrypt=True)
        if updates.abuseipdb_api_key is not None:
            set_setting(db, 'abuseipdb_api_key', updates.abuseipdb_api_key, 'threat_intel', encrypt=True)
        if updates.threat_intel_enabled is not None:
            set_setting(db, 'threat_intel_enabled', updates.threat_intel_enabled, 'threat_intel', 'boolean')

        logger.info(f"Settings updated by {current_user.username}")

        # Return updated settings
        return await get_settings(db, current_user)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


@router.post("/test-email", response_model=TestEmailResponse)
async def test_email_settings(
    test_data: TestEmailRequest,
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Test email configuration by sending a test email
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = test_data.smtp_from_email
        msg['To'] = test_data.recipient_email
        msg['Subject'] = "SIEM System - Test Email"

        body = f"""
        <html>
        <body>
            <h2>SIEM Test Email</h2>
            <p>This is a test email from your SIEM system.</p>
            <p><strong>Configuration:</strong></p>
            <ul>
                <li>SMTP Host: {test_data.smtp_host}</li>
                <li>SMTP Port: {test_data.smtp_port}</li>
                <li>Username: {test_data.smtp_username}</li>
                <li>TLS: {'Enabled' if test_data.smtp_use_tls else 'Disabled'}</li>
            </ul>
            <p>If you received this email, your SMTP configuration is working correctly.</p>
            <p><em>Sent by {current_user.username}</em></p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Send email
        if test_data.smtp_use_tls:
            server = smtplib.SMTP(test_data.smtp_host, test_data.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(test_data.smtp_host, test_data.smtp_port)

        server.login(test_data.smtp_username, test_data.smtp_password)
        server.send_message(msg)
        server.quit()

        logger.info(f"Test email sent successfully to {test_data.recipient_email}")

        return TestEmailResponse(
            success=True,
            message=f"Test email sent successfully to {test_data.recipient_email}"
        )

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        return TestEmailResponse(
            success=False,
            message="SMTP authentication failed",
            error=f"Invalid username or password: {str(e)}"
        )
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return TestEmailResponse(
            success=False,
            message="SMTP error",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Error sending test email: {e}", exc_info=True)
        return TestEmailResponse(
            success=False,
            message="Failed to send test email",
            error=str(e)
        )


@router.post("/test-freescout", response_model=TestFreeScoutResponse)
async def test_freescout_connection(
    test_data: TestFreeScoutRequest,
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Test FreeScout connection by fetching mailboxes
    """
    try:
        # Test API connection
        headers = {
            'X-FreeScout-API-Key': test_data.api_key,
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f"{test_data.url}/api/mailboxes",
            headers=headers,
            timeout=10
        )

        if response.status_code == 401:
            return TestFreeScoutResponse(
                success=False,
                message="Authentication failed",
                error="Invalid API key"
            )

        if response.status_code != 200:
            return TestFreeScoutResponse(
                success=False,
                message=f"HTTP {response.status_code}",
                error=response.text[:200]
            )

        # Parse response
        data = response.json()

        if '_embedded' in data and 'mailboxes' in data['_embedded']:
            mailboxes = data['_embedded']['mailboxes']
            if mailboxes:
                first_mailbox = mailboxes[0]
                logger.info(f"FreeScout connection test successful for {test_data.url}")
                return TestFreeScoutResponse(
                    success=True,
                    message=f"Connected successfully. Found {len(mailboxes)} mailbox(es)",
                    mailbox_name=first_mailbox.get('name'),
                    mailbox_id=first_mailbox.get('id')
                )

        return TestFreeScoutResponse(
            success=True,
            message="Connected successfully but no mailboxes found",
        )

    except requests.exceptions.Timeout:
        return TestFreeScoutResponse(
            success=False,
            message="Connection timeout",
            error="The request timed out after 10 seconds"
        )
    except requests.exceptions.ConnectionError:
        return TestFreeScoutResponse(
            success=False,
            message="Connection failed",
            error=f"Unable to connect to {test_data.url}"
        )
    except Exception as e:
        logger.error(f"Error testing FreeScout connection: {e}", exc_info=True)
        return TestFreeScoutResponse(
            success=False,
            message="Test failed",
            error=str(e)
        )
