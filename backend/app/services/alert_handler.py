"""
Alert Handler Service
Handles automatic actions for new alerts: email notifications, FreeScout tickets, etc.
"""

import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.incident import Alert
from app.models.integrations import EmailNotification, FreeScoutTicket
from app.api.v1.settings import get_setting
from app.services.email_service import get_email_service
from app.api.v1.integrations.freescout import FreeScoutClient

logger = logging.getLogger(__name__)


async def handle_new_alert(alert: Alert, db: Session, siem_url: str = "http://localhost:3000"):
    """
    Handle new alert: send email, create FreeScout ticket, etc.
    This should be called after alert is created and committed to DB
    """
    try:
        # Check if email notifications are enabled
        smtp_enabled = get_setting(db, 'smtp_enabled', False)
        if smtp_enabled:
            await send_alert_email(alert, db, siem_url)

        # Check if FreeScout auto-create is enabled
        freescout_enabled = get_setting(db, 'freescout_enabled', False)
        freescout_auto_create = get_setting(db, 'freescout_auto_create_on_alert', False)

        if freescout_enabled and freescout_auto_create:
            await create_freescout_ticket_for_alert(alert, db)

    except Exception as e:
        logger.error(f"Error handling new alert {alert.AlertId}: {e}", exc_info=True)
        # Don't raise - we don't want to fail alert creation if notifications fail


async def send_alert_email(alert: Alert, db: Session, siem_url: str):
    """Send email notification for alert"""
    try:
        # Get min severity for email
        min_severity = get_setting(db, 'email_alert_min_severity', 3)  # Default: High/Critical only

        if alert.Severity < min_severity:
            logger.debug(f"Alert {alert.AlertId} severity {alert.Severity} below threshold {min_severity}, skipping email")
            return

        # Get SMTP settings
        smtp_host = get_setting(db, 'smtp_host')
        smtp_port = get_setting(db, 'smtp_port', 587)
        smtp_username = get_setting(db, 'smtp_username')
        smtp_password = get_setting(db, 'smtp_password')
        smtp_from_email = get_setting(db, 'smtp_from_email')
        smtp_use_tls = get_setting(db, 'smtp_use_tls', True)

        # Get recipients
        recipients_str = get_setting(db, 'email_alert_recipients')
        if not recipients_str:
            logger.warning("Email notifications enabled but no recipients configured")
            return

        recipients = [r.strip() for r in recipients_str.split(',') if r.strip()]

        if not all([smtp_host, smtp_username, smtp_password, smtp_from_email]):
            logger.warning("Email notifications enabled but SMTP not fully configured")
            return

        # Create email service
        email_service = get_email_service(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            smtp_from_email=smtp_from_email,
            smtp_use_tls=smtp_use_tls
        )

        # Send email
        success, error_msg = email_service.send_alert_notification(
            alert=alert,
            recipients=recipients,
            siem_url=siem_url
        )

        # Log notification in database
        notification = EmailNotification(
            RecipientEmail=', '.join(recipients),
            Subject=f"SIEM Alert: {alert.Title}",
            AlertId=alert.AlertId,
            NotificationType='alert',
            Status='sent' if success else 'failed',
            ErrorMessage=error_msg,
            SentAt=datetime.utcnow() if success else None,
            CreatedAt=datetime.utcnow()
        )

        db.add(notification)
        db.commit()

        if success:
            logger.info(f"Email notification sent for alert {alert.AlertId} to {len(recipients)} recipient(s)")
        else:
            logger.error(f"Failed to send email for alert {alert.AlertId}: {error_msg}")

    except Exception as e:
        logger.error(f"Error sending alert email: {e}", exc_info=True)


async def create_freescout_ticket_for_alert(alert: Alert, db: Session):
    """Create FreeScout ticket for alert"""
    try:
        # Get min severity for auto-create
        min_severity = get_setting(db, 'freescout_auto_create_severity_min', 3)

        if alert.Severity < min_severity:
            logger.debug(f"Alert {alert.AlertId} severity {alert.Severity} below threshold {min_severity}, skipping FreeScout ticket")
            return

        # Check if ticket already exists
        existing = db.query(FreeScoutTicket).filter(FreeScoutTicket.AlertId == alert.AlertId).first()
        if existing:
            logger.debug(f"FreeScout ticket already exists for alert {alert.AlertId}")
            return

        # Get FreeScout settings
        freescout_url = get_setting(db, 'freescout_url')
        freescout_api_key = get_setting(db, 'freescout_api_key')
        freescout_mailbox_id = get_setting(db, 'freescout_mailbox_id')

        if not all([freescout_url, freescout_api_key, freescout_mailbox_id]):
            logger.warning("FreeScout auto-create enabled but not fully configured")
            return

        # Create FreeScout client
        client = FreeScoutClient(freescout_url, freescout_api_key, freescout_mailbox_id)

        # Create ticket
        result = client.create_ticket_from_alert(alert)

        if result.get('success'):
            # Save ticket reference
            ticket = FreeScoutTicket(
                FreeScoutConversationId=result['freescout_id'],
                FreeScoutConversationNumber=result['ticket_number'],
                AlertId=alert.AlertId,
                TicketUrl=result['ticket_url'],
                TicketStatus='active',
                TicketSubject=f"[SIEM Alert #{alert.AlertId}] {alert.Title}",
                CreatedAt=datetime.utcnow(),
                LastSyncedAt=datetime.utcnow()
            )

            db.add(ticket)
            db.commit()

            logger.info(f"FreeScout ticket #{result['ticket_number']} created for alert {alert.AlertId}")
        else:
            logger.error(f"Failed to create FreeScout ticket for alert {alert.AlertId}: {result.get('error')}")

    except Exception as e:
        logger.error(f"Error creating FreeScout ticket: {e}", exc_info=True)
