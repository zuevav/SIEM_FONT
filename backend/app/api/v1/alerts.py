"""
Alerts API Endpoints
Handles alerts, detection rules, and alert management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from typing import List, Optional
from datetime import datetime, timedelta
import json
import logging

from app.api.deps import get_db, get_current_user, require_analyst, require_admin
from app.schemas.alert import (
    DetectionRuleCreate,
    DetectionRuleUpdate,
    DetectionRuleResponse,
    DetectionRuleDetail,
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertDetail,
    AlertStatistics,
    AlertFilter,
    AlertAcknowledge,
    AlertResolve,
    AlertEscalate,
    AlertAssign,
    AlertComment
)
from app.schemas.auth import CurrentUser
from app.models.incident import DetectionRule, Alert, Incident
from app.models.event import Event
from app.models.user import User
from app.config import settings
from app.services.incident_correlation import get_correlation_service
from app.services.alert_handler import handle_new_alert

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# DETECTION RULES MANAGEMENT
# ============================================================================

@router.post("/rules", response_model=DetectionRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_detection_rule(
    rule: DetectionRuleCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Create a new detection rule (analyst or admin)
    """
    try:
        # Check if rule name already exists
        existing = db.query(DetectionRule).filter(DetectionRule.RuleName == rule.rule_name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Detection rule with name '{rule.rule_name}' already exists"
            )

        # Create new rule
        new_rule = DetectionRule(
            RuleName=rule.rule_name,
            Description=rule.description,
            IsEnabled=rule.is_enabled,
            Severity=rule.severity,
            Priority=rule.priority,
            RuleType=rule.rule_type,
            RuleLogic=rule.rule_logic,
            TimeWindowMinutes=rule.time_window_minutes,
            ThresholdCount=rule.threshold_count,
            GroupByFields=json.dumps(rule.group_by_fields) if rule.group_by_fields else None,
            SourceTypes=json.dumps(rule.source_types) if rule.source_types else None,
            EventCodes=json.dumps(rule.event_codes) if rule.event_codes else None,
            Categories=json.dumps(rule.categories) if rule.categories else None,
            Actions=json.dumps(rule.actions) if rule.actions else None,
            AutoEscalate=rule.auto_escalate,
            MitreAttackTactic=rule.mitre_attack_tactic,
            MitreAttackTechnique=rule.mitre_attack_technique,
            MitreAttackSubtechnique=rule.mitre_attack_subtechnique,
            Exceptions=json.dumps(rule.exceptions) if rule.exceptions else None,
            CreatedBy=current_user.user_id,
            CreatedAt=datetime.utcnow(),
            Tags=json.dumps(rule.tags) if rule.tags else None
        )

        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)

        logger.info(f"Detection rule '{new_rule.RuleName}' created by {current_user.username}")

        return DetectionRuleResponse.from_orm(new_rule)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating detection rule: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create detection rule: {str(e)}"
        )


