"""
Background Dashboard Statistics Updater
Periodically sends updated statistics to connected dashboard clients
"""

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import func, and_

from app.database import SessionLocal
from app.models.event import Event
from app.models.incident import Alert, Incident
from app.models.agent import Agent
from app.websocket import get_connection_manager
from app.config import settings

logger = logging.getLogger(__name__)


class DashboardUpdaterTask:
    """
    Background task that periodically sends dashboard statistics updates
    """

    def __init__(self, update_interval: int = 30):
        """
        Initialize dashboard updater

        Args:
            update_interval: Update interval in seconds (default: 30)
        """
        self.update_interval = update_interval
        self.is_running = False
        self.task = None

    async def start(self):
        """Start the dashboard updater task"""
        if self.is_running:
            logger.warning("Dashboard updater task is already running")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._run())
        logger.info(f"✓ Dashboard updater task started (interval: {self.update_interval}s)")

    async def stop(self):
        """Stop the dashboard updater task"""
        if not self.is_running:
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("Dashboard updater task stopped")

    async def _run(self):
        """Main loop for dashboard updater"""
        logger.info("Dashboard updater task is running...")

        while self.is_running:
            try:
                # Check if anyone is connected to dashboard
                manager = get_connection_manager()
                if manager.get_channel_count("dashboard") > 0:
                    await self._update_dashboard_statistics()

            except Exception as e:
                logger.error(f"Error in dashboard updater loop: {e}", exc_info=True)

            # Wait for next iteration
            await asyncio.sleep(self.update_interval)

    async def _update_dashboard_statistics(self):
        """
        Collect and broadcast dashboard statistics
        """
        db = SessionLocal()
        try:
            # Time range for statistics (last 24 hours)
            time_24h_ago = datetime.utcnow() - timedelta(hours=24)

            # Events statistics
            events_24h = db.query(func.count(Event.EventId)).filter(
                Event.EventTime >= time_24h_ago
            ).scalar() or 0

            events_last_hour = db.query(func.count(Event.EventId)).filter(
                Event.EventTime >= datetime.utcnow() - timedelta(hours=1)
            ).scalar() or 0

            high_severity_events = db.query(func.count(Event.EventId)).filter(
                and_(
                    Event.EventTime >= time_24h_ago,
                    Event.Severity >= 3
                )
            ).scalar() or 0

            # AI-detected attacks
            ai_attacks = db.query(func.count(Event.EventId)).filter(
                and_(
                    Event.EventTime >= time_24h_ago,
                    Event.AIIsAttack == True
                )
            ).scalar() or 0

            # Alerts statistics
            new_alerts = db.query(func.count(Alert.AlertId)).filter(
                and_(
                    Alert.CreatedAt >= time_24h_ago,
                    Alert.Status == 'new'
                )
            ).scalar() or 0

            critical_alerts = db.query(func.count(Alert.AlertId)).filter(
                and_(
                    Alert.CreatedAt >= time_24h_ago,
                    Alert.Severity >= 4
                )
            ).scalar() or 0

            # Incidents statistics
            open_incidents = db.query(func.count(Incident.IncidentId)).filter(
                Incident.Status.in_(['open', 'investigating', 'contained'])
            ).scalar() or 0

            # Agents statistics
            online_agents = db.query(func.count(Agent.AgentId)).filter(
                Agent.Status == 'online'
            ).scalar() or 0

            total_agents = db.query(func.count(Agent.AgentId)).scalar() or 0

            offline_agents = total_agents - online_agents

            # Prepare statistics message
            stats_data = {
                "events": {
                    "total_24h": events_24h,
                    "last_hour": events_last_hour,
                    "high_severity": high_severity_events,
                    "ai_attacks": ai_attacks
                },
                "alerts": {
                    "new": new_alerts,
                    "critical": critical_alerts
                },
                "incidents": {
                    "open": open_incidents
                },
                "agents": {
                    "online": online_agents,
                    "offline": offline_agents,
                    "total": total_agents
                },
                "updated_at": datetime.utcnow().isoformat()
            }

            # Broadcast to dashboard channel
            manager = get_connection_manager()
            await manager.broadcast_statistics(stats_data)

            logger.debug(f"Dashboard statistics updated and broadcasted to {manager.get_channel_count('dashboard')} clients")

        except Exception as e:
            logger.error(f"Error updating dashboard statistics: {e}", exc_info=True)
        finally:
            db.close()


# Global task instance
_dashboard_updater_task = None


def get_dashboard_updater_task() -> DashboardUpdaterTask:
    """Get the global dashboard updater task instance"""
    global _dashboard_updater_task
    if _dashboard_updater_task is None:
        _dashboard_updater_task = DashboardUpdaterTask(update_interval=30)
    return _dashboard_updater_task
