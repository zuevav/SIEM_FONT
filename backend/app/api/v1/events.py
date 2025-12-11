"""
Events API Endpoints
Handles event ingestion, retrieval, and statistics
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from typing import List, Optional
from datetime import datetime, timedelta
import json
import logging

from app.api.deps import get_db, get_current_user, require_analyst, require_admin, PaginationParams
from app.schemas.event import (
    EventCreate,
    EventBatchCreate,
    EventFilter,
    EventResponse,
    EventDetail,
    EventStatistics,
    EventsTimeline,
    EventsTimelineData
)
from app.schemas.auth import CurrentUser
from app.models.event import Event
from app.models.agent import Agent
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# EVENT INGESTION
# ============================================================================

@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def create_events_batch(
    batch: EventBatchCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Bulk insert events (from agents or manual import)
    Maximum 1000 events per batch
    """
    try:
        # Validate all agents exist
        agent_ids = {str(event.agent_id) for event in batch.events}
        agents = db.query(Agent).filter(Agent.AgentId.in_(agent_ids)).all()
        existing_agent_ids = {agent.AgentId for agent in agents}

        missing_agents = agent_ids - existing_agent_ids
        if missing_agents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown agents: {', '.join(missing_agents)}"
            )

        # Use stored procedure for high performance
        events_json = json.dumps([event.dict() for event in batch.events])

        # Call stored procedure
        db.execute(
            text("EXEC security_events.InsertEventsBatch @Events = :events"),
            {"events": events_json}
        )
        db.commit()

        logger.info(f"Inserted {len(batch.events)} events from {len(agent_ids)} agents")

        return {
            "success": True,
            "inserted": len(batch.events),
            "message": f"Successfully inserted {len(batch.events)} events"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error inserting events batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to insert events: {str(e)}"
        )


# ============================================================================
# EVENT RETRIEVAL
# ============================================================================

