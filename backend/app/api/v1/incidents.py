"""
Incidents API Endpoints
Handles incident management, correlation, and CBR reporting
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from typing import List, Optional
from datetime import datetime, timedelta
import json
import logging

from app.api.deps import get_db, get_current_user, require_analyst, require_admin
from app.schemas.incident import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    IncidentDetail,
    IncidentStatistics,
    IncidentFilter,
    IncidentWorkLogEntry,
    IncidentContainmentAction,
    IncidentRemediationAction,
    IncidentClose,
    IncidentCBRReport,
    IncidentTimeline,
    IncidentTimelineEntry,
    IncidentCorrelation,
    IncidentExport
)
from app.schemas.auth import CurrentUser
from app.models.incident import Incident, Alert
from app.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# INCIDENT MANAGEMENT
# ============================================================================

@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Create a new incident (analyst or admin)
    Can be created from alerts or manually
    """
    try:
        # Validate alerts if provided
        if incident.alert_ids:
            alerts = db.query(Alert).filter(Alert.AlertId.in_(incident.alert_ids)).all()
            if len(alerts) != len(incident.alert_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Some alert IDs do not exist"
                )

            # Get event count from alerts
            event_count = sum(alert.EventCount for alert in alerts)
        else:
            event_count = 0

        # Create new incident
        new_incident = Incident(
            Title=incident.title,
            Description=incident.description,
            Severity=incident.severity,
            Category=incident.category,
            AlertCount=len(incident.alert_ids) if incident.alert_ids else 0,
            EventCount=event_count,
            AffectedAgents=json.dumps(incident.affected_agents) if incident.affected_agents else None,
            AffectedUsers=json.dumps(incident.affected_users) if incident.affected_users else None,
            AffectedAssets=len(incident.affected_agents) if incident.affected_agents else 0,
            StartTime=incident.start_time,
            EndTime=incident.end_time,
            DetectedAt=datetime.utcnow(),
            Status='open',
            AssignedTo=incident.assigned_to or current_user.user_id,
            Priority=incident.priority,
            MitreAttackTactics=json.dumps(incident.mitre_attack_tactics) if incident.mitre_attack_tactics else None,
            MitreAttackTechniques=json.dumps(incident.mitre_attack_techniques) if incident.mitre_attack_techniques else None,
            OperationalRiskCategory=incident.operational_risk_category,
            EstimatedDamage_RUB=incident.estimated_damage_rub,
            CreatedAt=datetime.utcnow(),
            WorkLog=json.dumps([{
                "timestamp": datetime.utcnow().isoformat(),
                "user": current_user.username,
                "entry": f"Incident created by {current_user.username}",
                "type": "milestone"
            }])
        )

        db.add(new_incident)
        db.flush()

        # Link alerts to this incident
        if incident.alert_ids:
            for alert_id in incident.alert_ids:
                alert = db.query(Alert).filter(Alert.AlertId == alert_id).first()
                if alert:
                    alert.IncidentId = new_incident.IncidentId

        db.commit()
        db.refresh(new_incident)

        logger.info(f"Incident '{new_incident.Title}' created by {current_user.username} (ID: {new_incident.IncidentId})")

        return IncidentResponse.from_orm(new_incident)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating incident: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create incident: {str(e)}"
        )


