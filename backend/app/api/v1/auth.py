"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.api.deps import get_db, get_current_user, require_admin
from app.core.security import (
    verify_password,
    get_password_hash,
    create_session_token,
    validate_password_strength,
    get_client_ip,
    get_user_agent,
)
from app.models import User, Session as DBSession
from app.schemas import (
    LoginRequest,
    TokenResponse,
    UserInfo,
    PasswordChangeRequest,
    UserCreate,
    UserUpdate,
    UserResponse,
    CurrentUser,
)
from app.config import settings
import uuid

router = APIRouter()


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token

    - Validates username and password
    - Creates session in database
    - Returns JWT token
    """
    # Get user from database
    user = db.query(User).filter(User.Username == login_data.username).first()

    # Check if user exists and password is correct
    if not user or not verify_password(login_data.password, user.PasswordHash or ""):
        # Log failed attempt (TODO: implement lockout after N attempts)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.IsActive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Create JWT token
    token = create_session_token(user.UserId, user.Username)

    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )

    # Create session in database
    session_id = str(uuid.uuid4())
    db_session = DBSession(
        SessionId=session_id,
        UserId=user.UserId,
        Token=token,
        IPAddress=get_client_ip(request),
        UserAgent=get_user_agent(request),
        ExpiresAt=expires_at,
        IsActive=True
    )
    db.add(db_session)

    # Update last login time
    user.LastLogin = datetime.utcnow()

    db.commit()

    # Return token response
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserInfo(
            user_id=user.UserId,
            username=user.Username,
            email=user.Email,
            role=user.Role,
            is_active=user.IsActive
        )
    )


@router.post("/logout")
async def logout(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout current user

    - Deactivates current session
    """
    # Deactivate all active sessions for this user
    db.query(DBSession).filter(
        DBSession.UserId == current_user.user_id,
        DBSession.IsActive == True
    ).update({"IsActive": False})

    db.commit()

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information
    """
    user = db.query(User).filter(User.UserId == current_user.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        user_id=user.UserId,
        username=user.Username,
        email=user.Email,
        role=user.Role,
        is_ad_user=user.IsADUser,
        is_active=user.IsActive,
        created_at=user.CreatedAt,
        last_login=user.LastLogin
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password

    - Validates old password
    - Validates new password strength
    - Updates password hash
    """
    # Get user from database
    user = db.query(User).filter(User.UserId == current_user.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user is AD user (cannot change password)
    if user.IsADUser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for AD users"
        )

    # Verify old password
    if not verify_password(password_data.old_password, user.PasswordHash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect old password"
        )

    # Validate new password strength
    is_valid, error_message = validate_password_strength(password_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Update password hash
    user.PasswordHash = get_password_hash(password_data.new_password)
    db.commit()

    # Deactivate all sessions (force re-login)
    db.query(DBSession).filter(
        DBSession.UserId == user.UserId,
        DBSession.IsActive == True
    ).update({"IsActive": False})
    db.commit()

    return {"message": "Password changed successfully. Please login again."}


# ============================================================================
# USER MANAGEMENT ENDPOINTS (ADMIN ONLY)
# ============================================================================

@router.post("/users", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create new user (admin only)

    - Validates username uniqueness
    - Validates password strength
    - Creates user with hashed password
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.Username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Validate password strength
    is_valid, error_message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Create user
    new_user = User(
        Username=user_data.username,
        Email=user_data.email,
        PasswordHash=get_password_hash(user_data.password),
        Role=user_data.role,
        IsADUser=user_data.is_ad_user,
        IsActive=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        user_id=new_user.UserId,
        username=new_user.Username,
        email=new_user.Email,
        role=new_user.Role,
        is_ad_user=new_user.IsADUser,
        is_active=new_user.IsActive,
        created_at=new_user.CreatedAt,
        last_login=new_user.LastLogin
    )


@router.get("/users", response_model=list[UserResponse], dependencies=[Depends(require_admin)])
async def list_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    List all users (admin only)
    """
    users = db.query(User).offset(skip).limit(limit).all()

    return [
        UserResponse(
            user_id=user.UserId,
            username=user.Username,
            email=user.Email,
            role=user.Role,
            is_ad_user=user.IsADUser,
            is_active=user.IsActive,
            created_at=user.CreatedAt,
            last_login=user.LastLogin
        )
        for user in users
    ]


@router.patch("/users/{user_id}", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user (admin only)

    - Can update email, role, active status
    """
    user = db.query(User).filter(User.UserId == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update fields
    if user_data.email is not None:
        user.Email = user_data.email
    if user_data.role is not None:
        user.Role = user_data.role
    if user_data.is_active is not None:
        user.IsActive = user_data.is_active

    db.commit()
    db.refresh(user)

    return UserResponse(
        user_id=user.UserId,
        username=user.Username,
        email=user.Email,
        role=user.Role,
        is_ad_user=user.IsADUser,
        is_active=user.IsActive,
        created_at=user.CreatedAt,
        last_login=user.LastLogin
    )


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(
    user_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user (admin only)

    - Cannot delete self
    """
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    user = db.query(User).filter(User.UserId == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Soft delete - just deactivate
    user.IsActive = False
    db.commit()

    return {"message": f"User {user.Username} deactivated successfully"}