@router.get("", response_model=dict)
async def get_events(
    # Time filters
    start_time: Optional[datetime] = Query(None, description="Filter events after this time"),
    end_time: Optional[datetime] = Query(None, description="Filter events before this time"),
    last_hours: Optional[int] = Query(None, description="Get events from last N hours"),

    # Entity filters
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    min_severity: Optional[int] = Query(None, ge=0, le=4, description="Minimum severity (0-4)"),
    categories: Optional[str] = Query(None, description="Comma-separated categories"),
    source_types: Optional[str] = Query(None, description="Comma-separated source types"),

    # User/Network filters
    subject_user: Optional[str] = Query(None, description="Filter by subject username"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    destination_ip: Optional[str] = Query(None, description="Filter by destination IP"),
    process_name: Optional[str] = Query(None, description="Filter by process name"),

    # Search
    search_text: Optional[str] = Query(None, description="Full-text search in message"),

    # MITRE ATT&CK
    mitre_tactic: Optional[str] = Query(None, description="Filter by MITRE tactic"),
    mitre_technique: Optional[str] = Query(None, description="Filter by MITRE technique"),

    # AI Analysis
    ai_processed: Optional[bool] = Query(None, description="Filter by AI processing status"),
    ai_is_attack: Optional[bool] = Query(None, description="Filter by AI attack classification"),

    # Pagination
    limit: int = Query(100, ge=1, le=settings.max_events_per_query),
    offset: int = Query(0, ge=0),

    # Dependencies
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Search and filter events with pagination
    Returns events list and total count
    """
    try:
        # Build query
        query = db.query(Event)

        # Time filters
        if last_hours:
            start_time = datetime.utcnow() - timedelta(hours=last_hours)

        if start_time:
            query = query.filter(Event.EventTime >= start_time)
        if end_time:
            query = query.filter(Event.EventTime <= end_time)

        # Entity filters
        if agent_id:
            query = query.filter(Event.AgentId == agent_id)
        if min_severity is not None:
            query = query.filter(Event.Severity >= min_severity)

        if categories:
            cat_list = [c.strip() for c in categories.split(',')]
            query = query.filter(Event.Category.in_(cat_list))

        if source_types:
            type_list = [t.strip() for t in source_types.split(',')]
            query = query.filter(Event.SourceType.in_(type_list))

        # User/Network filters
        if subject_user:
            query = query.filter(Event.SubjectUser.ilike(f"%{subject_user}%"))
        if source_ip:
            query = query.filter(Event.SourceIP == source_ip)
        if destination_ip:
            query = query.filter(Event.DestinationIP == destination_ip)
        if process_name:
            query = query.filter(Event.ProcessName.ilike(f"%{process_name}%"))

        # Search
        if search_text:
            query = query.filter(Event.Message.ilike(f"%{search_text}%"))

        # MITRE ATT&CK
        if mitre_tactic:
            query = query.filter(Event.MitreAttackTactic == mitre_tactic)
        if mitre_technique:
            query = query.filter(Event.MitreAttackTechnique == mitre_technique)

        # AI Analysis
        if ai_processed is not None:
            query = query.filter(Event.AIProcessed == ai_processed)
        if ai_is_attack is not None:
            query = query.filter(Event.AIIsAttack == ai_is_attack)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        events = query.order_by(Event.EventTime.desc()).offset(offset).limit(limit).all()

        # Convert to response model
        events_response = [EventResponse.from_orm(event) for event in events]

        return {
            "events": events_response,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }

    except Exception as e:
        logger.error(f"Error retrieving events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve events: {str(e)}"
        )


@router.get("/{event_id}", response_model=EventDetail)
async def get_event_by_id(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get detailed event information by ID
    """
    event = db.query(Event).filter(Event.EventId == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found"
        )

    return EventDetail.from_orm(event)


# ============================================================================
# EVENT STATISTICS
# ============================================================================

@router.get("/stats/dashboard", response_model=EventStatistics)
async def get_event_statistics(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours (max 7 days)"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get event statistics for dashboard
    """
    try:
        # Use stored procedure for performance
        result = db.execute(
            text("EXEC security_events.GetDashboardStats @Hours = :hours"),
            {"hours": hours}
        )

        # Parse result sets
        stats_data = {}

        # First result set - Total counts
        total_row = result.fetchone()
        if total_row:
            stats_data['total_events'] = total_row[0]
            stats_data['critical_events'] = total_row[1]
            stats_data['high_events'] = total_row[2]
            stats_data['medium_events'] = total_row[3]
            stats_data['low_events'] = total_row[4]

        # Next result set - Events by severity
        result.nextset()
        events_by_severity = {}
        for row in result:
            severity_name = ['Info', 'Low', 'Medium', 'High', 'Critical'][row[0]]
            events_by_severity[severity_name] = row[1]

        # Next result set - Events by category
        result.nextset()
        events_by_category = {}
        for row in result:
            events_by_category[row[0] or 'Unknown'] = row[1]

        # Next result set - Events by source
        result.nextset()
        events_by_source = {}
        for row in result:
            events_by_source[row[0]] = row[1]

        # Next result set - Top agents
        result.nextset()
        top_agents = []
        for row in result:
            top_agents.append({
                'agent_id': row[0],
                'hostname': row[1],
                'event_count': row[2]
            })

        # Next result set - Top users
        result.nextset()
        top_users = []
        for row in result:
            if row[0]:  # Skip null users
                top_users.append({
                    'username': row[0],
                    'event_count': row[1]
                })

        # Next result set - Top processes
        result.nextset()
        top_processes = []
        for row in result:
            if row[0]:  # Skip null processes
                top_processes.append({
                    'process_name': row[0],
                    'event_count': row[1]
                })

        return EventStatistics(
            total_events=stats_data.get('total_events', 0),
            critical_events=stats_data.get('critical_events', 0),
            high_events=stats_data.get('high_events', 0),
            medium_events=stats_data.get('medium_events', 0),
            low_events=stats_data.get('low_events', 0),
            events_by_severity=events_by_severity,
            events_by_category=events_by_category,
            events_by_source=events_by_source,
            top_agents=top_agents,
            top_users=top_users,
            top_processes=top_processes
        )

    except Exception as e:
        logger.error(f"Error getting event statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/stats/timeline", response_model=EventsTimeline)
async def get_events_timeline(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    interval: str = Query("hour", pattern="^(hour|day)$", description="Time interval"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get events timeline for charts
    Returns time-series data grouped by interval
    """
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        end_time = datetime.utcnow()

        # Build time grouping SQL based on interval
        if interval == "hour":
            time_group = "DATEADD(HOUR, DATEDIFF(HOUR, 0, EventTime), 0)"
        else:  # day
            time_group = "DATEADD(DAY, DATEDIFF(DAY, 0, EventTime), 0)"

        # Query timeline data
        query = text(f"""
            SELECT
                {time_group} as TimeSlot,
                Severity,
                COUNT(*) as EventCount
            FROM security_events.Events
            WHERE EventTime >= :start_time AND EventTime <= :end_time
            GROUP BY {time_group}, Severity
            ORDER BY TimeSlot, Severity
        """)

        result = db.execute(query, {
            "start_time": start_time,
            "end_time": end_time
        })

        timeline_data = []
        for row in result:
            timeline_data.append(EventsTimelineData(
                timestamp=row[0],
                severity=row[1],
                count=row[2]
            ))

        return EventsTimeline(
            data=timeline_data,
            start_time=start_time,
            end_time=end_time,
            interval=interval
        )

    except Exception as e:
        logger.error(f"Error getting events timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get timeline: {str(e)}"
        )


# ============================================================================
# EVENT CORRELATION (For Detection Rules)
# ============================================================================

@router.get("/correlate/similar")
async def get_similar_events(
    event_id: int,
    hours: int = Query(24, ge=1, le=168, description="Time window to search"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Find similar events (for correlation analysis)
    Requires analyst role
    """
    # Get the reference event
    reference = db.query(Event).filter(Event.EventId == event_id).first()

    if not reference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found"
        )

    # Build similarity query
    start_time = reference.EventTime - timedelta(hours=hours)
    end_time = reference.EventTime + timedelta(hours=hours)

    query = db.query(Event).filter(
        and_(
            Event.EventId != event_id,
            Event.EventTime >= start_time,
            Event.EventTime <= end_time
        )
    )

    # Match on similar attributes
    conditions = []

    if reference.AgentId:
        conditions.append(Event.AgentId == reference.AgentId)
    if reference.SubjectUser:
        conditions.append(Event.SubjectUser == reference.SubjectUser)
    if reference.SourceIP:
        conditions.append(Event.SourceIP == reference.SourceIP)
    if reference.ProcessName:
        conditions.append(Event.ProcessName == reference.ProcessName)
    if reference.Category:
        conditions.append(Event.Category == reference.Category)

    if conditions:
        query = query.filter(or_(*conditions))

    similar_events = query.order_by(Event.EventTime.desc()).limit(limit).all()

    return {
        "reference_event_id": event_id,
        "similar_events": [EventResponse.from_orm(event) for event in similar_events],
        "count": len(similar_events)
    }


# ============================================================================
# EVENT EXPORT (For Analysis)
# ============================================================================

@router.post("/export")
async def export_events(
    filters: EventFilter,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Export events to JSON (for external analysis or backup)
    Requires analyst role
    Maximum 10,000 events per export
    """
    try:
        # Build query with filters
        query = db.query(Event)

        if filters.start_time:
            query = query.filter(Event.EventTime >= filters.start_time)
        if filters.end_time:
            query = query.filter(Event.EventTime <= filters.end_time)
        if filters.agent_id:
            query = query.filter(Event.AgentId == str(filters.agent_id))
        if filters.min_severity is not None:
            query = query.filter(Event.Severity >= filters.min_severity)

        # Limit export size
        max_export = min(filters.limit, 10000)
        events = query.order_by(Event.EventTime.desc()).limit(max_export).all()

        # Convert to dict
        export_data = {
            "export_time": datetime.utcnow().isoformat(),
            "exported_by": current_user.username,
            "filters": filters.dict(exclude_none=True),
            "event_count": len(events),
            "events": [EventDetail.from_orm(event).dict() for event in events]
        }

        logger.info(f"User {current_user.username} exported {len(events)} events")

        return export_data

    except Exception as e:
        logger.error(f"Error exporting events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export events: {str(e)}"
        )