@router.get("", response_model=dict)
async def get_incidents(
    # Time filters
    start_time: Optional[datetime] = Query(None, description="Filter incidents after this time"),
    end_time: Optional[datetime] = Query(None, description="Filter incidents before this time"),
    last_days: Optional[int] = Query(None, description="Get incidents from last N days"),

    # Status filters
    status: Optional[str] = Query(None, description="Filter by status"),
    min_severity: Optional[int] = Query(None, ge=0, le=4, description="Minimum severity"),
    category: Optional[str] = Query(None, description="Filter by category"),

    # Assignment
    assigned_to_me: bool = Query(False, description="Show only incidents assigned to me"),
    assigned_to: Optional[int] = Query(None, description="Filter by assigned user ID"),

    # MITRE
    mitre_tactic: Optional[str] = Query(None, description="Filter by MITRE tactic"),

    # CBR
    is_reported_to_cbr: Optional[bool] = Query(None, description="Filter by CBR reported status"),

    # Pagination
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),

    # Dependencies
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get list of incidents with filtering
    """
    try:
        query = db.query(Incident)

        # Time filters
        if last_days:
            start_time = datetime.utcnow() - timedelta(days=last_days)

        if start_time:
            query = query.filter(Incident.DetectedAt >= start_time)
        if end_time:
            query = query.filter(Incident.DetectedAt <= end_time)

        # Status filters
        if status:
            query = query.filter(Incident.Status == status)
        if min_severity is not None:
            query = query.filter(Incident.Severity >= min_severity)
        if category:
            query = query.filter(Incident.Category == category)

        # Assignment filters
        if assigned_to_me:
            query = query.filter(Incident.AssignedTo == current_user.user_id)
        elif assigned_to is not None:
            query = query.filter(Incident.AssignedTo == assigned_to)

        # MITRE filter
        if mitre_tactic:
            query = query.filter(Incident.MitreAttackTactics.like(f'%{mitre_tactic}%'))

        # CBR filter
        if is_reported_to_cbr is not None:
            query = query.filter(Incident.IsReportedToCBR == is_reported_to_cbr)

        # Get total
        total = query.count()

        # Apply pagination
        incidents = query.order_by(Incident.DetectedAt.desc()).offset(offset).limit(limit).all()

        return {
            "incidents": [IncidentResponse.from_orm(incident) for incident in incidents],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error retrieving incidents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve incidents: {str(e)}"
        )


@router.get("/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get incident details
    """
    incident = db.query(Incident).filter(Incident.IncidentId == incident_id).first()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )

    return IncidentDetail.from_orm(incident)


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: int,
    update_data: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Update incident (analyst or admin)
    """
    try:
        incident = db.query(Incident).filter(Incident.IncidentId == incident_id).first()

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found"
            )

        # Update fields
        status_changed = False
        if update_data.title is not None:
            incident.Title = update_data.title
        if update_data.description is not None:
            incident.Description = update_data.description
        if update_data.severity is not None:
            incident.Severity = update_data.severity
        if update_data.category is not None:
            incident.Category = update_data.category
        if update_data.status is not None:
            if update_data.status != incident.Status:
                status_changed = True
                old_status = incident.Status
                incident.Status = update_data.status

                # Add to work log
                work_log = json.loads(incident.WorkLog) if incident.WorkLog else []
                work_log.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "user": current_user.username,
                    "entry": f"Status changed from {old_status} to {update_data.status}",
                    "type": "milestone"
                })
                incident.WorkLog = json.dumps(work_log)

        if update_data.priority is not None:
            incident.Priority = update_data.priority
        if update_data.assigned_to is not None:
            incident.AssignedTo = update_data.assigned_to
        if update_data.start_time is not None:
            incident.StartTime = update_data.start_time
        if update_data.end_time is not None:
            incident.EndTime = update_data.end_time
        if update_data.operational_risk_category is not None:
            incident.OperationalRiskCategory = update_data.operational_risk_category
        if update_data.estimated_damage_rub is not None:
            incident.EstimatedDamage_RUB = update_data.estimated_damage_rub
        if update_data.actual_damage_rub is not None:
            incident.ActualDamage_RUB = update_data.actual_damage_rub

        incident.UpdatedAt = datetime.utcnow()

        db.commit()
        db.refresh(incident)

        logger.info(f"Incident {incident_id} updated by {current_user.username}")

        return IncidentResponse.from_orm(incident)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating incident: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update incident: {str(e)}"
        )


@router.delete("/{incident_id}")
async def delete_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Delete incident (admin only)
    Note: This will NOT delete related alerts, just unlink them
    """
    try:
        incident = db.query(Incident).filter(Incident.IncidentId == incident_id).first()

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found"
            )

        title = incident.Title

        # Unlink alerts
        db.query(Alert).filter(Alert.IncidentId == incident_id).update({Alert.IncidentId: None})

        # Delete incident
        db.delete(incident)
        db.commit()

        logger.warning(f"Incident '{title}' (ID: {incident_id}) deleted by {current_user.username}")

        return {
            "success": True,
            "message": f"Incident '{title}' deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting incident: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete incident: {str(e)}"
        )


