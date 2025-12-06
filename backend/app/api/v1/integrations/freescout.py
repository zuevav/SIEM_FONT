"""
FreeScout Integration API Endpoints
Handles ticket creation, webhooks, and synchronization
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
import logging
import requests
import hashlib
import hmac
from datetime import datetime

from app.api.deps import get_db, get_current_user, require_analyst
from app.schemas.settings import (
    FreeScoutTicketCreate,
    FreeScoutTicketResponse,
    FreeScoutWebhookPayload,
    FreeScoutSyncResponse
)
from app.schemas.auth import CurrentUser
from app.models.incident import Alert
from app.api.v1.settings import get_setting

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# FREESCOUT CLIENT
# ============================================================================

class FreeScoutClient:
    """FreeScout API client"""

    def __init__(self, url: str, api_key: str, mailbox_id: int):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.mailbox_id = mailbox_id
        self.headers = {
            'X-FreeScout-API-Key': api_key,
            'Content-Type': 'application/json'
        }

    def create_ticket_from_alert(self, alert: Alert, note: Optional[str] = None) -> dict:
        """
        Create FreeScout ticket from SIEM alert
        """
        try:
            # Severity names
            severity_names = ['Info', 'Low', 'Medium', 'High', 'Critical']
            severity = severity_names[alert.Severity] if 0 <= alert.Severity < 5 else 'Unknown'

            # Build ticket subject
            subject = f"[SIEM Alert #{alert.AlertId}] {alert.Title}"

            # Build ticket body
            body_parts = [
                f"<h2>SIEM Alert: {alert.Title}</h2>",
                f"<p><strong>Alert ID:</strong> {alert.AlertId}</p>",
                f"<p><strong>Severity:</strong> {severity} ({alert.Severity})</p>",
                f"<p><strong>Status:</strong> {alert.Status}</p>",
                f"<p><strong>Category:</strong> {alert.Category or 'N/A'}</p>",
                f"<p><strong>Created:</strong> {alert.CreatedAt}</p>",
                "",
                f"<h3>Description</h3>",
                f"<p>{alert.Description or 'No description provided'}</p>",
            ]

            # Add context information
            if any([alert.Hostname, alert.Username, alert.SourceIP]):
                body_parts.extend([
                    "",
                    "<h3>Context</h3>",
                    "<ul>"
                ])
                if alert.Hostname:
                    body_parts.append(f"<li><strong>Hostname:</strong> {alert.Hostname}</li>")
                if alert.Username:
                    body_parts.append(f"<li><strong>Username:</strong> {alert.Username}</li>")
                if alert.SourceIP:
                    body_parts.append(f"<li><strong>Source IP:</strong> {alert.SourceIP}</li>")
                if alert.ProcessName:
                    body_parts.append(f"<li><strong>Process:</strong> {alert.ProcessName}</li>")
                body_parts.append("</ul>")

            # Add MITRE ATT&CK
            if alert.MitreAttackTactic or alert.MitreAttackTechnique:
                body_parts.extend([
                    "",
                    "<h3>MITRE ATT&CK</h3>",
                    "<ul>"
                ])
                if alert.MitreAttackTactic:
                    body_parts.append(f"<li><strong>Tactic:</strong> {alert.MitreAttackTactic}</li>")
                if alert.MitreAttackTechnique:
                    body_parts.append(f"<li><strong>Technique:</strong> {alert.MitreAttackTechnique}</li>")
                body_parts.append("</ul>")

            # Add AI recommendations
            if alert.AIRecommendations:
                body_parts.extend([
                    "",
                    "<h3>AI Recommendations</h3>",
                    f"<p>{alert.AIRecommendations}</p>"
                ])

            # Add note if provided
            if note:
                body_parts.extend([
                    "",
                    "<h3>Additional Note</h3>",
                    f"<p>{note}</p>"
                ])

            body_parts.extend([
                "",
                "<hr>",
                "<p><em>This ticket was automatically created by the SIEM system.</em></p>"
            ])

            body = "\n".join(body_parts)

            # Create ticket payload
            payload = {
                "type": "email",
                "mailboxId": self.mailbox_id,
                "subject": subject,
                "customer": {
                    "email": "siem@system.local"
                },
                "threads": [
                    {
                        "type": "customer",
                        "text": body,
                    }
                ],
                "tags": [
                    "siem",
                    f"severity-{severity.lower()}",
                    alert.Category.lower() if alert.Category else "uncategorized"
                ],
                "customFields": {
                    "alert_id": alert.AlertId,
                    "severity": alert.Severity,
                }
            }

            # Send request
            response = requests.post(
                f"{self.url}/api/conversations",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 201:
                data = response.json()
                logger.info(f"FreeScout ticket created for alert {alert.AlertId}: "
                          f"conversation #{data.get('number')}")
                return {
                    "success": True,
                    "freescout_id": data.get('id'),
                    "ticket_number": data.get('number'),
                    "ticket_url": f"{self.url}/conversation/{data.get('number')}"
                }
            else:
                logger.error(f"Failed to create FreeScout ticket: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}"
                }

        except requests.exceptions.Timeout:
            logger.error("FreeScout API timeout")
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.RequestException as e:
            logger.error(f"FreeScout API error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error creating FreeScout ticket: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def update_ticket_status(self, conversation_id: int, status: str) -> bool:
        """
        Update FreeScout ticket status
        """
        try:
            # Map SIEM status to FreeScout status
            status_map = {
                'new': 'active',
                'acknowledged': 'active',
                'investigating': 'active',
                'resolved': 'closed',
                'false_positive': 'spam'
            }

            freescout_status = status_map.get(status, 'active')

            payload = {
                "status": freescout_status
            }

            response = requests.patch(
                f"{self.url}/api/conversations/{conversation_id}",
                headers=self.headers,
                json=payload,
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error updating FreeScout ticket status: {e}")
            return False

    def add_note(self, conversation_id: int, note: str, user: str = "SIEM System") -> bool:
        """
        Add note to FreeScout ticket
        """
        try:
            payload = {
                "type": "note",
                "text": f"<p><strong>{user}:</strong></p><p>{note}</p>",
                "imported": False
            }

            response = requests.post(
                f"{self.url}/api/conversations/{conversation_id}/threads",
                headers=self.headers,
                json=payload,
                timeout=10
            )

            return response.status_code == 201

        except Exception as e:
            logger.error(f"Error adding note to FreeScout ticket: {e}")
            return False


# ============================================================================
# FREESCOUT ENDPOINTS
# ============================================================================

@router.post("/create-ticket", response_model=FreeScoutTicketResponse)
async def create_freescout_ticket(
    ticket_data: FreeScoutTicketCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Create FreeScout ticket from alert (analyst or admin)
    """
    try:
        # Get FreeScout settings
        freescout_enabled = get_setting(db, 'freescout_enabled', False)
        if not freescout_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FreeScout integration is not enabled"
            )

        freescout_url = get_setting(db, 'freescout_url')
        freescout_api_key = get_setting(db, 'freescout_api_key')
        freescout_mailbox_id = get_setting(db, 'freescout_mailbox_id')

        if not all([freescout_url, freescout_api_key, freescout_mailbox_id]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FreeScout is not fully configured"
            )

        # Get alert
        alert = db.query(Alert).filter(Alert.AlertId == ticket_data.alert_id).first()
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {ticket_data.alert_id} not found"
            )

        # Create FreeScout client
        client = FreeScoutClient(freescout_url, freescout_api_key, freescout_mailbox_id)

        # Create ticket
        result = client.create_ticket_from_alert(alert, ticket_data.note)

        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get('error', 'Failed to create ticket')
            )

        # TODO: Store ticket reference in database (FreeScoutTickets table)
        # For now, just return the result

        logger.info(f"FreeScout ticket #{result['ticket_number']} created for alert {ticket_data.alert_id} "
                   f"by {current_user.username}")

        return FreeScoutTicketResponse(
            success=True,
            ticket_number=result['ticket_number'],
            ticket_url=result['ticket_url'],
            freescout_id=result['freescout_id'],
            message=f"Ticket #{result['ticket_number']} created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating FreeScout ticket: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create FreeScout ticket: {str(e)}"
        )


