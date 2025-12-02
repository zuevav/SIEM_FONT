"""
API dependencies - authentication, database, permissions
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.core.security import decode_access_token, check_permission
from app.models import User
from app.schemas import CurrentUser

# Security scheme
security = HTTPBearer()


# ============================================================================
# DATABASE DEPENDENCY
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Get database session

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """
    Get current authenticated user from JWT token

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    # Get user ID from token
    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.UserId == user_id).first()
    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.IsActive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Return current user info
    return CurrentUser(
        user_id=user.UserId,
        username=user.Username,
        role=user.Role,
        is_admin=user.is_admin,
        is_analyst=user.is_analyst,
        can_write=user.can_write
    )


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Get current active user
    Just an alias for get_current_user for clarity
    """
    return current_user


# ============================================================================
# PERMISSION DEPENDENCIES
# ============================================================================

class PermissionChecker:
    """
    Permission checker dependency

    Usage:
        @app.get("/admin")
        def admin_endpoint(user: CurrentUser = Depends(require_role("admin"))):
            ...
    """

    def __init__(self, required_role: str):
        self.required_role = required_role

    def __call__(
        self,
        current_user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        if not check_permission(current_user.role, self.required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {self.required_role}"
            )
        return current_user


def require_role(role: str):
    """
    Require specific role

    Args:
        role: Required role (viewer, analyst, admin)

    Returns:
        PermissionChecker: Dependency

    Usage:
        @app.get("/admin")
        def admin_endpoint(user: CurrentUser = Depends(require_role("admin"))):
            ...
    """
    return PermissionChecker(role)


# Convenient aliases
require_admin = require_role("admin")
require_analyst = require_role("analyst")
require_viewer = require_role("viewer")


# ============================================================================
# AGENT AUTHENTICATION
# ============================================================================

async def get_agent_id_from_header(
    x_agent_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> str:
    """
    Get agent ID from X-Agent-ID header

    Args:
        x_agent_id: Agent ID from header
        db: Database session

    Returns:
        str: Agent ID

    Raises:
        HTTPException: 401 if header is missing or agent not found
    """
    if not x_agent_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Agent-ID header is required"
        )

    # TODO: Verify agent exists and is active
    # from app.models import Agent
    # agent = db.query(Agent).filter(Agent.AgentId == x_agent_id).first()
    # if not agent:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Agent not found"
    #     )

    return x_agent_id


# ============================================================================
# PAGINATION DEPENDENCY
# ============================================================================

class PaginationParams:
    """
    Pagination parameters

    Usage:
        @app.get("/items")
        def get_items(pagination: PaginationParams = Depends()):
            skip = pagination.skip
            limit = pagination.limit
    """

    def __init__(
        self,
        page: int = 1,
        size: int = 100,
        max_size: int = 1000
    ):
        self.page = max(1, page)
        self.size = min(max(1, size), max_size)
        self.skip = (self.page - 1) * self.size
        self.limit = self.size

    @property
    def offset(self) -> int:
        """Get offset for database query"""
        return self.skip


def get_pagination(
    page: int = 1,
    size: int = 100
) -> PaginationParams:
    """
    Get pagination parameters

    Args:
        page: Page number (1-indexed)
        size: Page size

    Returns:
        PaginationParams: Pagination parameters
    """
    return PaginationParams(page=page, size=size)