# ============================================================================
# INCIDENT WORK LOG
# ============================================================================

@router.post("/{incident_id}/worklog")
async def add_work_log_entry(
    incident_id: int,
    entry: IncidentWorkLogEntry,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Add work log entry to incident
    """
    try:
        incident = db.query(Incident).filter(Incident.IncidentId == incident_id).first()

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found"
            )

        # Add to work log
        work_log = json.loads(incident.WorkLog) if incident.WorkLog else []
        work_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user": current_user.username,
            "entry": entry.entry,
            "type": entry.entry_type
        })
        incident.WorkLog = json.dumps(work_log)
        incident.UpdatedAt = datetime.utcnow()

        db.commit()

        logger.info(f"Work log entry added to incident {incident_id} by {current_user.username}")

        return {
            "success": True,
            "message": "Work log entry added"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding work log entry: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add work log entry: {str(e)}"
        )


# ============================================================================
# INCIDENT RESPONSE ACTIONS
# ============================================================================

@router.post("/{incident_id}/containment")
async def add_containment_action(
    incident_id: int,
    action: IncidentContainmentAction,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Add containment action to incident (analyst or admin)
    """
    try:
        incident = db.query(Incident).filter(Incident.IncidentId == incident_id).first()

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found"
            )

        # Add to containment actions
        containment = json.loads(incident.ContainmentActions) if incident.ContainmentActions else []
        containment.append({
            "timestamp": (action.timestamp or datetime.utcnow()).isoformat(),
            "performed_by": action.performed_by or current_user.username,
            "action": action.action,
            "result": action.result
        })
        incident.ContainmentActions = json.dumps(containment)

        # Update status if first containment action
        if incident.Status == 'investigating':
            incident.Status = 'contained'

        incident.UpdatedAt = datetime.utcnow()
        db.commit()

        logger.info(f"Containment action added to incident {incident_id} by {current_user.username}")

        return {
            "success": True,
            "message": "Containment action added"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding containment action: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add containment action: {str(e)}"
        )


@router.post("/{incident_id}/remediation")
async def add_remediation_action(
    incident_id: int,
    action: IncidentRemediationAction,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Add remediation action to incident (analyst or admin)
    """
    try:
        incident = db.query(Incident).filter(Incident.IncidentId == incident_id).first()

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found"
            )

        # Add to remediation actions
        remediation = json.loads(incident.RemediationActions) if incident.RemediationActions else []
        remediation.append({
            "timestamp": (action.timestamp or datetime.utcnow()).isoformat(),
            "performed_by": action.performed_by or current_user.username,
            "action": action.action,
            "result": action.result,
            "verified": action.verified
        })
        incident.RemediationActions = json.dumps(remediation)
        incident.UpdatedAt = datetime.utcnow()

        db.commit()

        logger.info(f"Remediation action added to incident {incident_id} by {current_user.username}")

        return {
            "success": True,
            "message": "Remediation action added"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding remediation action: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add remediation action: {str(e)}"
        )


@router.post("/{incident_id}/close", response_model=IncidentResponse)
async def close_incident(
    incident_id: int,
    close_data: IncidentClose,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Close incident (analyst or admin)
    """
    try:
        incident = db.query(Incident).filter(Incident.IncidentId == incident_id).first()

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found"
            )

        if incident.Status == 'closed':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incident is already closed"
            )

        # Update incident
        incident.Status = 'closed'
        incident.ClosedAt = datetime.utcnow()
        incident.LessonsLearned = close_data.lessons_learned

        if close_data.actual_damage_rub is not None:
            incident.ActualDamage_RUB = close_data.actual_damage_rub

        # Add to work log
        work_log = json.loads(incident.WorkLog) if incident.WorkLog else []
        work_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user": current_user.username,
            "entry": f"Incident closed by {current_user.username}. {close_data.final_notes or ''}",
            "type": "milestone"
        })
        incident.WorkLog = json.dumps(work_log)

        incident.UpdatedAt = datetime.utcnow()

        db.commit()
        db.refresh(incident)

        logger.info(f"Incident {incident_id} closed by {current_user.username}")

        return IncidentResponse.from_orm(incident)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error closing incident: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close incident: {str(e)}"
        )