@router.post("/webhook")
async def freescout_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_freescout_signature: Optional[str] = Header(None)
):
    """
    Handle FreeScout webhooks (ticket updates, status changes, etc.)
    This endpoint does NOT require authentication (uses webhook signature instead)
    """
    try:
        # Get webhook secret
        webhook_secret = get_setting(db, 'freescout_webhook_secret')

        # Verify signature if secret is configured
        if webhook_secret and x_freescout_signature:
            body = await request.body()
            expected_signature = hmac.new(
                webhook_secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, x_freescout_signature):
                logger.warning("FreeScout webhook signature verification failed")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature"
                )

        # Parse payload
        payload = await request.json()
        logger.info(f"Received FreeScout webhook: {payload.get('event')}")

        # Process webhook based on event type
        event = payload.get('event')
        conversation_id = payload.get('conversation', {}).get('id')

        if event == 'conversation.status_changed':
            # TODO: Sync ticket status back to alert
            new_status = payload.get('conversation', {}).get('status')
            logger.info(f"FreeScout conversation {conversation_id} status changed to {new_status}")

            # Map FreeScout status to SIEM status
            status_map = {
                'active': 'investigating',
                'closed': 'resolved',
                'spam': 'false_positive'
            }

            # TODO: Find alert by FreeScout conversation ID and update status
            # This requires FreeScoutTickets table to map conversation_id -> alert_id

        elif event == 'conversation.note_added':
            # TODO: Add note to alert comments
            logger.info(f"Note added to FreeScout conversation {conversation_id}")

        elif event == 'conversation.created':
            # Ticket created (probably by us, ignore)
            logger.info(f"FreeScout conversation {conversation_id} created")

        return {"success": True, "message": "Webhook processed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing FreeScout webhook: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/sync")
async def sync_freescout_tickets(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Manually sync FreeScout ticket statuses (analyst or admin)
    """
    try:
        # Get FreeScout settings
        freescout_enabled = get_setting(db, 'freescout_enabled', False)
        if not freescout_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FreeScout integration is not enabled"
            )

        # TODO: Implement sync logic
        # 1. Get all open tickets from database
        # 2. Query FreeScout API for each ticket
        # 3. Update SIEM alert status if FreeScout status changed
        # 4. Add notes from FreeScout to SIEM alerts

        logger.info(f"FreeScout sync requested by {current_user.username}")

        return FreeScoutSyncResponse(
            success=True,
            message="Sync completed (placeholder - full implementation pending)",
            synced_tickets=0,
            errors=[]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing FreeScout tickets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync FreeScout tickets: {str(e)}"
        )