@router.get("/rules", response_model=dict)
async def get_detection_rules(
    enabled_only: bool = Query(False, description="Show only enabled rules"),
    rule_type: Optional[str] = Query(None, description="Filter by rule type"),
    search: Optional[str] = Query(None, description="Search in rule name and description"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get list of detection rules
    """
    try:
        query = db.query(DetectionRule)

        if enabled_only:
            query = query.filter(DetectionRule.IsEnabled == True)

        if rule_type:
            query = query.filter(DetectionRule.RuleType == rule_type)

        if search:
            query = query.filter(
                or_(
                    DetectionRule.RuleName.ilike(f"%{search}%"),
                    DetectionRule.Description.ilike(f"%{search}%")
                )
            )

        total = query.count()
        rules = query.order_by(DetectionRule.Priority.desc()).offset(offset).limit(limit).all()

        return {
            "rules": [DetectionRuleResponse.from_orm(rule) for rule in rules],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error retrieving detection rules: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve detection rules: {str(e)}"
        )


@router.get("/rules/{rule_id}", response_model=DetectionRuleDetail)
async def get_detection_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get detection rule details
    """
    rule = db.query(DetectionRule).filter(DetectionRule.RuleId == rule_id).first()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection rule {rule_id} not found"
        )

    return DetectionRuleDetail.from_orm(rule)


@router.patch("/rules/{rule_id}", response_model=DetectionRuleResponse)
async def update_detection_rule(
    rule_id: int,
    update_data: DetectionRuleUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Update detection rule (analyst or admin)
    """
    try:
        rule = db.query(DetectionRule).filter(DetectionRule.RuleId == rule_id).first()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection rule {rule_id} not found"
            )

        # Update fields
        if update_data.rule_name is not None:
            rule.RuleName = update_data.rule_name
        if update_data.description is not None:
            rule.Description = update_data.description
        if update_data.is_enabled is not None:
            rule.IsEnabled = update_data.is_enabled
        if update_data.severity is not None:
            rule.Severity = update_data.severity
        if update_data.priority is not None:
            rule.Priority = update_data.priority
        if update_data.rule_logic is not None:
            rule.RuleLogic = update_data.rule_logic
        if update_data.time_window_minutes is not None:
            rule.TimeWindowMinutes = update_data.time_window_minutes
        if update_data.threshold_count is not None:
            rule.ThresholdCount = update_data.threshold_count
        if update_data.auto_escalate is not None:
            rule.AutoEscalate = update_data.auto_escalate
        if update_data.tags is not None:
            rule.Tags = json.dumps(update_data.tags)

        rule.UpdatedBy = current_user.user_id
        rule.UpdatedAt = datetime.utcnow()

        db.commit()
        db.refresh(rule)

        logger.info(f"Detection rule '{rule.RuleName}' updated by {current_user.username}")

        return DetectionRuleResponse.from_orm(rule)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating detection rule: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update detection rule: {str(e)}"
        )


@router.delete("/rules/{rule_id}")
async def delete_detection_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Delete detection rule (admin only)
    """
    try:
        rule = db.query(DetectionRule).filter(DetectionRule.RuleId == rule_id).first()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection rule {rule_id} not found"
            )

        rule_name = rule.RuleName

        db.delete(rule)
        db.commit()

        logger.warning(f"Detection rule '{rule_name}' deleted by {current_user.username}")

        return {
            "success": True,
            "message": f"Detection rule '{rule_name}' deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting detection rule: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete detection rule: {str(e)}"
        )


# ============================================================================
# ALERTS MANAGEMENT
# ============================================================================

@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert: AlertCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Create a new alert (usually from detection engine or manual)
    """
    try:
        # Validate event IDs exist
        if alert.event_ids:
            event_count = db.query(Event).filter(Event.event_id.in_(alert.event_ids)).count()
            if event_count != len(alert.event_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Some event IDs do not exist"
                )

        # Create new alert
        new_alert = Alert(
            RuleId=alert.rule_id,
            Severity=alert.severity,
            Title=alert.title,
            Description=alert.description,
            Category=alert.category,
            EventIds=json.dumps(alert.event_ids) if alert.event_ids else None,
            EventCount=len(alert.event_ids) if alert.event_ids else 0,
            FirstEventTime=alert.first_event_time,
            LastEventTime=alert.last_event_time,
            AgentId=str(alert.agent_id) if alert.agent_id else None,
            Hostname=alert.hostname,
            Username=alert.username,
            SourceIP=alert.source_ip,
            TargetIP=alert.target_ip,
            ProcessName=alert.process_name,
            MitreAttackTactic=alert.mitre_attack_tactic,
            MitreAttackTechnique=alert.mitre_attack_technique,
            MitreAttackSubtechnique=alert.mitre_attack_subtechnique,
            Status='new',
            Priority=alert.severity,  # Default priority equals severity
            AIAnalysis=json.dumps(alert.ai_analysis) if alert.ai_analysis else None,
            AIRecommendations=alert.ai_recommendations,
            AIConfidence=alert.ai_confidence,
            CreatedAt=datetime.utcnow()
        )

        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)

        logger.info(f"Alert '{new_alert.Title}' created (ID: {new_alert.AlertId})")

        # Auto-correlate alert with existing alerts and potentially create incident
        try:
            correlation_service = get_correlation_service(db)
            incident = await correlation_service.correlate_new_alert(new_alert)
            if incident:
                logger.info(f"Alert {new_alert.AlertId} correlated to incident {incident.IncidentId}")
                db.refresh(new_alert)  # Refresh to get updated IncidentId
        except Exception as e:
            logger.error(f"Error in alert correlation: {e}", exc_info=True)
            # Don't fail the alert creation if correlation fails

        # Handle new alert: send email, create FreeScout ticket, etc.
        try:
            siem_url = settings.siem_url if hasattr(settings, 'siem_url') else "http://localhost:3000"
            await handle_new_alert(new_alert, db, siem_url)
        except Exception as e:
            logger.error(f"Error handling new alert {new_alert.AlertId}: {e}", exc_info=True)
            # Don't fail the alert creation if notification fails

        return AlertResponse.from_orm(new_alert)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating alert: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert: {str(e)}"
        )


@router.get("", response_model=dict)
async def get_alerts(
    # Time filters
    start_time: Optional[datetime] = Query(None, description="Filter alerts after this time"),
    end_time: Optional[datetime] = Query(None, description="Filter alerts before this time"),
    last_hours: Optional[int] = Query(None, description="Get alerts from last N hours"),

    # Status filters
    alert_status: Optional[str] = Query(None, description="Filter by status"),
    min_severity: Optional[int] = Query(None, ge=0, le=4, description="Minimum severity"),
    category: Optional[str] = Query(None, description="Filter by category"),

    # Assignment
    assigned_to_me: bool = Query(False, description="Show only alerts assigned to me"),
    assigned_to: Optional[int] = Query(None, description="Filter by assigned user ID"),
    unassigned: bool = Query(False, description="Show only unassigned alerts"),

    # Related
    rule_id: Optional[int] = Query(None, description="Filter by detection rule"),
    incident_id: Optional[int] = Query(None, description="Filter by incident"),

    # Context
    hostname: Optional[str] = Query(None, description="Filter by hostname"),
    username: Optional[str] = Query(None, description="Filter by username"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),

    # MITRE
    mitre_tactic: Optional[str] = Query(None, description="Filter by MITRE tactic"),

    # CBR
    is_reportable: Optional[bool] = Query(None, description="Filter by CBR reportable status"),

    # Pagination
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),

    # Dependencies
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get list of alerts with filtering
    """
    try:
        query = db.query(Alert)

        # Time filters
        if last_hours:
            start_time = datetime.utcnow() - timedelta(hours=last_hours)

        if start_time:
            query = query.filter(Alert.CreatedAt >= start_time)
        if end_time:
            query = query.filter(Alert.CreatedAt <= end_time)

        # Status filters
        if alert_status:
            query = query.filter(Alert.Status == alert_status)
        if min_severity is not None:
            query = query.filter(Alert.Severity >= min_severity)
        if category:
            query = query.filter(Alert.Category == category)

        # Assignment filters
        if assigned_to_me:
            query = query.filter(Alert.AssignedTo == current_user.user_id)
        elif assigned_to is not None:
            query = query.filter(Alert.AssignedTo == assigned_to)
        elif unassigned:
            query = query.filter(Alert.AssignedTo.is_(None))

        # Related filters
        if rule_id is not None:
            query = query.filter(Alert.RuleId == rule_id)
        if incident_id is not None:
            query = query.filter(Alert.IncidentId == incident_id)

        # Context filters
        if hostname:
            query = query.filter(Alert.Hostname.ilike(f"%{hostname}%"))
        if username:
            query = query.filter(Alert.Username.ilike(f"%{username}%"))
        if source_ip:
            query = query.filter(Alert.SourceIP == source_ip)

        # MITRE filter
        if mitre_tactic:
            query = query.filter(Alert.MitreAttackTactic == mitre_tactic)

        # CBR filter
        if is_reportable is not None:
            query = query.filter(Alert.IsReportable == is_reportable)

        # Get total
        total = query.count()

        # Apply pagination
        alerts = query.order_by(Alert.CreatedAt.desc()).offset(offset).limit(limit).all()

        return {
            "alerts": [AlertResponse.from_orm(alert) for alert in alerts],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error retrieving alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alerts: {str(e)}"
        )


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get alert details
    """
    alert = db.query(Alert).filter(Alert.AlertId == alert_id).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )

    return AlertDetail.from_orm(alert)


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    update_data: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Update alert (analyst or admin)
    """
    try:
        alert = db.query(Alert).filter(Alert.AlertId == alert_id).first()

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )

        # Update fields
        if update_data.status is not None:
            old_status = alert.Status
            alert.Status = update_data.status
            alert.UpdatedAt = datetime.utcnow()

            # Track status changes
            if update_data.status == 'acknowledged' and old_status == 'new':
                alert.AcknowledgedAt = datetime.utcnow()
            elif update_data.status in ('resolved', 'false_positive'):
                alert.ResolvedAt = datetime.utcnow()

        if update_data.assigned_to is not None:
            alert.AssignedTo = update_data.assigned_to

        if update_data.priority is not None:
            alert.Priority = update_data.priority

        if update_data.incident_id is not None:
            alert.IncidentId = update_data.incident_id

        if update_data.operational_risk_category is not None:
            alert.OperationalRiskCategory = update_data.operational_risk_category

        if update_data.estimated_damage_rub is not None:
            alert.EstimatedDamage_RUB = update_data.estimated_damage_rub

        if update_data.is_reportable is not None:
            alert.IsReportable = update_data.is_reportable

        # Add comment or action to history
        if update_data.comment or update_data.action_taken:
            comments = json.loads(alert.Comments) if alert.Comments else []
            actions = json.loads(alert.ActionsTaken) if alert.ActionsTaken else []

            if update_data.comment:
                comments.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "user": current_user.username,
                    "comment": update_data.comment
                })
                alert.Comments = json.dumps(comments)

            if update_data.action_taken:
                actions.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "user": current_user.username,
                    "action": update_data.action_taken
                })
                alert.ActionsTaken = json.dumps(actions)

        db.commit()
        db.refresh(alert)

        logger.info(f"Alert {alert_id} updated by {current_user.username}")

        return AlertResponse.from_orm(alert)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating alert: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert: {str(e)}"
        )