# ============================================================================
# CBR REPORTING
# ============================================================================

@router.post("/{incident_id}/cbr-report")
async def report_to_cbr(
    incident_id: int,
    report: IncidentCBRReport,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Mark incident as reported to CBR (analyst or admin)
    """
    try:
        incident = db.query(Incident).filter(Incident.IncidentId == incident_id).first()

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found"
            )

        # Update CBR reporting fields
        incident.IsReportedToCBR = True
        incident.CBRReportDate = datetime.utcnow()
        incident.CBRIncidentNumber = report.cbr_incident_number
        incident.OperationalRiskCategory = report.operational_risk_category

        if report.actual_damage_rub is not None:
            incident.ActualDamage_RUB = report.actual_damage_rub

        # Add to work log
        work_log = json.loads(incident.WorkLog) if incident.WorkLog else []
        work_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user": current_user.username,
            "entry": f"Reported to CBR. Incident number: {report.cbr_incident_number}. {report.report_notes or ''}",
            "type": "milestone"
        })
        incident.WorkLog = json.dumps(work_log)

        incident.UpdatedAt = datetime.utcnow()

        db.commit()

        logger.info(f"Incident {incident_id} reported to CBR by {current_user.username}")

        return {
            "success": True,
            "message": f"Incident reported to CBR with number {report.cbr_incident_number}"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error reporting to CBR: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to report to CBR: {str(e)}"
        )


# ============================================================================
# INCIDENT STATISTICS
# ============================================================================

@router.get("/stats/overview", response_model=IncidentStatistics)
async def get_incident_statistics(
    days: int = Query(30, ge=1, le=365, description="Time window in days"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get incident statistics for dashboard
    """
    try:
        start_time = datetime.utcnow() - timedelta(days=days)

        # Total incidents
        total_incidents = db.query(func.count(Incident.IncidentId)).filter(
            Incident.DetectedAt >= start_time
        ).scalar()

        # Incidents by status
        open_incidents = db.query(func.count(Incident.IncidentId)).filter(
            and_(Incident.DetectedAt >= start_time, Incident.Status == 'open')
        ).scalar()

        investigating_incidents = db.query(func.count(Incident.IncidentId)).filter(
            and_(Incident.DetectedAt >= start_time, Incident.Status == 'investigating')
        ).scalar()

        contained_incidents = db.query(func.count(Incident.IncidentId)).filter(
            and_(Incident.DetectedAt >= start_time, Incident.Status == 'contained')
        ).scalar()

        resolved_incidents = db.query(func.count(Incident.IncidentId)).filter(
            and_(Incident.DetectedAt >= start_time, Incident.Status == 'resolved')
        ).scalar()

        closed_incidents = db.query(func.count(Incident.IncidentId)).filter(
            and_(Incident.DetectedAt >= start_time, Incident.Status == 'closed')
        ).scalar()

        critical_incidents = db.query(func.count(Incident.IncidentId)).filter(
            and_(Incident.DetectedAt >= start_time, Incident.Severity >= 4)
        ).scalar()

        # Incidents by severity
        incidents_by_severity = {}
        severity_stats = db.query(
            Incident.Severity,
            func.count(Incident.IncidentId).label('count')
        ).filter(Incident.DetectedAt >= start_time).group_by(Incident.Severity).all()

        for severity, count in severity_stats:
            severity_name = ['Info', 'Low', 'Medium', 'High', 'Critical'][severity]
            incidents_by_severity[severity_name] = count

        # Incidents by category
        incidents_by_category = {}
        category_stats = db.query(
            Incident.Category,
            func.count(Incident.IncidentId).label('count')
        ).filter(Incident.DetectedAt >= start_time).group_by(Incident.Category).all()

        for category, count in category_stats:
            incidents_by_category[category or 'Unknown'] = count

        # Incidents by status (for chart)
        incidents_by_status = {
            'open': open_incidents or 0,
            'investigating': investigating_incidents or 0,
            'contained': contained_incidents or 0,
            'resolved': resolved_incidents or 0,
            'closed': closed_incidents or 0
        }

        # Average resolution time
        resolved_with_times = db.query(Incident).filter(
            and_(
                Incident.DetectedAt >= start_time,
                Incident.Status.in_(['resolved', 'closed']),
                Incident.ClosedAt.isnot(None)
            )
        ).all()

        if resolved_with_times:
            total_hours = sum([
                (inc.ClosedAt - inc.DetectedAt).total_seconds() / 3600
                for inc in resolved_with_times
            ])
            avg_resolution_time_hours = total_hours / len(resolved_with_times)
        else:
            avg_resolution_time_hours = None

        # This month vs last month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)

        incidents_this_month = db.query(func.count(Incident.IncidentId)).filter(
            Incident.DetectedAt >= month_start
        ).scalar()

        incidents_last_month = db.query(func.count(Incident.IncidentId)).filter(
            and_(
                Incident.DetectedAt >= last_month_start,
                Incident.DetectedAt < month_start
            )
        ).scalar()

        return IncidentStatistics(
            total_incidents=total_incidents or 0,
            open_incidents=open_incidents or 0,
            investigating_incidents=investigating_incidents or 0,
            contained_incidents=contained_incidents or 0,
            resolved_incidents=resolved_incidents or 0,
            closed_incidents=closed_incidents or 0,
            critical_incidents=critical_incidents or 0,
            incidents_by_severity=incidents_by_severity,
            incidents_by_category=incidents_by_category,
            incidents_by_status=incidents_by_status,
            avg_resolution_time_hours=avg_resolution_time_hours,
            incidents_this_month=incidents_this_month or 0,
            incidents_last_month=incidents_last_month or 0
        )

    except Exception as e:
        logger.error(f"Error getting incident statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get incident statistics: {str(e)}"
        )


# ============================================================================
# INCIDENT TIMELINE
# ============================================================================

@router.get("/{incident_id}/timeline", response_model=IncidentTimeline)
async def get_incident_timeline(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get incident timeline with all events, alerts, and actions
    """
    try:
        incident = db.query(Incident).filter(Incident.IncidentId == incident_id).first()

        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found"
            )

        timeline = []

        # Add incident creation
        timeline.append(IncidentTimelineEntry(
            timestamp=incident.DetectedAt,
            event_type="status_change",
            title="Incident created",
            description=f"Incident '{incident.Title}' created",
            severity=incident.Severity
        ))

        # Add related alerts
        alerts = db.query(Alert).filter(Alert.IncidentId == incident_id).all()
        for alert in alerts:
            timeline.append(IncidentTimelineEntry(
                timestamp=alert.CreatedAt,
                event_type="alert",
                title=alert.Title,
                description=alert.Description,
                severity=alert.Severity,
                related_alert_id=alert.AlertId
            ))

        # Add containment actions
        if incident.ContainmentActions:
            containment = json.loads(incident.ContainmentActions)
            for action in containment:
                timeline.append(IncidentTimelineEntry(
                    timestamp=datetime.fromisoformat(action['timestamp']),
                    event_type="containment",
                    title="Containment action",
                    description=action['action']
                ))

        # Add remediation actions
        if incident.RemediationActions:
            remediation = json.loads(incident.RemediationActions)
            for action in remediation:
                timeline.append(IncidentTimelineEntry(
                    timestamp=datetime.fromisoformat(action['timestamp']),
                    event_type="remediation",
                    title="Remediation action",
                    description=action['action']
                ))

        # Sort timeline by timestamp
        timeline.sort(key=lambda x: x.timestamp)

        return IncidentTimeline(
            incident_id=incident_id,
            timeline=timeline,
            start_time=incident.StartTime or incident.DetectedAt,
            end_time=incident.EndTime or (incident.ClosedAt if incident.Status == 'closed' else None)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting incident timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get incident timeline: {str(e)}"
        )


# ============================================================================
# INCIDENT ALERTS
# ============================================================================

@router.get("/{incident_id}/alerts")
async def get_incident_alerts(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get all alerts related to this incident
    """
    incident = db.query(Incident).filter(Incident.IncidentId == incident_id).first()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )

    alerts = db.query(Alert).filter(Alert.IncidentId == incident_id).all()

    from app.schemas.alert import AlertResponse
    return {
        "incident_id": incident_id,
        "alerts": [AlertResponse.from_orm(alert) for alert in alerts],
        "count": len(alerts)
    }
