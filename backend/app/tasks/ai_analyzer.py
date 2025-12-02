"""
Background AI Analyzer Task
Automatically analyzes security events using configured AI provider
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database import SessionLocal
from app.models.event import Event
from app.models.incident import Alert
from app.services import get_ai_service, AIService
from app.websocket import get_connection_manager
from app.config import settings

logger = logging.getLogger(__name__)


class AIAnalyzerTask:
    """
    Background task that automatically analyzes security events
    """

    def __init__(self):
        self.is_running = False
        self.task = None
        self.ai_available = False

    async def start(self):
        """Start the background AI analyzer task"""
        if self.is_running:
            logger.warning("AI Analyzer task is already running")
            return

        # Check if AI service is available
        try:
            ai_service = get_ai_service()
            self.ai_available = ai_service.is_enabled()
            if not self.ai_available:
                logger.warning("AI service is not available - AI analyzer will not start")
                return
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._run())
        logger.info(f"✓ AI Analyzer task started (interval: {settings.ai_process_interval_sec}s, batch: {settings.ai_batch_size})")

    async def stop(self):
        """Stop the background AI analyzer task"""
        if not self.is_running:
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("AI Analyzer task stopped")

    async def _run(self):
        """Main loop for AI analyzer"""
        logger.info("AI Analyzer task is running...")

        while self.is_running:
            try:
                await self._process_events()

            except Exception as e:
                logger.error(f"Error in AI analyzer loop: {e}", exc_info=True)

            # Wait for next iteration
            await asyncio.sleep(settings.ai_process_interval_sec)

    async def _process_events(self):
        """
        Process unanalyzed events from database
        """
        db = SessionLocal()
        try:
            # Get AI service
            ai_service = get_ai_service()

            # Get unanalyzed events (oldest first, limit batch size)
            unanalyzed_events = db.query(Event).filter(
                or_(
                    Event.AIProcessed == False,
                    Event.AIProcessed == None
                )
            ).order_by(Event.EventTime.asc()).limit(settings.ai_batch_size).all()

            if not unanalyzed_events:
                return  # No events to process

            logger.info(f"Processing {len(unanalyzed_events)} unanalyzed events...")

            processed_count = 0
            high_risk_count = 0

            for event in unanalyzed_events:
                try:
                    # Prepare event data for analysis
                    event_data = {
                        "source_type": event.SourceType,
                        "event_code": event.EventCode,
                        "severity": event.Severity,
                        "computer": event.Computer,
                        "event_time": event.EventTime.isoformat() if event.EventTime else None,
                        "subject_user": event.SubjectUser,
                        "subject_domain": event.SubjectDomain,
                        "target_user": event.TargetUser,
                        "process_name": event.ProcessName,
                        "process_command_line": event.ProcessCommandLine,
                        "source_ip": event.SourceIP,
                        "source_port": event.SourcePort,
                        "destination_ip": event.DestinationIP,
                        "destination_port": event.DestinationPort,
                        "file_path": event.FilePath,
                        "registry_path": event.RegistryPath,
                        "message": event.Message
                    }

                    # Analyze with AI
                    analysis = await ai_service.analyze_event(event_data)

                    # Update event with AI analysis
                    event.AIProcessed = analysis.get("ai_processed", True)
                    event.AIIsAttack = analysis.get("ai_is_attack")
                    event.AIScore = analysis.get("ai_score")
                    event.AICategory = analysis.get("ai_category")
                    event.AIDescription = analysis.get("ai_description")
                    event.AIConfidence = analysis.get("ai_confidence")
                    event.AIProcessedAt = datetime.utcnow()

                    processed_count += 1

                    # Check if high-risk event (score > 70 or classified as attack)
                    if (analysis.get("ai_is_attack") or (analysis.get("ai_score") and analysis.get("ai_score") > 70)):
                        high_risk_count += 1

                        # Broadcast high-risk event via WebSocket
                        await self._broadcast_high_risk_event(event, analysis)

                        # Auto-create alert for very high scores (>85)
                        if analysis.get("ai_score") and analysis.get("ai_score") > 85:
                            await self._create_auto_alert(event, analysis, db)

                except Exception as e:
                    logger.error(f"Error analyzing event {event.EventId}: {e}", exc_info=True)
                    # Mark as processed with error
                    event.AIProcessed = False
                    event.AIDescription = f"Ошибка AI-анализа: {str(e)}"

            # Commit all changes
            db.commit()

            if processed_count > 0:
                logger.info(f"✓ Processed {processed_count} events, {high_risk_count} high-risk detected")

        except Exception as e:
            logger.error(f"Error processing events batch: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

    async def _broadcast_high_risk_event(self, event: Event, analysis: Dict[str, Any]):
        """
        Broadcast high-risk event via WebSocket

        Args:
            event: Event model instance
            analysis: AI analysis results
        """
        try:
            manager = get_connection_manager()

            notification_data = {
                "event_id": event.EventId,
                "computer": event.Computer,
                "severity": event.Severity,
                "ai_score": analysis.get("ai_score"),
                "ai_category": analysis.get("ai_category"),
                "ai_description": analysis.get("ai_description"),
                "message": event.Message[:200] if event.Message else "",
                "timestamp": event.EventTime.isoformat() if event.EventTime else None
            }

            # Broadcast to dashboard and events channels
            await manager.broadcast_notification(
                notification_data,
                severity="warning" if analysis.get("ai_score", 0) < 90 else "critical"
            )

        except Exception as e:
            logger.error(f"Error broadcasting high-risk event: {e}")

    async def _create_auto_alert(self, event: Event, analysis: Dict[str, Any], db: Session):
        """
        Auto-create alert for very high-risk events

        Args:
            event: Event model instance
            analysis: AI analysis results
            db: Database session
        """
        try:
            # Check if alert already exists for this event
            existing_alert = db.query(Alert).filter(
                Alert.EventIds.contains(f'[{event.EventId}]')
            ).first()

            if existing_alert:
                return  # Alert already exists

            # Create new alert
            alert = Alert(
                Severity=max(event.Severity, 4),  # At least High
                Title=f"Автоматический алерт: {analysis.get('ai_category', 'Подозрительная активность')}",
                Description=analysis.get('ai_description', 'Обнаружена потенциально опасная активность'),
                Category=analysis.get('ai_category', 'ai_detected'),
                EventIds=f'[{event.EventId}]',
                EventCount=1,
                FirstEventTime=event.EventTime,
                LastEventTime=event.EventTime,
                AgentId=str(event.AgentId) if event.AgentId else None,
                Hostname=event.Computer,
                Username=event.SubjectUser,
                SourceIP=event.SourceIP,
                ProcessName=event.ProcessName,
                Status='new',
                Priority=4,  # High priority
                AIAnalysis=str(analysis),
                AIConfidence=analysis.get('ai_confidence'),
                CreatedAt=datetime.utcnow()
            )

            db.add(alert)
            db.flush()  # Get alert ID

            # Broadcast new alert via WebSocket
            manager = get_connection_manager()
            await manager.broadcast_alert({
                "alert_id": alert.AlertId,
                "title": alert.Title,
                "severity": alert.Severity,
                "category": alert.Category,
                "hostname": alert.Hostname,
                "status": alert.Status
            }, action="created")

            logger.info(f"✓ Auto-created alert {alert.AlertId} for high-risk event {event.EventId}")

        except Exception as e:
            logger.error(f"Error creating auto-alert: {e}", exc_info=True)


# Global task instance
_ai_analyzer_task = None


def get_ai_analyzer_task() -> AIAnalyzerTask:
    """Get the global AI analyzer task instance"""
    global _ai_analyzer_task
    if _ai_analyzer_task is None:
        _ai_analyzer_task = AIAnalyzerTask()
    return _ai_analyzer_task
