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
from app.models.ad import ADUser, ADComputer, ADGroup, ADSyncLog, SoftwareInstallRequest
from app.models.user import User
from app.api.v1.auth import get_current_user, require_role

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
        }
    }
