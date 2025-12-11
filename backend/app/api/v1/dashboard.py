"""
Dashboard API Endpoints
Combined statistics for the main dashboard
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, text
from datetime import datetime, timedelta
import logging

from app.api.deps import get_db, get_current_user
from app.schemas.auth import CurrentUser
from app.models.event import Event
from app.models.incident import Alert, Incident
from app.models.agent import Agent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get combined dashboard statistics for events, alerts, incidents and agents
    Returns data in the format expected by the frontend Dashboard component
    """
    try:
        now = datetime.utcnow()
        start_24h = now - timedelta(hours=24)
        start_7d = now - timedelta(days=7)
        start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # ============================================================================
        # EVENTS STATISTICS
        # ============================================================================

        # Total events in last 24 hours
        events_24h = db.execute(
            text("SELECT COUNT(*) FROM security_events.events WHERE event_time >= :start_time"),
            {"start_time": start_24h}
        ).scalar() or 0

        # Total events in last 7 days
        events_7d = db.execute(
            text("SELECT COUNT(*) FROM security_events.events WHERE event_time >= :start_time"),
            {"start_time": start_7d}
        ).scalar() or 0

        # Calculate rate per hour (events in last hour)
        start_1h = now - timedelta(hours=1)
        events_1h = db.execute(
            text("SELECT COUNT(*) FROM security_events.events WHERE event_time >= :start_time"),
            {"start_time": start_1h}
        ).scalar() or 0

        # ============================================================================
        # ALERTS STATISTICS
        # ============================================================================

        # New alerts (status = 'new')
        alerts_new = db.query(func.count(Alert.AlertId)).filter(
            Alert.Status == 'new'
        ).scalar() or 0

        # Acknowledged alerts
        alerts_acknowledged = db.query(func.count(Alert.AlertId)).filter(
            Alert.Status == 'acknowledged'
        ).scalar() or 0

        # Total open alerts (new + acknowledged + investigating)
        alerts_total_open = db.query(func.count(Alert.AlertId)).filter(
            Alert.Status.in_(['new', 'acknowledged', 'investigating'])
        ).scalar() or 0

        # ============================================================================
        # INCIDENTS STATISTICS
        # ============================================================================

        # Open incidents
        incidents_open = db.query(func.count(Incident.IncidentId)).filter(
            Incident.Status == 'open'
        ).scalar() or 0

        # Investigating incidents
        incidents_investigating = db.query(func.count(Incident.IncidentId)).filter(
            Incident.Status == 'investigating'
        ).scalar() or 0

        # Total incidents this month
        incidents_this_month = db.query(func.count(Incident.IncidentId)).filter(
            Incident.CreatedAt >= start_month
        ).scalar() or 0

        # ============================================================================
        # AGENTS STATISTICS
        # ============================================================================

        # Total agents
        agents_total = db.query(func.count(Agent.agent_id)).scalar() or 0

        # Online agents (seen in last 5 minutes)
        agent_online_threshold = now - timedelta(minutes=5)
        agents_online = db.query(func.count(Agent.agent_id)).filter(
            Agent.last_seen >= agent_online_threshold
        ).scalar() or 0

        # Offline agents
        agents_offline = agents_total - agents_online

        # ============================================================================
        # BUILD RESPONSE
        # ============================================================================

        return {
            "events": {
                "total_24h": events_24h,
                "total_7d": events_7d,
                "rate_per_hour": events_1h
            },
            "alerts": {
                "new": alerts_new,
                "acknowledged": alerts_acknowledged,
                "total_open": alerts_total_open
            },
            "incidents": {
                "open": incidents_open,
                "investigating": incidents_investigating,
                "total_this_month": incidents_this_month
            },
            "agents": {
                "online": agents_online,
                "offline": agents_offline,
                "total": agents_total
            }
        }

    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard statistics: {str(e)}"
        )
