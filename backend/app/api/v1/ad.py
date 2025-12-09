"""
Active Directory API Router
Endpoints for AD users, computers, groups and software installation requests
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.ad import (
    ADUser, ADComputer, ADGroup, ADSyncLog, SoftwareInstallRequest,
    RemoteSession, PeerHelpSession, RemoteScript, RemoteScriptExecution,
    AppStoreApp, AppStoreInstallRequest
)
import json
import secrets
import string
from app.models.user import User
from app.models.agent import Agent
from app.api.v1.auth import get_current_user, require_role
import uuid

router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ADUserResponse(BaseModel):
    ADUserId: int
    ObjectGUID: Optional[str]
    SID: Optional[str]
    SamAccountName: str
    UserPrincipalName: Optional[str]
    DisplayName: Optional[str]
    FirstName: Optional[str]
    LastName: Optional[str]
    Email: Optional[str]
    Phone: Optional[str]
    Department: Optional[str]
    Title: Optional[str]
    ManagerDisplayName: Optional[str]
    Company: Optional[str]
    OrganizationalUnit: Optional[str]
    Domain: Optional[str]
    IsEnabled: bool
    IsLocked: bool
    LastLogon: Optional[datetime]
    RiskScore: int

    class Config:
        from_attributes = True


class ADComputerResponse(BaseModel):
    ADComputerId: int
    ObjectGUID: Optional[str]
    Name: str
    DNSHostName: Optional[str]
    Description: Optional[str]
    IPv4Address: Optional[str]
    OperatingSystem: Optional[str]
    OperatingSystemVersion: Optional[str]
    OrganizationalUnit: Optional[str]
    Domain: Optional[str]
    IsEnabled: bool
    LastLogon: Optional[datetime]
    AgentId: Optional[str]
    CriticalityLevel: str

    class Config:
        from_attributes = True


class ADGroupResponse(BaseModel):
    ADGroupId: int
    Name: str
    SamAccountName: Optional[str]
    Description: Optional[str]
    GroupCategory: Optional[str]
    GroupScope: Optional[str]
    Domain: Optional[str]
    MemberCount: int
    IsPrivileged: bool

    class Config:
        from_attributes = True


class SoftwareInstallRequestCreate(BaseModel):
    """Schema for creating a new software install request (from agent)"""
    AgentId: str
    ComputerName: str
    UserName: str
    UserDisplayName: Optional[str] = None
    UserDepartment: Optional[str] = None
    UserEmail: Optional[str] = None
    SoftwareName: str
    SoftwareVersion: Optional[str] = None
    SoftwarePublisher: Optional[str] = None
    InstallerPath: Optional[str] = None
    InstallerHash: Optional[str] = None
    InstallerSize: Optional[int] = None
    UserComment: Optional[str] = None
    BusinessJustification: Optional[str] = None


class SoftwareInstallRequestResponse(BaseModel):
    RequestId: int
    AgentId: str
    ComputerName: str
    UserName: str
    UserDisplayName: Optional[str]
    UserDepartment: Optional[str]
    UserEmail: Optional[str]
    SoftwareName: str
    SoftwareVersion: Optional[str]
    SoftwarePublisher: Optional[str]
    InstallerPath: Optional[str]
    InstallerHash: Optional[str]
    VirusTotalDetections: int
    ThreatIntelScore: int
    UserComment: Optional[str]
    BusinessJustification: Optional[str]
    RequestedAt: datetime
    Status: str
    ReviewedAt: Optional[datetime]
    AdminComment: Optional[str]
    ApprovedUntil: Optional[datetime]

    class Config:
        from_attributes = True


class ReviewRequestInput(BaseModel):
    """Schema for admin to approve/deny a request"""
    action: str = Field(..., pattern="^(approve|deny)$")
    admin_comment: Optional[str] = None
    approval_hours: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week


class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# AD USERS ENDPOINTS
# ============================================================================

@router.get("/users", response_model=PaginatedResponse)
async def get_ad_users(
    search: Optional[str] = Query(None, description="Search by name, email, username"),
    department: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    enabled_only: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of AD users with filtering and pagination"""

    query = db.query(ADUser)

    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                ADUser.SamAccountName.ilike(search_term),
                ADUser.DisplayName.ilike(search_term),
                ADUser.Email.ilike(search_term),
                ADUser.Department.ilike(search_term),
            )
        )

    # Department filter
    if department:
        query = query.filter(ADUser.Department == department)

    # Domain filter
    if domain:
        query = query.filter(ADUser.Domain == domain)

    # Enabled only filter
    if enabled_only:
        query = query.filter(ADUser.IsEnabled == True)

    # Get total count
    total = query.count()

    # Pagination
    offset = (page - 1) * page_size
    users = query.order_by(ADUser.DisplayName).offset(offset).limit(page_size).all()

    return PaginatedResponse(
        items=[ADUserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/users/{user_id}", response_model=ADUserResponse)
async def get_ad_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AD user by ID"""
    user = db.query(ADUser).filter(ADUser.ADUserId == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="AD user not found")
    return user


@router.get("/users/departments/list")
async def get_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of unique departments"""
    departments = db.query(ADUser.Department).distinct().filter(ADUser.Department.isnot(None)).all()
    return [d[0] for d in departments if d[0]]


# ============================================================================
# AD COMPUTERS ENDPOINTS
# ============================================================================

@router.get("/computers", response_model=PaginatedResponse)
async def get_ad_computers(
    search: Optional[str] = Query(None, description="Search by name, DNS name"),
    domain: Optional[str] = Query(None),
    os: Optional[str] = Query(None, description="Filter by OS"),
    enabled_only: bool = Query(True),
    has_agent: Optional[bool] = Query(None, description="Filter by agent presence"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of AD computers with filtering and pagination"""

    query = db.query(ADComputer)

    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                ADComputer.Name.ilike(search_term),
                ADComputer.DNSHostName.ilike(search_term),
                ADComputer.Description.ilike(search_term),
            )
        )

    # Domain filter
    if domain:
        query = query.filter(ADComputer.Domain == domain)

    # OS filter
    if os:
        query = query.filter(ADComputer.OperatingSystem.ilike(f"%{os}%"))

    # Enabled only filter
    if enabled_only:
        query = query.filter(ADComputer.IsEnabled == True)

    # Has agent filter
    if has_agent is True:
        query = query.filter(ADComputer.AgentId.isnot(None))
    elif has_agent is False:
        query = query.filter(ADComputer.AgentId.is_(None))

    # Get total count
    total = query.count()

    # Pagination
    offset = (page - 1) * page_size
    computers = query.order_by(ADComputer.Name).offset(offset).limit(page_size).all()

    return PaginatedResponse(
        items=[ADComputerResponse.model_validate(c) for c in computers],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/computers/{computer_id}", response_model=ADComputerResponse)
async def get_ad_computer(
    computer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AD computer by ID"""
    computer = db.query(ADComputer).filter(ADComputer.ADComputerId == computer_id).first()
    if not computer:
        raise HTTPException(status_code=404, detail="AD computer not found")
    return computer


# ============================================================================
# AD GROUPS ENDPOINTS
# ============================================================================

@router.get("/groups", response_model=PaginatedResponse)
async def get_ad_groups(
    search: Optional[str] = Query(None),
    privileged_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of AD groups"""

    query = db.query(ADGroup)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                ADGroup.Name.ilike(search_term),
                ADGroup.Description.ilike(search_term),
            )
        )

    if privileged_only:
        query = query.filter(ADGroup.IsPrivileged == True)

    total = query.count()
    offset = (page - 1) * page_size
    groups = query.order_by(ADGroup.Name).offset(offset).limit(page_size).all()

    return PaginatedResponse(
        items=[ADGroupResponse.model_validate(g) for g in groups],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


# ============================================================================
# SOFTWARE INSTALL REQUESTS ENDPOINTS
# ============================================================================

@router.post("/software-requests", status_code=status.HTTP_201_CREATED)
async def create_software_request(
    request: SoftwareInstallRequestCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new software installation request (called by agent)
    No authentication required - uses agent ID for verification
    """
    # Create the request
    new_request = SoftwareInstallRequest(
        AgentId=request.AgentId,
        ComputerName=request.ComputerName,
        UserName=request.UserName,
        UserDisplayName=request.UserDisplayName,
        UserDepartment=request.UserDepartment,
        UserEmail=request.UserEmail,
        SoftwareName=request.SoftwareName,
        SoftwareVersion=request.SoftwareVersion,
        SoftwarePublisher=request.SoftwarePublisher,
        InstallerPath=request.InstallerPath,
        InstallerHash=request.InstallerHash,
        InstallerSize=request.InstallerSize,
        UserComment=request.UserComment,
        BusinessJustification=request.BusinessJustification,
        Status="pending",
        RequestedAt=datetime.utcnow()
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # TODO: Send notification to admins (Telegram, Email, WebSocket)
    # TODO: Check VirusTotal for installer hash

    return {
        "request_id": new_request.RequestId,
        "status": "pending",
        "message": "Request created successfully. Waiting for admin approval."
    }


@router.get("/software-requests", response_model=PaginatedResponse)
async def get_software_requests(
    status_filter: Optional[str] = Query(None, description="pending, approved, denied, expired"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of software installation requests (admin view)"""

    query = db.query(SoftwareInstallRequest)

    if status_filter:
        query = query.filter(SoftwareInstallRequest.Status == status_filter)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                SoftwareInstallRequest.SoftwareName.ilike(search_term),
                SoftwareInstallRequest.UserName.ilike(search_term),
                SoftwareInstallRequest.ComputerName.ilike(search_term),
            )
        )

    # Order by most recent first
    query = query.order_by(SoftwareInstallRequest.RequestedAt.desc())

    total = query.count()
    offset = (page - 1) * page_size
    requests = query.offset(offset).limit(page_size).all()

    return PaginatedResponse(
        items=[SoftwareInstallRequestResponse.model_validate(r) for r in requests],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/software-requests/pending/count")
async def get_pending_requests_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get count of pending software requests"""
    count = db.query(SoftwareInstallRequest).filter(
        SoftwareInstallRequest.Status == "pending"
    ).count()
    return {"pending_count": count}


@router.get("/software-requests/{request_id}", response_model=SoftwareInstallRequestResponse)
async def get_software_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get software request details"""
    request = db.query(SoftwareInstallRequest).filter(
        SoftwareInstallRequest.RequestId == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    return request


@router.post("/software-requests/{request_id}/review")
async def review_software_request(
    request_id: int,
    review: ReviewRequestInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    """
    Approve or deny a software installation request
    Only admins and analysts can review requests
    """
    request = db.query(SoftwareInstallRequest).filter(
        SoftwareInstallRequest.RequestId == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.Status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Request already {request.Status}. Cannot review."
        )

    # Update request status
    request.Status = "approved" if review.action == "approve" else "denied"
    request.ReviewedBy = current_user.UserId
    request.ReviewedAt = datetime.utcnow()
    request.AdminComment = review.admin_comment

    if review.action == "approve":
        request.ApprovedUntil = datetime.utcnow() + timedelta(hours=review.approval_hours)

    db.commit()
    db.refresh(request)

    # TODO: Send notification to agent about decision
    # TODO: Send notification to user about decision

    return {
        "request_id": request.RequestId,
        "status": request.Status,
        "message": f"Request {request.Status} successfully",
        "approved_until": request.ApprovedUntil.isoformat() if request.ApprovedUntil else None
    }


@router.get("/software-requests/{request_id}/status")
async def check_request_status(
    request_id: int,
    db: Session = Depends(get_db)
):
    """
    Check status of a software request (called by agent)
    No authentication - agent polls this endpoint
    """
    request = db.query(SoftwareInstallRequest).filter(
        SoftwareInstallRequest.RequestId == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check if approval has expired
    if request.Status == "approved" and request.ApprovedUntil:
        if datetime.utcnow() > request.ApprovedUntil:
            request.Status = "expired"
            db.commit()

    return {
        "request_id": request.RequestId,
        "status": request.Status,
        "approved_until": request.ApprovedUntil.isoformat() if request.ApprovedUntil else None,
        "admin_comment": request.AdminComment,
        "can_install": request.Status == "approved" and (
            request.ApprovedUntil is None or datetime.utcnow() < request.ApprovedUntil
        )
    }


@router.post("/software-requests/{request_id}/confirm-install")
async def confirm_installation(
    request_id: int,
    db: Session = Depends(get_db)
):
    """
    Confirm that software was installed (called by agent)
    """
    request = db.query(SoftwareInstallRequest).filter(
        SoftwareInstallRequest.RequestId == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.Status != "approved":
        raise HTTPException(status_code=400, detail="Request is not approved")

    request.InstallationConfirmed = True
    request.InstalledAt = datetime.utcnow()
    db.commit()

    return {"message": "Installation confirmed", "installed_at": request.InstalledAt.isoformat()}


# ============================================================================
# AD SYNC ENDPOINTS
# ============================================================================

@router.post("/sync")
async def start_ad_sync(
    sync_type: str = Query("full", pattern="^(full|incremental|users|computers|groups)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Start AD synchronization (admin only)"""
    # Create sync log entry
    sync_log = ADSyncLog(
        SyncType=sync_type,
        Status="running",
        StartedAt=datetime.utcnow()
    )
    db.add(sync_log)
    db.commit()

    # TODO: Implement actual AD sync using LDAP
    # This would be a background task

    return {
        "sync_id": sync_log.LogId,
        "status": "started",
        "sync_type": sync_type,
        "message": "AD synchronization started"
    }


@router.get("/sync/status")
async def get_sync_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get latest AD sync status"""
    latest_sync = db.query(ADSyncLog).order_by(ADSyncLog.LogId.desc()).first()

    if not latest_sync:
        return {"message": "No sync history found"}

    return {
        "sync_id": latest_sync.LogId,
        "sync_type": latest_sync.SyncType,
        "status": latest_sync.Status,
        "started_at": latest_sync.StartedAt.isoformat() if latest_sync.StartedAt else None,
        "completed_at": latest_sync.CompletedAt.isoformat() if latest_sync.CompletedAt else None,
        "stats": {
            "users_added": latest_sync.UsersAdded,
            "users_updated": latest_sync.UsersUpdated,
            "computers_added": latest_sync.ComputersAdded,
            "computers_updated": latest_sync.ComputersUpdated,
            "groups_added": latest_sync.GroupsAdded,
            "groups_updated": latest_sync.GroupsUpdated,
            "errors": latest_sync.ErrorCount
        }
    }


# ============================================================================
# STATISTICS ENDPOINTS
# ============================================================================

@router.get("/stats")
async def get_ad_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AD statistics"""
    return {
        "users": {
            "total": db.query(ADUser).count(),
            "enabled": db.query(ADUser).filter(ADUser.IsEnabled == True).count(),
            "disabled": db.query(ADUser).filter(ADUser.IsEnabled == False).count(),
            "locked": db.query(ADUser).filter(ADUser.IsLocked == True).count(),
        },
        "computers": {
            "total": db.query(ADComputer).count(),
            "enabled": db.query(ADComputer).filter(ADComputer.IsEnabled == True).count(),
            "with_agent": db.query(ADComputer).filter(ADComputer.AgentId.isnot(None)).count(),
        },
        "groups": {
            "total": db.query(ADGroup).count(),
            "privileged": db.query(ADGroup).filter(ADGroup.IsPrivileged == True).count(),
        },
        "software_requests": {
            "pending": db.query(SoftwareInstallRequest).filter(SoftwareInstallRequest.Status == "pending").count(),
            "approved": db.query(SoftwareInstallRequest).filter(SoftwareInstallRequest.Status == "approved").count(),
            "denied": db.query(SoftwareInstallRequest).filter(SoftwareInstallRequest.Status == "denied").count(),
        },
        "remote_sessions": {
            "active": db.query(RemoteSession).filter(RemoteSession.Status == "active").count(),
            "pending": db.query(RemoteSession).filter(RemoteSession.Status == "pending").count(),
        }
    }


# ============================================================================
# REMOTE SESSION SCHEMAS
# ============================================================================

class RemoteSessionCreate(BaseModel):
    """Schema for creating a remote session request"""
    target_user_id: Optional[int] = None  # ADUserId
    target_computer_id: Optional[int] = None  # ADComputerId
    target_agent_id: Optional[str] = None  # AgentId directly
    session_type: str = Field(default="remote_assistance", pattern="^(remote_assistance|shadow|screen_share)$")
    reason: Optional[str] = None
    ticket_number: Optional[str] = None
    record_session: bool = False


class RemoteSessionResponse(BaseModel):
    SessionId: int
    SessionGUID: str
    AgentId: str
    ComputerName: Optional[str]
    ComputerIP: Optional[str]
    TargetUserName: Optional[str]
    TargetUserDisplayName: Optional[str]
    InitiatedByName: Optional[str]
    SessionType: str
    Reason: Optional[str]
    TicketNumber: Optional[str]
    Status: str
    RequestedAt: datetime
    UserRespondedAt: Optional[datetime]
    ConnectedAt: Optional[datetime]
    EndedAt: Optional[datetime]
    ConnectionString: Optional[str]
    ConnectionPassword: Optional[str]
    Port: Optional[int]
    UserConsented: bool
    DurationSeconds: Optional[int]

    class Config:
        from_attributes = True


class RemoteSessionUserResponse(BaseModel):
    """Response for agent - user consent request"""
    action: str = Field(..., pattern="^(accept|decline)$")
    connection_string: Optional[str] = None
    connection_password: Optional[str] = None
    port: Optional[int] = None
    message: Optional[str] = None


# ============================================================================
# REMOTE SESSION ENDPOINTS
# ============================================================================

@router.post("/remote-sessions", status_code=status.HTTP_201_CREATED)
async def create_remote_session(
    request: RemoteSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    """
    Create a new remote session request
    Admin selects a user/computer and initiates remote connection
    """
    agent_id = None
    computer_name = None
    computer_ip = None
    target_user_name = None
    target_user_display = None
    ad_user_id = None

    # Determine target by user, computer, or agent
    if request.target_user_id:
        # Find user and their computer
        ad_user = db.query(ADUser).filter(ADUser.ADUserId == request.target_user_id).first()
        if not ad_user:
            raise HTTPException(status_code=404, detail="AD user not found")

        ad_user_id = ad_user.ADUserId
        target_user_name = ad_user.SamAccountName
        target_user_display = ad_user.DisplayName

        # Find computer where user last logged in (if available)
        # For now, we need to specify computer separately or use agent
        if not request.target_agent_id and not request.target_computer_id:
            raise HTTPException(
                status_code=400,
                detail="Please specify target_computer_id or target_agent_id for this user"
            )

    if request.target_computer_id:
        computer = db.query(ADComputer).filter(ADComputer.ADComputerId == request.target_computer_id).first()
        if not computer:
            raise HTTPException(status_code=404, detail="AD computer not found")

        computer_name = computer.Name
        computer_ip = computer.IPv4Address
        agent_id = computer.AgentId

        if not agent_id:
            raise HTTPException(
                status_code=400,
                detail="This computer does not have an agent installed"
            )

    if request.target_agent_id:
        agent = db.query(Agent).filter(Agent.AgentId == request.target_agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent_id = agent.AgentId
        computer_name = agent.Hostname
        computer_ip = agent.IPAddress

    if not agent_id:
        raise HTTPException(status_code=400, detail="Could not determine target agent")

    # Create session
    session_guid = str(uuid.uuid4())

    new_session = RemoteSession(
        SessionGUID=session_guid,
        AgentId=agent_id,
        ComputerName=computer_name,
        ComputerIP=computer_ip,
        TargetUserName=target_user_name,
        TargetUserDisplayName=target_user_display,
        ADUserId=ad_user_id,
        InitiatedBy=current_user.UserId,
        InitiatedByName=current_user.Username,
        SessionType=request.session_type,
        Reason=request.reason,
        TicketNumber=request.ticket_number,
        Status="pending",
        RecordSession=request.record_session,
        RequestedAt=datetime.utcnow()
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # TODO: Send command to agent via WebSocket/message queue
    # The agent will receive this and show consent dialog to user

    return {
        "session_id": new_session.SessionId,
        "session_guid": session_guid,
        "status": "pending",
        "message": "Remote session request created. Waiting for user consent.",
        "agent_id": agent_id,
        "computer": computer_name
    }


@router.get("/remote-sessions", response_model=PaginatedResponse)
async def get_remote_sessions(
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of remote sessions"""
    query = db.query(RemoteSession)

    if status_filter:
        query = query.filter(RemoteSession.Status == status_filter)

    query = query.order_by(RemoteSession.RequestedAt.desc())

    total = query.count()
    offset = (page - 1) * page_size
    sessions = query.offset(offset).limit(page_size).all()

    return PaginatedResponse(
        items=[RemoteSessionResponse.model_validate(s) for s in sessions],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/remote-sessions/active")
async def get_active_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all active remote sessions"""
    sessions = db.query(RemoteSession).filter(
        RemoteSession.Status.in_(["pending", "connecting", "active"])
    ).order_by(RemoteSession.RequestedAt.desc()).all()

    return [RemoteSessionResponse.model_validate(s) for s in sessions]


@router.get("/remote-sessions/{session_id}", response_model=RemoteSessionResponse)
async def get_remote_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get remote session details"""
    session = db.query(RemoteSession).filter(RemoteSession.SessionId == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/remote-sessions/pending/{agent_id}")
async def get_pending_session_for_agent(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    Get pending remote session for agent (called by agent)
    Agent polls this to check if admin wants to connect
    """
    session = db.query(RemoteSession).filter(
        RemoteSession.AgentId == agent_id,
        RemoteSession.Status == "pending"
    ).order_by(RemoteSession.RequestedAt.desc()).first()

    if not session:
        return {"has_pending": False}

    return {
        "has_pending": True,
        "session_guid": session.SessionGUID,
        "session_type": session.SessionType,
        "initiated_by": session.InitiatedByName,
        "reason": session.Reason,
        "requested_at": session.RequestedAt.isoformat()
    }


@router.post("/remote-sessions/{session_guid}/user-response")
async def user_response_to_session(
    session_guid: str,
    response: RemoteSessionUserResponse,
    db: Session = Depends(get_db)
):
    """
    User responds to remote session request (called by agent)
    User accepts or declines the connection request
    """
    session = db.query(RemoteSession).filter(
        RemoteSession.SessionGUID == session_guid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.Status != "pending":
        raise HTTPException(status_code=400, detail="Session is not pending")

    session.UserRespondedAt = datetime.utcnow()

    if response.action == "accept":
        session.UserConsented = True
        session.Status = "connecting"
        session.ConnectionString = response.connection_string
        session.ConnectionPassword = response.connection_password
        session.Port = response.port
        session.UserConsentMessage = response.message
    else:
        session.UserConsented = False
        session.Status = "user_declined"
        session.UserConsentMessage = response.message

    db.commit()
    db.refresh(session)

    return {
        "session_guid": session.SessionGUID,
        "status": session.Status,
        "user_consented": session.UserConsented
    }


@router.post("/remote-sessions/{session_guid}/connected")
async def mark_session_connected(
    session_guid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark session as connected (admin clicked connect)"""
    session = db.query(RemoteSession).filter(
        RemoteSession.SessionGUID == session_guid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.Status != "connecting":
        raise HTTPException(status_code=400, detail="Session is not in connecting state")

    session.Status = "active"
    session.ConnectedAt = datetime.utcnow()
    db.commit()

    return {"status": "active", "connected_at": session.ConnectedAt.isoformat()}


@router.post("/remote-sessions/{session_guid}/end")
async def end_remote_session(
    session_guid: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """End a remote session"""
    session = db.query(RemoteSession).filter(
        RemoteSession.SessionGUID == session_guid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.Status = "completed"
    session.EndedAt = datetime.utcnow()

    if session.ConnectedAt:
        duration = (session.EndedAt - session.ConnectedAt).total_seconds()
        session.DurationSeconds = int(duration)

    if notes:
        session.Notes = notes

    db.commit()

    return {
        "status": "completed",
        "duration_seconds": session.DurationSeconds
    }


@router.post("/remote-sessions/{session_guid}/cancel")
async def cancel_remote_session(
    session_guid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a pending remote session"""
    session = db.query(RemoteSession).filter(
        RemoteSession.SessionGUID == session_guid
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.Status not in ["pending", "connecting"]:
        raise HTTPException(status_code=400, detail="Can only cancel pending or connecting sessions")

    session.Status = "cancelled"
    session.EndedAt = datetime.utcnow()
    db.commit()

    return {"status": "cancelled"}


# ============================================================================
# PEER HELP (USER-TO-USER) SCHEMAS
# ============================================================================

class PeerHelpRequest(BaseModel):
    """Request from agent to create a help session"""
    agent_id: str
    computer_name: str
    computer_ip: Optional[str] = None
    user_name: str
    user_display_name: Optional[str] = None
    description: Optional[str] = None
    expiry_minutes: int = Field(default=30, ge=5, le=120)


class PeerHelpJoin(BaseModel):
    """Helper joining a session"""
    helper_name: str
    helper_ip: Optional[str] = None


class PeerHelpConsent(BaseModel):
    """Requester's consent response"""
    action: str = Field(..., pattern="^(accept|decline)$")
    connection_password: Optional[str] = None
    port: Optional[int] = None


class PeerHelpResponse(BaseModel):
    SessionId: int
    SessionToken: str
    RequesterComputerName: Optional[str]
    RequesterUserName: Optional[str]
    RequesterDisplayName: Optional[str]
    HelperName: Optional[str]
    Description: Optional[str]
    ShareableLink: Optional[str]
    Status: str
    CreatedAt: datetime
    ExpiresAt: Optional[datetime]
    HelperJoinedAt: Optional[datetime]
    ConnectionPassword: Optional[str]
    Port: Optional[int]
    DurationSeconds: Optional[int]

    class Config:
        from_attributes = True


def generate_short_token(length: int = 8) -> str:
    """Generate a short, easy to share token"""
    # Use only uppercase letters and digits, excluding confusing chars (0,O,I,1,L)
    alphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ============================================================================
# PEER HELP ENDPOINTS
# ============================================================================

@router.post("/peer-help/request")
async def create_peer_help_request(
    request: PeerHelpRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new peer help request (called by agent when user clicks "Help me")
    Returns a shareable link that can be sent to a colleague
    """
    # Generate unique token
    token = generate_short_token(8)

    # Ensure token is unique
    while db.query(PeerHelpSession).filter(PeerHelpSession.SessionToken == token).first():
        token = generate_short_token(8)

    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(minutes=request.expiry_minutes)

    # Create session
    session = PeerHelpSession(
        SessionToken=token,
        RequesterAgentId=request.agent_id,
        RequesterComputerName=request.computer_name,
        RequesterIP=request.computer_ip,
        RequesterUserName=request.user_name,
        RequesterDisplayName=request.user_display_name,
        Description=request.description,
        Status="waiting",
        ExpiresAt=expires_at,
        CreatedAt=datetime.utcnow()
    )

    # Generate shareable link (will be set based on server config)
    # Format: https://siem.company.com/help/{token}
    session.ShareableLink = f"/help/{token}"

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.SessionId,
        "token": token,
        "shareable_link": session.ShareableLink,
        "expires_at": expires_at.isoformat(),
        "message": f"Отправьте эту ссылку коллеге: /help/{token}"
    }


@router.get("/peer-help/{token}")
async def get_peer_help_session(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Get peer help session info by token (for helper joining)
    No authentication required - anyone with link can join
    """
    session = db.query(PeerHelpSession).filter(
        PeerHelpSession.SessionToken == token
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена или ссылка недействительна")

    # Check expiration
    if session.ExpiresAt and datetime.utcnow() > session.ExpiresAt:
        session.Status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Ссылка истекла")

    if session.Status not in ["waiting", "helper_joined", "pending_consent"]:
        raise HTTPException(
            status_code=400,
            detail=f"Сессия недоступна (статус: {session.Status})"
        )

    return {
        "session_id": session.SessionId,
        "token": token,
        "requester_name": session.RequesterDisplayName or session.RequesterUserName,
        "requester_computer": session.RequesterComputerName,
        "description": session.Description,
        "status": session.Status,
        "expires_at": session.ExpiresAt.isoformat() if session.ExpiresAt else None
    }


@router.post("/peer-help/{token}/join")
async def join_peer_help_session(
    token: str,
    join_data: PeerHelpJoin,
    db: Session = Depends(get_db)
):
    """
    Helper joins the session (clicks the link and enters their name)
    """
    session = db.query(PeerHelpSession).filter(
        PeerHelpSession.SessionToken == token
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    if session.ExpiresAt and datetime.utcnow() > session.ExpiresAt:
        session.Status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Ссылка истекла")

    if session.Status not in ["waiting"]:
        raise HTTPException(status_code=400, detail="Сессия уже активна или завершена")

    # Record helper info
    session.HelperName = join_data.helper_name
    session.HelperIP = join_data.helper_ip
    session.HelperJoinedAt = datetime.utcnow()
    session.Status = "helper_joined"

    db.commit()
    db.refresh(session)

    return {
        "status": "helper_joined",
        "message": f"Ожидание подтверждения от {session.RequesterDisplayName or session.RequesterUserName}",
        "session_id": session.SessionId
    }


@router.get("/peer-help/{token}/status")
async def check_peer_help_status(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Check status of peer help session
    Called by both agent and helper's browser
    """
    session = db.query(PeerHelpSession).filter(
        PeerHelpSession.SessionToken == token
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    # Check expiration
    if session.Status == "waiting" and session.ExpiresAt and datetime.utcnow() > session.ExpiresAt:
        session.Status = "expired"
        db.commit()

    return {
        "status": session.Status,
        "helper_name": session.HelperName,
        "helper_joined_at": session.HelperJoinedAt.isoformat() if session.HelperJoinedAt else None,
        "connection_password": session.ConnectionPassword if session.Status == "active" else None,
        "port": session.Port if session.Status == "active" else None,
        "can_connect": session.Status == "active"
    }


@router.get("/peer-help/pending/{agent_id}")
async def get_pending_peer_help(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    Get pending peer help session for agent
    Agent polls this to check if someone wants to help
    """
    session = db.query(PeerHelpSession).filter(
        PeerHelpSession.RequesterAgentId == agent_id,
        PeerHelpSession.Status == "helper_joined"
    ).order_by(PeerHelpSession.CreatedAt.desc()).first()

    if not session:
        return {"has_pending": False}

    return {
        "has_pending": True,
        "token": session.SessionToken,
        "helper_name": session.HelperName,
        "helper_ip": session.HelperIP,
        "helper_joined_at": session.HelperJoinedAt.isoformat()
    }


@router.post("/peer-help/{token}/consent")
async def peer_help_consent(
    token: str,
    consent: PeerHelpConsent,
    db: Session = Depends(get_db)
):
    """
    Requester gives consent (or declines) for helper to connect
    Called by agent after showing consent dialog to user
    """
    session = db.query(PeerHelpSession).filter(
        PeerHelpSession.SessionToken == token
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    if session.Status != "helper_joined":
        raise HTTPException(status_code=400, detail="Нет ожидающего помощника")

    if consent.action == "accept":
        session.Status = "active"
        session.ConsentGivenAt = datetime.utcnow()
        session.ConnectionPassword = consent.connection_password
        session.Port = consent.port
        message = "Подключение разрешено"
    else:
        session.Status = "declined"
        message = "Подключение отклонено пользователем"

    db.commit()

    return {
        "status": session.Status,
        "message": message
    }


@router.post("/peer-help/{token}/end")
async def end_peer_help_session(
    token: str,
    db: Session = Depends(get_db)
):
    """End a peer help session"""
    session = db.query(PeerHelpSession).filter(
        PeerHelpSession.SessionToken == token
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    session.Status = "completed"
    session.EndedAt = datetime.utcnow()

    if session.ConsentGivenAt:
        duration = (session.EndedAt - session.ConsentGivenAt).total_seconds()
        session.DurationSeconds = int(duration)

    db.commit()

    return {
        "status": "completed",
        "duration_seconds": session.DurationSeconds
    }


@router.post("/peer-help/{token}/cancel")
async def cancel_peer_help_session(
    token: str,
    db: Session = Depends(get_db)
):
    """Cancel a peer help session"""
    session = db.query(PeerHelpSession).filter(
        PeerHelpSession.SessionToken == token
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    if session.Status in ["completed", "cancelled", "expired"]:
        raise HTTPException(status_code=400, detail="Сессия уже завершена")

    session.Status = "cancelled"
    session.EndedAt = datetime.utcnow()
    db.commit()

    return {"status": "cancelled"}


# ============================================================================
# REMOTE SCRIPTS SCHEMAS
# ============================================================================

class RemoteScriptCreate(BaseModel):
    """Schema for creating a remote script"""
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    category: Optional[str] = None
    script_type: str = Field(default="powershell", pattern="^(powershell|batch|python)$")
    script_content: str = Field(..., min_length=1)
    parameters: Optional[List[dict]] = None  # [{"name": "param1", "type": "string", "required": true}]
    requires_admin: bool = True
    timeout: int = Field(default=300, ge=30, le=3600)


class RemoteScriptUpdate(BaseModel):
    """Schema for updating a remote script"""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    script_content: Optional[str] = None
    parameters: Optional[List[dict]] = None
    requires_admin: Optional[bool] = None
    timeout: Optional[int] = None
    is_active: Optional[bool] = None


class RemoteScriptResponse(BaseModel):
    ScriptId: int
    ScriptGUID: str
    Name: str
    Description: Optional[str]
    Category: Optional[str]
    ScriptType: str
    ScriptContent: str
    Parameters: Optional[str]
    RequiresAdmin: bool
    Timeout: int
    CreatedByName: Optional[str]
    CreatedAt: datetime
    IsActive: bool

    class Config:
        from_attributes = True


class ExecuteScriptRequest(BaseModel):
    """Request to execute a script on target"""
    script_id: int
    agent_ids: List[str]  # Can execute on multiple agents
    parameters: Optional[dict] = None  # {"param1": "value1"}


class RemoteScriptExecutionResponse(BaseModel):
    ExecutionId: int
    ExecutionGUID: str
    ScriptId: int
    ScriptName: Optional[str]
    AgentId: str
    ComputerName: Optional[str]
    ExecutedByName: Optional[str]
    ExecutedAt: datetime
    ExecutionParameters: Optional[str]
    Status: str
    StartedAt: Optional[datetime]
    CompletedAt: Optional[datetime]
    ExitCode: Optional[int]
    Output: Optional[str]
    ErrorOutput: Optional[str]
    DurationMs: Optional[int]

    class Config:
        from_attributes = True


# ============================================================================
# REMOTE SCRIPTS ENDPOINTS
# ============================================================================

@router.post("/scripts", status_code=status.HTTP_201_CREATED)
async def create_remote_script(
    script: RemoteScriptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Create a new remote script (admin only)"""
    script_guid = str(uuid.uuid4())

    new_script = RemoteScript(
        ScriptGUID=script_guid,
        Name=script.name,
        Description=script.description,
        Category=script.category,
        ScriptType=script.script_type,
        ScriptContent=script.script_content,
        Parameters=json.dumps(script.parameters) if script.parameters else None,
        RequiresAdmin=script.requires_admin,
        Timeout=script.timeout,
        CreatedBy=current_user.UserId,
        CreatedByName=current_user.Username,
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    db.add(new_script)
    db.commit()
    db.refresh(new_script)

    return {
        "script_id": new_script.ScriptId,
        "script_guid": script_guid,
        "message": "Script created successfully"
    }


@router.get("/scripts", response_model=PaginatedResponse)
async def get_remote_scripts(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    active_only: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of remote scripts"""
    query = db.query(RemoteScript)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                RemoteScript.Name.ilike(search_term),
                RemoteScript.Description.ilike(search_term),
            )
        )

    if category:
        query = query.filter(RemoteScript.Category == category)

    if active_only:
        query = query.filter(RemoteScript.IsActive == True)

    query = query.order_by(RemoteScript.Name)

    total = query.count()
    offset = (page - 1) * page_size
    scripts = query.offset(offset).limit(page_size).all()

    return PaginatedResponse(
        items=[RemoteScriptResponse.model_validate(s) for s in scripts],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/scripts/categories")
async def get_script_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of script categories"""
    categories = db.query(RemoteScript.Category).distinct().filter(
        RemoteScript.Category.isnot(None),
        RemoteScript.IsActive == True
    ).all()
    return [c[0] for c in categories if c[0]]


@router.get("/scripts/{script_id}", response_model=RemoteScriptResponse)
async def get_remote_script(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get script details"""
    script = db.query(RemoteScript).filter(RemoteScript.ScriptId == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.put("/scripts/{script_id}")
async def update_remote_script(
    script_id: int,
    update: RemoteScriptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Update a remote script"""
    script = db.query(RemoteScript).filter(RemoteScript.ScriptId == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    if update.name is not None:
        script.Name = update.name
    if update.description is not None:
        script.Description = update.description
    if update.category is not None:
        script.Category = update.category
    if update.script_content is not None:
        script.ScriptContent = update.script_content
    if update.parameters is not None:
        script.Parameters = json.dumps(update.parameters)
    if update.requires_admin is not None:
        script.RequiresAdmin = update.requires_admin
    if update.timeout is not None:
        script.Timeout = update.timeout
    if update.is_active is not None:
        script.IsActive = update.is_active

    script.UpdatedAt = datetime.utcnow()
    db.commit()

    return {"message": "Script updated successfully"}


@router.delete("/scripts/{script_id}")
async def delete_remote_script(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Delete a remote script (soft delete)"""
    script = db.query(RemoteScript).filter(RemoteScript.ScriptId == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    script.IsActive = False
    script.UpdatedAt = datetime.utcnow()
    db.commit()

    return {"message": "Script deleted successfully"}


@router.post("/scripts/execute")
async def execute_remote_script(
    request: ExecuteScriptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    """Execute a script on one or more agents"""
    # Verify script exists
    script = db.query(RemoteScript).filter(
        RemoteScript.ScriptId == request.script_id,
        RemoteScript.IsActive == True
    ).first()

    if not script:
        raise HTTPException(status_code=404, detail="Script not found or inactive")

    # Verify agents exist
    agents = db.query(Agent).filter(Agent.AgentId.in_(request.agent_ids)).all()
    if len(agents) != len(request.agent_ids):
        raise HTTPException(status_code=400, detail="One or more agents not found")

    executions = []

    for agent in agents:
        execution_guid = str(uuid.uuid4())

        execution = RemoteScriptExecution(
            ExecutionGUID=execution_guid,
            ScriptId=script.ScriptId,
            ScriptName=script.Name,
            AgentId=agent.AgentId,
            ComputerName=agent.Hostname,
            ExecutedBy=current_user.UserId,
            ExecutedByName=current_user.Username,
            ExecutedAt=datetime.utcnow(),
            ExecutionParameters=json.dumps(request.parameters) if request.parameters else None,
            Status="pending"
        )

        db.add(execution)
        executions.append({
            "execution_guid": execution_guid,
            "agent_id": agent.AgentId,
            "computer_name": agent.Hostname
        })

    db.commit()

    # TODO: Send execution command to agents via WebSocket/message queue

    return {
        "script_id": script.ScriptId,
        "script_name": script.Name,
        "executions": executions,
        "message": f"Script execution initiated on {len(executions)} agent(s)"
    }


@router.get("/scripts/executions/pending/{agent_id}")
async def get_pending_script_execution(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """Get pending script execution for agent (called by agent)"""
    execution = db.query(RemoteScriptExecution).filter(
        RemoteScriptExecution.AgentId == agent_id,
        RemoteScriptExecution.Status == "pending"
    ).order_by(RemoteScriptExecution.ExecutedAt).first()

    if not execution:
        return {"has_pending": False}

    script = db.query(RemoteScript).filter(
        RemoteScript.ScriptId == execution.ScriptId
    ).first()

    if not script:
        return {"has_pending": False}

    # Mark as sent
    execution.Status = "sent"
    db.commit()

    return {
        "has_pending": True,
        "execution_guid": execution.ExecutionGUID,
        "script_type": script.ScriptType,
        "script_content": script.ScriptContent,
        "parameters": json.loads(execution.ExecutionParameters) if execution.ExecutionParameters else None,
        "requires_admin": script.RequiresAdmin,
        "timeout": script.Timeout
    }


@router.post("/scripts/executions/{execution_guid}/result")
async def report_script_execution_result(
    execution_guid: str,
    exit_code: int,
    output: Optional[str] = None,
    error_output: Optional[str] = None,
    duration_ms: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Report script execution result (called by agent)"""
    execution = db.query(RemoteScriptExecution).filter(
        RemoteScriptExecution.ExecutionGUID == execution_guid
    ).first()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution.Status = "completed" if exit_code == 0 else "failed"
    execution.CompletedAt = datetime.utcnow()
    execution.ExitCode = exit_code
    execution.Output = output
    execution.ErrorOutput = error_output
    execution.DurationMs = duration_ms

    db.commit()

    return {"status": execution.Status}


@router.get("/scripts/executions", response_model=PaginatedResponse)
async def get_script_executions(
    script_id: Optional[int] = Query(None),
    agent_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get script execution history"""
    query = db.query(RemoteScriptExecution)

    if script_id:
        query = query.filter(RemoteScriptExecution.ScriptId == script_id)

    if agent_id:
        query = query.filter(RemoteScriptExecution.AgentId == agent_id)

    if status_filter:
        query = query.filter(RemoteScriptExecution.Status == status_filter)

    query = query.order_by(RemoteScriptExecution.ExecutedAt.desc())

    total = query.count()
    offset = (page - 1) * page_size
    executions = query.offset(offset).limit(page_size).all()

    return PaginatedResponse(
        items=[RemoteScriptExecutionResponse.model_validate(e) for e in executions],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


# ============================================================================
# APP STORE SCHEMAS
# ============================================================================

class AppStoreAppCreate(BaseModel):
    """Schema for creating an app store app"""
    name: str = Field(..., min_length=1, max_length=256)
    display_name: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    version: Optional[str] = None
    category: Optional[str] = None
    app_type: str = Field(default="by_request", pattern="^(always_allowed|by_request)$")
    installer_type: str = Field(default="exe", pattern="^(exe|msi|msix|script)$")
    installer_url: Optional[str] = None
    installer_path: Optional[str] = None
    installer_hash: Optional[str] = None
    installer_size: Optional[int] = None
    silent_install_args: Optional[str] = None
    uninstall_command: Optional[str] = None
    min_os_version: Optional[str] = None
    required_disk_space: Optional[int] = None
    requires_reboot: bool = False
    icon_url: Optional[str] = None
    is_featured: bool = False


class AppStoreAppUpdate(BaseModel):
    """Schema for updating an app store app"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    version: Optional[str] = None
    category: Optional[str] = None
    app_type: Optional[str] = None
    installer_url: Optional[str] = None
    installer_path: Optional[str] = None
    installer_hash: Optional[str] = None
    silent_install_args: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class AppStoreAppResponse(BaseModel):
    AppId: int
    AppGUID: str
    Name: str
    DisplayName: Optional[str]
    Description: Optional[str]
    Publisher: Optional[str]
    Version: Optional[str]
    Category: Optional[str]
    AppType: str
    InstallerType: str
    InstallerUrl: Optional[str]
    InstallerPath: Optional[str]
    SilentInstallArgs: Optional[str]
    RequiresReboot: bool
    IconUrl: Optional[str]
    AddedByName: Optional[str]
    AddedAt: datetime
    IsActive: bool
    IsFeatured: bool
    TotalInstalls: int
    PendingRequests: int

    class Config:
        from_attributes = True


class AppStoreInstallRequestCreate(BaseModel):
    """Schema for user requesting app installation"""
    app_id: int
    agent_id: str
    computer_name: str
    user_name: str
    user_display_name: Optional[str] = None
    user_department: Optional[str] = None
    request_reason: Optional[str] = None


class AppStoreInstallRequestResponse(BaseModel):
    RequestId: int
    RequestGUID: str
    AppId: int
    AppName: Optional[str]
    AgentId: str
    ComputerName: Optional[str]
    UserName: str
    UserDisplayName: Optional[str]
    UserDepartment: Optional[str]
    RequestReason: Optional[str]
    RequestedAt: datetime
    Status: str
    ReviewedByName: Optional[str]
    ReviewedAt: Optional[datetime]
    AdminComment: Optional[str]
    InstalledAt: Optional[datetime]

    class Config:
        from_attributes = True


class ReviewAppRequest(BaseModel):
    """Schema for admin reviewing app install request"""
    action: str = Field(..., pattern="^(approve|deny)$")
    admin_comment: Optional[str] = None


# ============================================================================
# APP STORE ENDPOINTS
# ============================================================================

@router.post("/appstore/apps", status_code=status.HTTP_201_CREATED)
async def create_appstore_app(
    app: AppStoreAppCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Create a new app in the store (admin only)"""
    app_guid = str(uuid.uuid4())

    new_app = AppStoreApp(
        AppGUID=app_guid,
        Name=app.name,
        DisplayName=app.display_name or app.name,
        Description=app.description,
        Publisher=app.publisher,
        Version=app.version,
        Category=app.category,
        AppType=app.app_type,
        InstallerType=app.installer_type,
        InstallerUrl=app.installer_url,
        InstallerPath=app.installer_path,
        InstallerHash=app.installer_hash,
        InstallerSize=app.installer_size,
        SilentInstallArgs=app.silent_install_args,
        UninstallCommand=app.uninstall_command,
        MinOSVersion=app.min_os_version,
        RequiredDiskSpace=app.required_disk_space,
        RequiresReboot=app.requires_reboot,
        IconUrl=app.icon_url,
        AddedBy=current_user.UserId,
        AddedByName=current_user.Username,
        AddedAt=datetime.utcnow(),
        IsActive=True,
        IsFeatured=app.is_featured
    )

    db.add(new_app)
    db.commit()
    db.refresh(new_app)

    return {
        "app_id": new_app.AppId,
        "app_guid": app_guid,
        "message": "App added to store successfully"
    }


@router.get("/appstore/apps", response_model=PaginatedResponse)
async def get_appstore_apps(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    app_type: Optional[str] = Query(None),
    featured_only: bool = Query(False),
    active_only: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of apps in the store"""
    query = db.query(AppStoreApp)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                AppStoreApp.Name.ilike(search_term),
                AppStoreApp.DisplayName.ilike(search_term),
                AppStoreApp.Description.ilike(search_term),
                AppStoreApp.Publisher.ilike(search_term),
            )
        )

    if category:
        query = query.filter(AppStoreApp.Category == category)

    if app_type:
        query = query.filter(AppStoreApp.AppType == app_type)

    if featured_only:
        query = query.filter(AppStoreApp.IsFeatured == True)

    if active_only:
        query = query.filter(AppStoreApp.IsActive == True)

    query = query.order_by(AppStoreApp.IsFeatured.desc(), AppStoreApp.Name)

    total = query.count()
    offset = (page - 1) * page_size
    apps = query.offset(offset).limit(page_size).all()

    return PaginatedResponse(
        items=[AppStoreAppResponse.model_validate(a) for a in apps],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/appstore/apps/client")
async def get_appstore_apps_for_client(
    agent_id: str,
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get available apps for client app store (called by agent)
    Returns apps with install status for this agent
    """
    query = db.query(AppStoreApp).filter(AppStoreApp.IsActive == True)

    if category:
        query = query.filter(AppStoreApp.Category == category)

    apps = query.order_by(AppStoreApp.IsFeatured.desc(), AppStoreApp.Name).all()

    result = []
    for app in apps:
        # Check if there's a pending request for this app and agent
        pending_request = db.query(AppStoreInstallRequest).filter(
            AppStoreInstallRequest.AppId == app.AppId,
            AppStoreInstallRequest.AgentId == agent_id,
            AppStoreInstallRequest.Status.in_(["pending", "approved", "installing"])
        ).first()

        result.append({
            "app_id": app.AppId,
            "app_guid": app.AppGUID,
            "name": app.Name,
            "display_name": app.DisplayName,
            "description": app.Description,
            "publisher": app.Publisher,
            "version": app.Version,
            "category": app.Category,
            "app_type": app.AppType,
            "icon_url": app.IconUrl,
            "is_featured": app.IsFeatured,
            "requires_reboot": app.RequiresReboot,
            "can_install": app.AppType == "always_allowed" or (pending_request and pending_request.Status == "approved"),
            "request_status": pending_request.Status if pending_request else None,
            "request_id": pending_request.RequestId if pending_request else None
        })

    return result


@router.get("/appstore/apps/categories")
async def get_appstore_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of app categories"""
    categories = db.query(AppStoreApp.Category).distinct().filter(
        AppStoreApp.Category.isnot(None),
        AppStoreApp.IsActive == True
    ).all()
    return [c[0] for c in categories if c[0]]


@router.get("/appstore/apps/{app_id}", response_model=AppStoreAppResponse)
async def get_appstore_app(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get app details"""
    app = db.query(AppStoreApp).filter(AppStoreApp.AppId == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.put("/appstore/apps/{app_id}")
async def update_appstore_app(
    app_id: int,
    update: AppStoreAppUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Update an app in the store"""
    app = db.query(AppStoreApp).filter(AppStoreApp.AppId == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(app, field.replace("_", "").title() if "_" in field else field.title().replace("_", ""), value)

    app.UpdatedAt = datetime.utcnow()
    db.commit()

    return {"message": "App updated successfully"}


@router.delete("/appstore/apps/{app_id}")
async def delete_appstore_app(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Delete an app from the store (soft delete)"""
    app = db.query(AppStoreApp).filter(AppStoreApp.AppId == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    app.IsActive = False
    app.UpdatedAt = datetime.utcnow()
    db.commit()

    return {"message": "App removed from store"}


@router.post("/appstore/requests", status_code=status.HTTP_201_CREATED)
async def create_app_install_request(
    request: AppStoreInstallRequestCreate,
    db: Session = Depends(get_db)
):
    """
    Request to install an app (called by agent)
    For always_allowed apps, immediately returns install info
    For by_request apps, creates a pending request
    """
    app = db.query(AppStoreApp).filter(
        AppStoreApp.AppId == request.app_id,
        AppStoreApp.IsActive == True
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    # Check for existing pending request
    existing = db.query(AppStoreInstallRequest).filter(
        AppStoreInstallRequest.AppId == request.app_id,
        AppStoreInstallRequest.AgentId == request.agent_id,
        AppStoreInstallRequest.Status.in_(["pending", "approved"])
    ).first()

    if existing:
        return {
            "request_id": existing.RequestId,
            "status": existing.Status,
            "message": "Request already exists",
            "can_install": existing.Status == "approved" or app.AppType == "always_allowed"
        }

    request_guid = str(uuid.uuid4())

    # For always_allowed, auto-approve
    initial_status = "approved" if app.AppType == "always_allowed" else "pending"

    new_request = AppStoreInstallRequest(
        RequestGUID=request_guid,
        AppId=app.AppId,
        AppName=app.Name,
        AgentId=request.agent_id,
        ComputerName=request.computer_name,
        UserName=request.user_name,
        UserDisplayName=request.user_display_name,
        UserDepartment=request.user_department,
        RequestReason=request.request_reason,
        RequestedAt=datetime.utcnow(),
        Status=initial_status
    )

    if app.AppType == "always_allowed":
        new_request.ReviewedAt = datetime.utcnow()
        new_request.AdminComment = "Auto-approved (always allowed app)"

    db.add(new_request)

    # Update pending count
    if app.AppType == "by_request":
        app.PendingRequests = (app.PendingRequests or 0) + 1

    db.commit()
    db.refresh(new_request)

    response = {
        "request_id": new_request.RequestId,
        "request_guid": request_guid,
        "status": new_request.Status,
        "can_install": app.AppType == "always_allowed"
    }

    if app.AppType == "always_allowed":
        response["install_info"] = {
            "installer_type": app.InstallerType,
            "installer_url": app.InstallerUrl,
            "installer_path": app.InstallerPath,
            "silent_install_args": app.SilentInstallArgs
        }
        response["message"] = "App approved for installation"
    else:
        response["message"] = "Request submitted. Waiting for admin approval."

    return response


@router.get("/appstore/requests", response_model=PaginatedResponse)
async def get_app_install_requests(
    status_filter: Optional[str] = Query(None),
    app_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get app install requests (admin view)"""
    query = db.query(AppStoreInstallRequest)

    if status_filter:
        query = query.filter(AppStoreInstallRequest.Status == status_filter)

    if app_id:
        query = query.filter(AppStoreInstallRequest.AppId == app_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                AppStoreInstallRequest.AppName.ilike(search_term),
                AppStoreInstallRequest.UserName.ilike(search_term),
                AppStoreInstallRequest.ComputerName.ilike(search_term),
            )
        )

    query = query.order_by(AppStoreInstallRequest.RequestedAt.desc())

    total = query.count()
    offset = (page - 1) * page_size
    requests = query.offset(offset).limit(page_size).all()

    return PaginatedResponse(
        items=[AppStoreInstallRequestResponse.model_validate(r) for r in requests],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/appstore/requests/pending/count")
async def get_pending_app_requests_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get count of pending app install requests"""
    count = db.query(AppStoreInstallRequest).filter(
        AppStoreInstallRequest.Status == "pending"
    ).count()
    return {"pending_count": count}


@router.post("/appstore/requests/{request_id}/review")
async def review_app_install_request(
    request_id: int,
    review: ReviewAppRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    """Approve or deny an app install request"""
    request = db.query(AppStoreInstallRequest).filter(
        AppStoreInstallRequest.RequestId == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.Status != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {request.Status}")

    request.Status = "approved" if review.action == "approve" else "denied"
    request.ReviewedBy = current_user.UserId
    request.ReviewedByName = current_user.Username
    request.ReviewedAt = datetime.utcnow()
    request.AdminComment = review.admin_comment

    # Update app pending count
    app = db.query(AppStoreApp).filter(AppStoreApp.AppId == request.AppId).first()
    if app and app.PendingRequests > 0:
        app.PendingRequests -= 1

    db.commit()

    return {
        "request_id": request.RequestId,
        "status": request.Status,
        "message": f"Request {request.Status}"
    }


@router.get("/appstore/requests/{request_id}/status")
async def check_app_request_status(
    request_id: int,
    db: Session = Depends(get_db)
):
    """Check status of app install request (called by agent)"""
    request = db.query(AppStoreInstallRequest).filter(
        AppStoreInstallRequest.RequestId == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    result = {
        "request_id": request.RequestId,
        "status": request.Status,
        "can_install": request.Status == "approved",
        "admin_comment": request.AdminComment
    }

    if request.Status == "approved":
        app = db.query(AppStoreApp).filter(AppStoreApp.AppId == request.AppId).first()
        if app:
            result["install_info"] = {
                "installer_type": app.InstallerType,
                "installer_url": app.InstallerUrl,
                "installer_path": app.InstallerPath,
                "silent_install_args": app.SilentInstallArgs
            }

    return result


@router.post("/appstore/requests/{request_id}/installed")
async def confirm_app_installed(
    request_id: int,
    exit_code: int = 0,
    output: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Confirm app was installed (called by agent)"""
    request = db.query(AppStoreInstallRequest).filter(
        AppStoreInstallRequest.RequestId == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if exit_code == 0:
        request.Status = "installed"
        request.InstalledAt = datetime.utcnow()

        # Update app install count
        app = db.query(AppStoreApp).filter(AppStoreApp.AppId == request.AppId).first()
        if app:
            app.TotalInstalls = (app.TotalInstalls or 0) + 1
    else:
        request.Status = "failed"

    request.InstallExitCode = exit_code
    request.InstallOutput = output
    db.commit()

    return {"status": request.Status}
