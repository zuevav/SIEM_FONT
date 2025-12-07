"""
SOAR Playbooks API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.playbook import (
    Playbook, PlaybookAction, PlaybookExecution, ActionResult,
    PlaybookStatus
)
from app.schemas.playbook import (
    PlaybookCreate, PlaybookUpdate, PlaybookResponse, PlaybookListResponse,
    PlaybookActionCreate, PlaybookActionUpdate, PlaybookActionResponse, PlaybookActionListResponse,
    PlaybookExecutionCreate, PlaybookExecutionResponse, PlaybookExecutionListResponse,
    PlaybookExecutionApprove, ActionResultResponse, PlaybookStats
)
from app.services.playbook_executor import PlaybookExecutor
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Playbooks CRUD
# ============================================================================

@router.get("/playbooks", response_model=PlaybookListResponse)
async def list_playbooks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all playbooks with pagination
    """
    try:
        query = db.query(Playbook)

        if enabled_only:
            query = query.filter(Playbook.is_enabled == True)

        total = query.count()

        playbooks = query.order_by(desc(Playbook.created_at)).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": playbooks,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        logger.error(f"Error listing playbooks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list playbooks"
        )


@router.get("/playbooks/{playbook_id}", response_model=PlaybookResponse)
async def get_playbook(
    playbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get playbook by ID
    """
    playbook = db.query(Playbook).filter(Playbook.playbook_id == playbook_id).first()

    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )

    return playbook


@router.post("/playbooks", response_model=PlaybookResponse, status_code=status.HTTP_201_CREATED)
async def create_playbook(
    data: PlaybookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new playbook
    """
    try:
        playbook = Playbook(
            name=data.name,
            description=data.description,
            trigger_on_severity=data.trigger_on_severity,
            trigger_on_mitre_tactic=data.trigger_on_mitre_tactic,
            action_ids=data.action_ids or [],
            requires_approval=data.requires_approval,
            is_enabled=data.is_enabled,
            created_at=datetime.utcnow()
        )

        db.add(playbook)
        db.commit()
        db.refresh(playbook)

        logger.info(f"Playbook {playbook.playbook_id} created by user {current_user.user_id}")

        return playbook

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating playbook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create playbook"
        )


@router.put("/playbooks/{playbook_id}", response_model=PlaybookResponse)
async def update_playbook(
    playbook_id: int,
    data: PlaybookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update playbook
    """
    playbook = db.query(Playbook).filter(Playbook.playbook_id == playbook_id).first()

    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )

    try:
        update_data = data.dict(exclude_unset=True)

        for field, value in update_data.items():
            setattr(playbook, field, value)

        playbook.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(playbook)

        logger.info(f"Playbook {playbook_id} updated by user {current_user.user_id}")

        return playbook

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating playbook {playbook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update playbook"
        )


@router.delete("/playbooks/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playbook(
    playbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete playbook
    """
    playbook = db.query(Playbook).filter(Playbook.playbook_id == playbook_id).first()

    if not playbook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found"
        )

    try:
        db.delete(playbook)
        db.commit()

        logger.info(f"Playbook {playbook_id} deleted by user {current_user.user_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting playbook {playbook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete playbook"
        )


# ============================================================================
# Playbook Actions CRUD
# ============================================================================

@router.get("/actions", response_model=PlaybookActionListResponse)
async def list_actions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all playbook actions with pagination
    """
    try:
        query = db.query(PlaybookAction)
        total = query.count()

        actions = query.order_by(desc(PlaybookAction.created_at)).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": actions,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        logger.error(f"Error listing actions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list actions"
        )


@router.get("/actions/{action_id}", response_model=PlaybookActionResponse)
async def get_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get action by ID
    """
    action = db.query(PlaybookAction).filter(PlaybookAction.action_id == action_id).first()

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action {action_id} not found"
        )

    return action


@router.post("/actions", response_model=PlaybookActionResponse, status_code=status.HTTP_201_CREATED)
async def create_action(
    data: PlaybookActionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new playbook action
    """
    try:
        action = PlaybookAction(
            name=data.name,
            action_type=data.action_type,
            config=data.config,
            timeout_seconds=data.timeout_seconds,
            retry_count=data.retry_count,
            created_at=datetime.utcnow()
        )

        db.add(action)
        db.commit()
        db.refresh(action)

        logger.info(f"Action {action.action_id} created by user {current_user.user_id}")

        return action

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating action: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create action"
        )


@router.put("/actions/{action_id}", response_model=PlaybookActionResponse)
async def update_action(
    action_id: int,
    data: PlaybookActionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update playbook action
    """
    action = db.query(PlaybookAction).filter(PlaybookAction.action_id == action_id).first()

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action {action_id} not found"
        )

    try:
        update_data = data.dict(exclude_unset=True)

        for field, value in update_data.items():
            setattr(action, field, value)

        action.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(action)

        logger.info(f"Action {action_id} updated by user {current_user.user_id}")

        return action

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating action {action_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update action"
        )


