"""
File Integrity Monitoring (FIM) API Endpoints
Handles Sysmon file and registry events
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import json

from app.api.deps import get_db, get_current_user
from app.schemas.auth import CurrentUser
from app.models.event import Event
from app.config import settings

logger = logging.getLogger(__name__)


def parse_event_data(raw_event: str) -> dict:
    """Parse raw_event JSON string to dict, return empty dict on failure"""
    if not raw_event:
        return {}
    try:
        return json.loads(raw_event)
    except (json.JSONDecodeError, TypeError):
        return {}

router = APIRouter()

# Sysmon Event IDs for FIM
FIM_EVENT_CODES = {
    11: "File Created",
    23: "File Deleted",
    26: "File Delete Detected",
    12: "Registry Object Added/Deleted",
    13: "Registry Value Set",
    14: "Registry Key/Value Renamed"
}


@router.get("/events")
async def get_fim_events(
    # Time filters
    start_time: Optional[datetime] = Query(None, description="Filter events after this time"),
    end_time: Optional[datetime] = Query(None, description="Filter events before this time"),
    last_hours: Optional[int] = Query(24, description="Get events from last N hours"),

    # FIM-specific filters
    event_type: Optional[str] = Query(None, description="Event type: file_created, file_deleted, registry_set, etc."),
    file_path: Optional[str] = Query(None, description="Filter by file path (partial match)"),
    registry_key: Optional[str] = Query(None, description="Filter by registry key (partial match)"),
    process_name: Optional[str] = Query(None, description="Filter by process name"),

    # General filters
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    hostname: Optional[str] = Query(None, description="Filter by hostname"),

    # Pagination
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),

    # Dependencies
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get File Integrity Monitoring events (Sysmon file/registry changes)
    Returns file creations, deletions, and registry modifications
    """
    try:
        # Build query - filter for Sysmon events only
        query = db.query(Event).filter(
            or_(
                Event.source_type == "Sysmon",
                Event.provider.ilike("%Sysmon%")
            )
        )

        # Filter by FIM event codes
        query = query.filter(Event.event_code.in_(list(FIM_EVENT_CODES.keys())))

        # Time filters
        if last_hours:
            start_time = datetime.utcnow() - timedelta(hours=last_hours)

        if start_time:
            query = query.filter(Event.event_time >= start_time)
        if end_time:
            query = query.filter(Event.event_time <= end_time)

        # Event type filter
        if event_type:
            event_code_map = {
                "file_created": 11,
                "file_deleted": [23, 26],
                "registry_create": 12,
                "registry_set": 13,
                "registry_rename": 14
            }
            if event_type in event_code_map:
                codes = event_code_map[event_type]
                if isinstance(codes, list):
                    query = query.filter(Event.event_code.in_(codes))
                else:
                    query = query.filter(Event.event_code == codes)

        # FIM-specific filters
        if file_path:
            query = query.filter(Event.file_path.ilike(f"%{file_path}%"))

        if registry_key:
            # FIX BUG-005: Use snake_case field registry_key instead of JSONB access
            # Event model has registry_key column directly
            query = query.filter(Event.registry_key.ilike(f"%{registry_key}%"))

        if process_name:
            query = query.filter(Event.process_name.ilike(f"%{process_name}%"))

        # General filters
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)

        if hostname:
            query = query.filter(Event.computer.ilike(f"%{hostname}%"))

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        events = query.order_by(Event.event_time.desc()).offset(offset).limit(limit).all()

        # Convert to dict with FIM-specific fields
        # FIX BUG-005, BUG-011: Use snake_case attributes and parse raw_event JSON
        fim_events = []
        for event in events:
            # Parse raw_event JSON for additional FIM data
            event_data = parse_event_data(event.raw_event)

            event_dict = {
                "event_id": event.event_id,
                "event_time": event.event_time.isoformat() if event.event_time else None,
                "event_code": event.event_code,
                "event_type": FIM_EVENT_CODES.get(event.event_code, "Unknown"),
                "hostname": event.computer,  # Event model uses 'computer', not 'hostname'
                "agent_id": str(event.agent_id) if event.agent_id else None,
                "file_path": event.file_path,
                "process_name": event.process_name,
                "target_user": event.target_user,
                "message": event.message,
                "severity": event.severity,
                "category": event.category,
                # Use model fields or parse from raw_event JSON
                "file_hash": event.file_hash or event_data.get("FileHash") or event_data.get("Hashes"),
                "registry_key": event.registry_key or event_data.get("RegistryKey"),
                "registry_value": event.registry_value or event_data.get("RegistryValue"),
                "event_type_detail": event_data.get("EventType"),  # CreateKey, SetValue, etc.
                "details": event_data.get("Details"),  # Registry value details
                "new_name": event_data.get("NewName"),  # For rename operations
            }
            fim_events.append(event_dict)

        return {
            "events": fim_events,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }

    except Exception as e:
        logger.error(f"Error retrieving FIM events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve FIM events: {str(e)}"
        )


@router.get("/events/{event_id}")
async def get_fim_event_detail(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get detailed FIM event information by ID
    """
    event = db.query(Event).filter(
        Event.event_id == event_id,
        or_(
            Event.source_type == "Sysmon",
            Event.provider.ilike("%Sysmon%")
        ),
        Event.event_code.in_(list(FIM_EVENT_CODES.keys()))
    ).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FIM event with ID {event_id} not found"
        )

    # FIX BUG-005, BUG-011: Use snake_case attributes and parse raw_event JSON
    event_data = parse_event_data(event.raw_event)

    return {
        "event_id": event.event_id,
        "event_time": event.event_time.isoformat() if event.event_time else None,
        "event_code": event.event_code,
        "event_type": FIM_EVENT_CODES.get(event.event_code, "Unknown"),
        "hostname": event.computer,
        "agent_id": str(event.agent_id) if event.agent_id else None,
        "source_type": event.source_type,
        "provider": event.provider,
        "severity": event.severity,
        "category": event.category,
        "message": event.message,

        # File details
        "file_path": event.file_path,
        "file_hash": event.file_hash or event_data.get("FileHash") or event_data.get("Hashes"),

        # Registry details (use model fields first, then parsed event_data)
        "registry_key": event.registry_key or event_data.get("RegistryKey"),
        "registry_value": event.registry_value or event_data.get("RegistryValue"),
        "registry_details": event_data.get("Details"),
        "event_type_detail": event_data.get("EventType"),
        "target_object": event_data.get("TargetObject"),
        "new_name": event_data.get("NewName"),

        # Process details
        "process_name": event.process_name,
        "process_id": event.process_id,
        "process_command_line": event.process_command_line,

        # User details
        "target_user": event.target_user,
        "subject_user": event.subject_user,

        # Full event data
        "event_data": event_data,
        "raw_xml": event.raw_event
    }


@router.get("/statistics")
async def get_fim_statistics(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours (max 7 days)"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get FIM statistics for the specified time window
    """
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours)

        # Base query for FIM events
        base_query = db.query(Event).filter(
            or_(
                Event.source_type == "Sysmon",
                Event.provider.ilike("%Sysmon%")
            ),
            Event.event_code.in_(list(FIM_EVENT_CODES.keys())),
            Event.event_time >= start_time
        )

        # Total FIM events
        total_events = base_query.count()

        # Events by type
        events_by_type = {}
        for event_code, event_name in FIM_EVENT_CODES.items():
            count = base_query.filter(Event.event_code == event_code).count()
            events_by_type[event_name] = count

        # Top modified paths (files and registry)
        top_file_paths = db.query(
            Event.file_path,
            func.count(Event.event_id).label('count')
        ).filter(
            Event.event_id.in_(base_query.with_entities(Event.event_id).subquery()),
            Event.file_path.isnot(None)
        ).group_by(Event.file_path).order_by(func.count(Event.event_id).desc()).limit(10).all()

        # Top processes making changes
        top_processes = db.query(
            Event.process_name,
            func.count(Event.event_id).label('count')
        ).filter(
            Event.event_id.in_(base_query.with_entities(Event.event_id).subquery()),
            Event.process_name.isnot(None)
        ).group_by(Event.process_name).order_by(func.count(Event.event_id).desc()).limit(10).all()

        # Events by severity
        events_by_severity = db.query(
            Event.severity,
            func.count(Event.event_id).label('count')
        ).filter(
            Event.event_id.in_(base_query.with_entities(Event.event_id).subquery())
        ).group_by(Event.severity).all()

        severity_map = {0: 'Info', 1: 'Low', 2: 'Medium', 3: 'High', 4: 'Critical'}
        events_by_severity_dict = {
            severity_map.get(sev, 'Unknown'): count
            for sev, count in events_by_severity
        }

        # Critical file changes (high severity)
        critical_changes = base_query.filter(Event.severity >= 3).count()

        return {
            "time_window_hours": hours,
            "total_fim_events": total_events,
            "critical_changes": critical_changes,
            "events_by_type": events_by_type,
            "events_by_severity": events_by_severity_dict,
            "top_file_paths": [{"path": path, "count": count} for path, count in top_file_paths],
            "top_processes": [{"name": name, "count": count} for name, count in top_processes]
        }

    except Exception as e:
        logger.error(f"Error retrieving FIM statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve FIM statistics: {str(e)}"
        )