# ============================================================================
# ALERT ACTIONS
# ============================================================================

@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: int,
    ack: AlertAcknowledge,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Acknowledge an alert
    """
    update = AlertUpdate(
        status="acknowledged",
        comment=ack.comment or f"Alert acknowledged by {current_user.username}"
    )
    return await update_alert(alert_id, update, db, current_user)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: int,
    resolve: AlertResolve,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Resolve or mark alert as false positive (analyst or admin)
    """
    update = AlertUpdate(
        status=resolve.resolution,
        comment=resolve.comment,
        action_taken=resolve.lessons_learned
    )
    return await update_alert(alert_id, update, db, current_user)


@router.post("/{alert_id}/assign", response_model=AlertResponse)
async def assign_alert(
    alert_id: int,
    assign: AlertAssign,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst)
):
    """
    Assign alert to user (analyst or admin)
    """
    # Verify user exists
    user = db.query(User).filter(User.user_id == assign.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {assign.user_id} not found"
        )

    update = AlertUpdate(
        assigned_to=assign.user_id,
        comment=assign.comment or f"Alert assigned to {user.username} by {current_user.username}"
    )
    return await update_alert(alert_id, update, db, current_user)


@router.post("/{alert_id}/comment", response_model=AlertResponse)
async def add_alert_comment(
    alert_id: int,
    comment_data: AlertComment,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Add comment to alert
    """
    update = AlertUpdate(
        comment=comment_data.comment,
        action_taken=comment_data.action_taken
    )
    return await update_alert(alert_id, update, db, current_user)


# ============================================================================
# ALERT STATISTICS
# ============================================================================

@router.get("/stats/overview", response_model=AlertStatistics)
async def get_alert_statistics(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get alert statistics for dashboard
    """
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours)

        # Total alerts
        total_alerts = db.query(func.count(Alert.AlertId)).filter(
            Alert.CreatedAt >= start_time
        ).scalar()

        # Alerts by status
        new_alerts = db.query(func.count(Alert.AlertId)).filter(
            and_(Alert.CreatedAt >= start_time, Alert.Status == 'new')
        ).scalar()

        acknowledged_alerts = db.query(func.count(Alert.AlertId)).filter(
            and_(Alert.CreatedAt >= start_time, Alert.Status == 'acknowledged')
        ).scalar()

        investigating_alerts = db.query(func.count(Alert.AlertId)).filter(
            and_(Alert.CreatedAt >= start_time, Alert.Status == 'investigating')
        ).scalar()

        resolved_alerts = db.query(func.count(Alert.AlertId)).filter(
            and_(Alert.CreatedAt >= start_time, Alert.Status == 'resolved')
        ).scalar()

        false_positives = db.query(func.count(Alert.AlertId)).filter(
            and_(Alert.CreatedAt >= start_time, Alert.Status == 'false_positive')
        ).scalar()

        # Alerts by severity
        alerts_by_severity = {}
        severity_stats = db.query(
            Alert.Severity,
            func.count(Alert.AlertId).label('count')
        ).filter(Alert.CreatedAt >= start_time).group_by(Alert.Severity).all()

        for severity, count in severity_stats:
            severity_name = ['Info', 'Low', 'Medium', 'High', 'Critical'][severity]
            alerts_by_severity[severity_name] = count

        # Alerts by category
        alerts_by_category = {}
        category_stats = db.query(
            Alert.Category,
            func.count(Alert.AlertId).label('count')
        ).filter(Alert.CreatedAt >= start_time).group_by(Alert.Category).all()

        for category, count in category_stats:
            alerts_by_category[category or 'Unknown'] = count

        # Alerts by status (for chart)
        alerts_by_status = {
            'new': new_alerts or 0,
            'acknowledged': acknowledged_alerts or 0,
            'investigating': investigating_alerts or 0,
            'resolved': resolved_alerts or 0,
            'false_positive': false_positives or 0
        }

        # Top rules
        top_rules = []
        rule_stats = db.query(
            DetectionRule.RuleId,
            DetectionRule.RuleName,
            func.count(Alert.AlertId).label('count')
        ).join(Alert, Alert.RuleId == DetectionRule.RuleId).filter(
            Alert.CreatedAt >= start_time
        ).group_by(DetectionRule.RuleId, DetectionRule.RuleName).order_by(
            func.count(Alert.AlertId).desc()
        ).limit(10).all()

        for rule_id, rule_name, count in rule_stats:
            top_rules.append({
                'rule_id': rule_id,
                'rule_name': rule_name,
                'alert_count': count
            })

        # Recent alerts (last 10)
        recent_alerts = db.query(Alert).filter(
            Alert.CreatedAt >= start_time
        ).order_by(Alert.CreatedAt.desc()).limit(10).all()

        return AlertStatistics(
            total_alerts=total_alerts or 0,
            new_alerts=new_alerts or 0,
            acknowledged_alerts=acknowledged_alerts or 0,
            investigating_alerts=investigating_alerts or 0,
            resolved_alerts=resolved_alerts or 0,
            false_positives=false_positives or 0,
            alerts_by_severity=alerts_by_severity,
            alerts_by_category=alerts_by_category,
            alerts_by_status=alerts_by_status,
            top_rules=top_rules,
            recent_alerts=[AlertResponse.from_orm(alert) for alert in recent_alerts]
        )

    except Exception as e:
        logger.error(f"Error getting alert statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert statistics: {str(e)}"
        )