@router.delete("/actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete playbook action
    """
    action = db.query(PlaybookAction).filter(PlaybookAction.action_id == action_id).first()

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action {action_id} not found"
        )

    try:
        db.delete(action)
        db.commit()

        logger.info(f"Action {action_id} deleted by user {current_user.user_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting action {action_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete action"
        )


# ============================================================================
# Playbook Executions
# ============================================================================

@router.get("/executions", response_model=PlaybookExecutionListResponse)
async def list_executions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    playbook_id: Optional[int] = Query(None),
    status: Optional[PlaybookStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List playbook executions with filtering
    """
    try:
        query = db.query(PlaybookExecution)

        if playbook_id:
            query = query.filter(PlaybookExecution.playbook_id == playbook_id)

        if status:
            query = query.filter(PlaybookExecution.status == status)

        total = query.count()

        executions = query.order_by(desc(PlaybookExecution.started_at)).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": executions,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        logger.error(f"Error listing executions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list executions"
        )


@router.get("/executions/{execution_id}", response_model=PlaybookExecutionResponse)
async def get_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get execution by ID
    """
    execution = db.query(PlaybookExecution).filter(PlaybookExecution.execution_id == execution_id).first()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found"
        )

    return execution


@router.post("/executions", response_model=PlaybookExecutionResponse, status_code=status.HTTP_201_CREATED)
async def execute_playbook(
    data: PlaybookExecutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute a playbook manually
    """
    try:
        executor = PlaybookExecutor(db)
        execution_id = await executor.execute_playbook(
            playbook_id=data.playbook_id,
            alert_id=data.alert_id,
            incident_id=data.incident_id
        )

        if not execution_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to execute playbook"
            )

        execution = db.query(PlaybookExecution).filter(
            PlaybookExecution.execution_id == execution_id
        ).first()

        return execution

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing playbook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute playbook"
        )


@router.post("/executions/{execution_id}/approve")
async def approve_execution(
    execution_id: int,
    data: PlaybookExecutionApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve or reject a pending playbook execution
    """
    try:
        if data.approved:
            executor = PlaybookExecutor(db)
            success = await executor.approve_execution(execution_id, current_user.user_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to approve execution"
                )

            return {"message": "Execution approved and started", "execution_id": execution_id}
        else:
            executor = PlaybookExecutor(db)
            success = await executor.cancel_execution(execution_id, current_user.user_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to reject execution"
                )

            return {"message": "Execution rejected", "execution_id": execution_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving execution {execution_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process approval"
        )


@router.delete("/executions/{execution_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a running or pending playbook execution
    """
    try:
        executor = PlaybookExecutor(db)
        success = await executor.cancel_execution(execution_id, current_user.user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel execution"
            )

        return {"message": "Execution cancelled", "execution_id": execution_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution {execution_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel execution"
        )


# ============================================================================
# Statistics
# ============================================================================

@router.get("/stats", response_model=PlaybookStats)
async def get_playbook_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get playbook execution statistics
    """
    try:
        total_playbooks = db.query(func.count(Playbook.playbook_id)).scalar() or 0
        enabled_playbooks = db.query(func.count(Playbook.playbook_id)).filter(
            Playbook.is_enabled == True
        ).scalar() or 0

        total_executions = db.query(func.count(PlaybookExecution.execution_id)).scalar() or 0
        successful_executions = db.query(func.count(PlaybookExecution.execution_id)).filter(
            PlaybookExecution.status == PlaybookStatus.COMPLETED
        ).scalar() or 0
        failed_executions = db.query(func.count(PlaybookExecution.execution_id)).filter(
            PlaybookExecution.status == PlaybookStatus.FAILED
        ).scalar() or 0
        pending_approvals = db.query(func.count(PlaybookExecution.execution_id)).filter(
            PlaybookExecution.status == PlaybookStatus.PENDING_APPROVAL
        ).scalar() or 0

        # Calculate average execution time
        avg_time_result = db.query(
            func.avg(
                func.extract('epoch', PlaybookExecution.completed_at - PlaybookExecution.started_at)
            )
        ).filter(
            PlaybookExecution.completed_at.isnot(None),
            PlaybookExecution.status == PlaybookStatus.COMPLETED
        ).scalar()

        return {
            "total_playbooks": total_playbooks,
            "enabled_playbooks": enabled_playbooks,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "pending_approvals": pending_approvals,
            "avg_execution_time_seconds": float(avg_time_result) if avg_time_result else None
        }

    except Exception as e:
        logger.error(f"Error getting playbook stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )
