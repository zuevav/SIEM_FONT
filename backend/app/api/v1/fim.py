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

from app.api.deps import get_db, get_current_user
from app.schemas.auth import CurrentUser
from app.models.event import Event
from app.config import settings

logger = logging.getLogger(__name__)

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
                Event.SourceType == "Sysmon",
                Event.Provider.ilike("%Sysmon%")
            )
        )

        # Filter by FIM event codes
        query = query.filter(Event.EventCode.in_(list(FIM_EVENT_CODES.keys())))

        # Time filters
        if last_hours:
            start_time = datetime.utcnow() - timedelta(hours=last_hours)

        if start_time:
            query = query.filter(Event.EventTime >= start_time)
        if end_time:
            query = query.filter(Event.EventTime <= end_time)

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
                    query = query.filter(Event.EventCode.in_(codes))
                else:
                    query = query.filter(Event.EventCode == codes)

        # FIM-specific filters
        if file_path:
            query = query.filter(Event.FilePath.ilike(f"%{file_path}%"))

        if registry_key:
            # Registry key is stored in EventData JSONB field
            query = query.filter(
                Event.EventData['RegistryKey'].astext.ilike(f"%{registry_key}%")
            )

        if process_name:
            query = query.filter(Event.ProcessName.ilike(f"%{process_name}%"))

        # General filters
        if agent_id:
            query = query.filter(Event.AgentId == agent_id)

        if hostname:
            query = query.filter(Event.Hostname.ilike(f"%{hostname}%"))

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        events = query.order_by(Event.EventTime.desc()).offset(offset).limit(limit).all()

        # Convert to dict with FIM-specific fields
        fim_events = []
        for event in events:
            event_dict = {
                "event_id": event.EventId,
                "event_time": event.EventTime.isoformat() if event.EventTime else None,
                "event_code": event.EventCode,
                "event_type": FIM_EVENT_CODES.get(event.EventCode, "Unknown"),
                "hostname": event.Hostname,
                "agent_id": event.AgentId,
                "file_path": event.FilePath,
                "process_name": event.ProcessName,
                "target_user": event.TargetUser,
                "message": event.Message,
                "severity": event.Severity,
                "category": event.Category,
                # Extract FIM-specific data from EventData JSONB
                "file_hash": event.EventData.get("FileHash") or event.EventData.get("Hashes"),
                "registry_key": event.EventData.get("RegistryKey"),
                "registry_value": event.EventData.get("RegistryValue"),
                "event_type_detail": event.EventData.get("EventType"),  # CreateKey, SetValue, etc.
                "details": event.EventData.get("Details"),  # Registry value details
                "new_name": event.EventData.get("NewName"),  # For rename operations
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
        Event.EventId == event_id,
        or_(
            Event.SourceType == "Sysmon",
            Event.Provider.ilike("%Sysmon%")
        ),
        Event.EventCode.in_(list(FIM_EVENT_CODES.keys()))
    ).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FIM event with ID {event_id} not found"
        )

    return {
        "event_id": event.EventId,
        "event_time": event.EventTime.isoformat() if event.EventTime else None,
        "event_code": event.EventCode,
        "event_type": FIM_EVENT_CODES.get(event.EventCode, "Unknown"),
        "hostname": event.Hostname,
        "agent_id": event.AgentId,
        "source_type": event.SourceType,
        "provider": event.Provider,
        "severity": event.Severity,
        "category": event.Category,
        "message": event.Message,

        # File details
        "file_path": event.FilePath,
        "file_hash": event.EventData.get("FileHash") or event.EventData.get("Hashes"),

        # Registry details
        "registry_key": event.EventData.get("RegistryKey"),
        "registry_value": event.EventData.get("RegistryValue"),
        "registry_details": event.EventData.get("Details"),
        "event_type_detail": event.EventData.get("EventType"),
        "target_object": event.EventData.get("TargetObject"),
        "new_name": event.EventData.get("NewName"),

        # Process details
        "process_name": event.ProcessName,
        "process_id": event.ProcessID,
        "process_command_line": event.ProcessCommandLine,

        # User details
        "target_user": event.TargetUser,
        "subject_user": event.SubjectUser,

        # Full event data
        "event_data": event.EventData,
        "raw_xml": event.RawData
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
                Event.SourceType == "Sysmon",
                Event.Provider.ilike("%Sysmon%")
            ),
            Event.EventCode.in_(list(FIM_EVENT_CODES.keys())),
            Event.EventTime >= start_time
        )

        # Total FIM events
        total_events = base_query.count()

        # Events by type
        events_by_type = {}
        for event_code, event_name in FIM_EVENT_CODES.items():
            count = base_query.filter(Event.EventCode == event_code).count()
            events_by_type[event_name] = count

        # Top modified paths (files and registry)
        top_file_paths = db.query(
            Event.FilePath,
            func.count(Event.EventId).label('count')
        ).filter(
            Event.EventId.in_(base_query.with_entities(Event.EventId).subquery()),
            Event.FilePath.isnot(None)
        ).group_by(Event.FilePath).order_by(func.count(Event.EventId).desc()).limit(10).all()

        # Top processes making changes
        top_processes = db.query(
            Event.ProcessName,
            func.count(Event.EventId).label('count')
        ).filter(
            Event.EventId.in_(base_query.with_entities(Event.EventId).subquery()),
            Event.ProcessName.isnot(None)
        ).group_by(Event.ProcessName).order_by(func.count(Event.EventId).desc()).limit(10).all()

        # Events by severity
        events_by_severity = db.query(
            Event.Severity,
            func.count(Event.EventId).label('count')
        ).filter(
            Event.EventId.in_(base_query.with_entities(Event.EventId).subquery())
        ).group_by(Event.Severity).all()

        severity_map = {0: 'Info', 1: 'Low', 2: 'Medium', 3: 'High', 4: 'Critical'}
        events_by_severity_dict = {
            severity_map.get(sev, 'Unknown'): count
            for sev, count in events_by_severity
        }

        # Critical file changes (high severity)
        critical_changes = base_query.filter(Event.Severity >= 3).count()

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
