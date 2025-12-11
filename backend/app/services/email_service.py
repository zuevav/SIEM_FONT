"""
Email Notification Service
Handles sending email notifications for alerts and incidents
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict
from datetime import datetime
import logging
from jinja2 import Template

from app.models.incident import Alert, Incident

logger = logging.getLogger(__name__)


class EmailService:
    """Email notification service"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        smtp_from_email: str,
        smtp_use_tls: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_from_email = smtp_from_email
        self.smtp_use_tls = smtp_use_tls

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Send email
        Returns (success, error_message)
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject

            # Add text version if provided
            if text_body:
                msg.attach(MIMEText(text_body, 'plain', 'utf-8'))

            # Add HTML version
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            # Connect to SMTP server
            if self.smtp_use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)

            # Login
            server.login(self.smtp_username, self.smtp_password)

            # Send email
            server.send_message(msg)
            server.quit()

            logger.info(f"Email sent successfully to {to_emails}: {subject}")
            return (True, None)

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed: {str(e)}"
            logger.error(error_msg)
            return (False, error_msg)

        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return (False, error_msg)

        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return (False, error_msg)

    def send_alert_notification(
        self,
        alert: Alert,
        recipients: List[str],
        siem_url: str = "http://localhost:3000"
    ) -> tuple[bool, Optional[str]]:
        """
        Send email notification for an alert
        """
        severity_names = ['Info', 'Low', 'Medium', 'High', 'Critical']
        severity = severity_names[alert.Severity] if 0 <= alert.Severity < 5 else 'Unknown'

        # Severity colors
        severity_colors = {
            'Critical': '#dc3545',  # red
            'High': '#fd7e14',      # orange
            'Medium': '#ffc107',    # yellow
            'Low': '#17a2b8',       # cyan
            'Info': '#6c757d'       # gray
        }
        color = severity_colors.get(severity, '#6c757d')

        # Build subject
        subject = f"🚨 SIEM Alert: {alert.Title} [{severity}]"

        # Build HTML body
        html_body = self._render_alert_template(alert, severity, color, siem_url)

        # Build text body (fallback)
        text_body = self._build_alert_text_body(alert, severity, siem_url)

        return self.send_email(recipients, subject, html_body, text_body)

    def send_incident_notification(
        self,
        incident: Incident,
        recipients: List[str],
        siem_url: str = "http://localhost:3000"
    ) -> tuple[bool, Optional[str]]:
        """
        Send email notification for an incident
        """
        severity_names = ['Info', 'Low', 'Medium', 'High', 'Critical']
        severity = severity_names[incident.Severity] if 0 <= incident.Severity < 5 else 'Unknown'

        severity_colors = {
            'Critical': '#dc3545',
            'High': '#fd7e14',
            'Medium': '#ffc107',
            'Low': '#17a2b8',
            'Info': '#6c757d'
        }
        color = severity_colors.get(severity, '#6c757d')

        # Build subject
        subject = f"🔥 SIEM Incident: {incident.Title} [{severity}]"

        # Build HTML body
        html_body = self._render_incident_template(incident, severity, color, siem_url)

        # Build text body
        text_body = self._build_incident_text_body(incident, severity, siem_url)

        return self.send_email(recipients, subject, html_body, text_body)

    def _render_alert_template(
        self,
        alert: Alert,
        severity: str,
        color: str,
        siem_url: str
    ) -> str:
        """Render alert email HTML template"""

        template = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }
        .container { max-width: 600px; margin: 20px auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: {{ color }}; color: white; padding: 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { padding: 30px; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; background: {{ color }}; color: white; }
        .info-grid { margin: 20px 0; }
        .info-row { display: flex; border-bottom: 1px solid #eee; padding: 10px 0; }
        .info-label { font-weight: bold; width: 140px; color: #666; }
        .info-value { flex: 1; }
        .description { background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; border-left: 4px solid {{ color }}; }
        .button { display: inline-block; padding: 12px 24px; background: {{ color }}; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }
        .footer { background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px; }
        .mitre { background: #fff3cd; padding: 10px; border-radius: 4px; margin: 15px 0; }
        .ai-recommendations { background: #d1ecf1; padding: 15px; border-radius: 4px; margin: 15px 0; border-left: 4px solid #0c5460; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Security Alert</h1>
        </div>

        <div class="content">
            <h2>{{ alert.Title }}</h2>
            <span class="badge">{{ severity }}</span>

            {% if alert.Description %}
            <div class="description">
                <strong>Description:</strong><br>
                {{ alert.Description }}
            </div>
            {% endif %}

            <div class="info-grid">
                <div class="info-row">
                    <div class="info-label">Alert ID:</div>
                    <div class="info-value">#{{ alert.AlertId }}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Status:</div>
                    <div class="info-value">{{ alert.Status }}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Category:</div>
                    <div class="info-value">{{ alert.Category or 'N/A' }}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Created:</div>
                    <div class="info-value">{{ alert.CreatedAt.strftime('%Y-%m-%d %H:%M:%S UTC') }}</div>
                </div>

                {% if alert.Hostname %}
                <div class="info-row">
                    <div class="info-label">Hostname:</div>
                    <div class="info-value">{{ alert.Hostname }}</div>
                </div>
                {% endif %}

                {% if alert.Username %}
                <div class="info-row">
                    <div class="info-label">Username:</div>
                    <div class="info-value">{{ alert.Username }}</div>
                </div>
                {% endif %}

                {% if alert.SourceIP %}
                <div class="info-row">
                    <div class="info-label">Source IP:</div>
                    <div class="info-value">{{ alert.SourceIP }}</div>
                </div>
                {% endif %}

                {% if alert.ProcessName %}
                <div class="info-row">
                    <div class="info-label">Process:</div>
                    <div class="info-value">{{ alert.ProcessName }}</div>
                </div>
                {% endif %}
            </div>

            {% if alert.MitreAttackTactic or alert.MitreAttackTechnique %}
            <div class="mitre">
                <strong>🎯 MITRE ATT&CK:</strong><br>
                {% if alert.MitreAttackTactic %}
                <strong>Tactic:</strong> {{ alert.MitreAttackTactic }}<br>
                {% endif %}
                {% if alert.MitreAttackTechnique %}
                <strong>Technique:</strong> {{ alert.MitreAttackTechnique }}
                {% endif %}
            </div>
            {% endif %}

            {% if alert.AIRecommendations %}
            <div class="ai-recommendations">
                <strong>🤖 AI Recommendations:</strong><br>
                {{ alert.AIRecommendations }}
            </div>
            {% endif %}

            <a href="{{ siem_url }}/alerts/{{ alert.AlertId }}" class="button">View Alert in SIEM →</a>
        </div>

        <div class="footer">
            <p>This is an automated alert from your SIEM system.</p>
            <p>Do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
        """)

        return template.render(
            alert=alert,
            severity=severity,
            color=color,
            siem_url=siem_url
        )

    def _render_incident_template(
        self,
        incident: Incident,
        severity: str,
        color: str,
        siem_url: str
    ) -> str:
        """Render incident email HTML template"""

        template = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }
        .container { max-width: 600px; margin: 20px auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { background: {{ color }}; color: white; padding: 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { padding: 30px; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; background: {{ color }}; color: white; }
        .info-grid { margin: 20px 0; }
        .info-row { display: flex; border-bottom: 1px solid #eee; padding: 10px 0; }
        .info-label { font-weight: bold; width: 140px; color: #666; }
        .info-value { flex: 1; }
        .description { background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; border-left: 4px solid {{ color }}; }
        .button { display: inline-block; padding: 12px 24px; background: {{ color }}; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }
        .footer { background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px; }
        .stats { display: flex; justify-content: space-around; margin: 20px 0; }
        .stat { text-align: center; }
        .stat-value { font-size: 32px; font-weight: bold; color: {{ color }}; }
        .stat-label { font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 Security Incident</h1>
        </div>

        <div class="content">
            <h2>{{ incident.Title }}</h2>
            <span class="badge">{{ severity }}</span>

            {% if incident.Description %}
            <div class="description">
                <strong>Description:</strong><br>
                {{ incident.Description }}
            </div>
            {% endif %}

            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{{ incident.AlertCount or 0 }}</div>
                    <div class="stat-label">Related Alerts</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ incident.AffectedAssetsCount or 0 }}</div>
                    <div class="stat-label">Affected Assets</div>
                </div>
            </div>

            <div class="info-grid">
                <div class="info-row">
                    <div class="info-label">Incident ID:</div>
                    <div class="info-value">#{{ incident.IncidentId }}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Status:</div>
                    <div class="info-value">{{ incident.Status }}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Category:</div>
                    <div class="info-value">{{ incident.Category or 'N/A' }}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Created:</div>
                    <div class="info-value">{{ incident.CreatedAt.strftime('%Y-%m-%d %H:%M:%S UTC') }}</div>
                </div>
            </div>

            <a href="{{ siem_url }}/incidents/{{ incident.IncidentId }}" class="button">View Incident in SIEM →</a>
        </div>

        <div class="footer">
            <p>This is an automated alert from your SIEM system.</p>
            <p>Do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
        """)

        return template.render(
            incident=incident,
            severity=severity,
            color=color,
            siem_url=siem_url
        )

    def _build_alert_text_body(self, alert: Alert, severity: str, siem_url: str) -> str:
        """Build plain text version of alert email"""
        lines = [
            "=" * 60,
            "SECURITY ALERT",
            "=" * 60,
            "",
            f"Title: {alert.Title}",
            f"Severity: {severity}",
            f"Alert ID: #{alert.AlertId}",
            f"Status: {alert.Status}",
            f"Category: {alert.Category or 'N/A'}",
            f"Created: {alert.CreatedAt}",
            ""
        ]

        if alert.Description:
            lines.extend([
                "Description:",
                alert.Description,
                ""
            ])

        if any([alert.Hostname, alert.Username, alert.SourceIP, alert.ProcessName]):
            lines.append("Context:")
            if alert.Hostname:
                lines.append(f"  Hostname: {alert.Hostname}")
            if alert.Username:
                lines.append(f"  Username: {alert.Username}")
            if alert.SourceIP:
                lines.append(f"  Source IP: {alert.SourceIP}")
            if alert.ProcessName:
                lines.append(f"  Process: {alert.ProcessName}")
            lines.append("")

        if alert.MitreAttackTactic or alert.MitreAttackTechnique:
            lines.append("MITRE ATT&CK:")
            if alert.MitreAttackTactic:
                lines.append(f"  Tactic: {alert.MitreAttackTactic}")
            if alert.MitreAttackTechnique:
                lines.append(f"  Technique: {alert.MitreAttackTechnique}")
            lines.append("")

        if alert.AIRecommendations:
            lines.extend([
                "AI Recommendations:",
                alert.AIRecommendations,
                ""
            ])

        lines.extend([
            f"View in SIEM: {siem_url}/alerts/{alert.AlertId}",
            "",
            "=" * 60,
            "This is an automated alert from your SIEM system.",
            "=" * 60
        ])

        return "\n".join(lines)

    def _build_incident_text_body(self, incident: Incident, severity: str, siem_url: str) -> str:
        """Build plain text version of incident email"""
        lines = [
            "=" * 60,
            "SECURITY INCIDENT",
            "=" * 60,
            "",
            f"Title: {incident.Title}",
            f"Severity: {severity}",
            f"Incident ID: #{incident.IncidentId}",
            f"Status: {incident.Status}",
            f"Category: {incident.Category or 'N/A'}",
            f"Created: {incident.CreatedAt}",
            "",
            f"Related Alerts: {incident.AlertCount or 0}",
            f"Affected Assets: {incident.AffectedAssetsCount or 0}",
            ""
        ]

        if incident.Description:
            lines.extend([
                "Description:",
                incident.Description,
                ""
            ])

        lines.extend([
            f"View in SIEM: {siem_url}/incidents/{incident.IncidentId}",
            "",
            "=" * 60,
            "This is an automated alert from your SIEM system.",
            "=" * 60
        ])

        return "\n".join(lines)


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service(
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    smtp_from_email: str,
    smtp_use_tls: bool = True
) -> EmailService:
    """Get or create email service instance"""
    global _email_service

    # Always create new instance with current settings
    _email_service = EmailService(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        smtp_from_email=smtp_from_email,
        smtp_use_tls=smtp_use_tls
    )

    return _email_service


async def send_email(
    to_emails: List[str],
    subject: str,
    html_body: str,
    text_body: Optional[str] = None
) -> tuple:
    """
    Convenience function to send email using settings from config
    Returns (success, error_message)
    """
    from app.config import settings

    if not settings.email_enabled:
        logger.warning("Email is disabled in settings")
        return False, "Email is disabled"

    service = get_email_service(
        smtp_host=settings.smtp_server,
        smtp_port=settings.smtp_port,
        smtp_username=settings.smtp_username,
        smtp_password=settings.smtp_password,
        smtp_from_email=settings.smtp_from_email,
        smtp_use_tls=settings.smtp_use_tls
    )

    return service.send_email(to_emails, subject, html_body, text_body)
