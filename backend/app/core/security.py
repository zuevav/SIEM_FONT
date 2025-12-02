"""
Security utilities: JWT, password hashing, authentication
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# PASSWORD HASHING
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password

    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password against policy

    Args:
        password: Password to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < settings.password_min_length:
        return False, f"Password must be at least {settings.password_min_length} characters long"

    if settings.password_require_uppercase and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if settings.password_require_lowercase and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if settings.password_require_digits and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    if settings.password_require_special:
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, f"Password must contain at least one special character: {special_chars}"

    return True, None


# ============================================================================
# JWT TOKEN
# ============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token

    Args:
        data: Data to encode in token
        expires_delta: Token expiration time

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify JWT token

    Args:
        token: JWT token string

    Returns:
        dict: Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def create_session_token(user_id: int, username: str) -> str:
    """
    Create session token for user

    Args:
        user_id: User ID
        username: Username

    Returns:
        str: JWT token
    """
    token_data = {
        "sub": str(user_id),
        "username": username,
        "type": "access"
    }

    return create_access_token(token_data)


# ============================================================================
# PERMISSION CHECKING
# ============================================================================

def check_permission(user_role: str, required_role: str) -> bool:
    """
    Check if user has required permission level

    Permission hierarchy: viewer < analyst < admin

    Args:
        user_role: User's role
        required_role: Required role level

    Returns:
        bool: True if user has permission
    """
    role_hierarchy = {
        'viewer': 1,
        'analyst': 2,
        'admin': 3
    }

    user_level = role_hierarchy.get(user_role, 0)
    required_level = role_hierarchy.get(required_role, 99)

    return user_level >= required_level


def can_write(user_role: str) -> bool:
    """Check if user can write data"""
    return user_role in ('admin', 'analyst')


def can_manage_users(user_role: str) -> bool:
    """Check if user can manage other users"""
    return user_role == 'admin'


def can_manage_rules(user_role: str) -> bool:
    """Check if user can manage detection rules"""
    return user_role in ('admin', 'analyst')


# ============================================================================
# AUDIT UTILITIES
# ============================================================================

def get_client_ip(request) -> str:
    """
    Get client IP address from request

    Args:
        request: FastAPI request object

    Returns:
        str: Client IP address
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"


def get_user_agent(request) -> str:
    """
    Get user agent from request

    Args:
        request: FastAPI request object

    Returns:
        str: User agent string
    """
    return request.headers.get("User-Agent", "unknown")


# ============================================================================
# API KEY GENERATION (for agents)
# ============================================================================

import secrets


def generate_api_key(length: int = 32) -> str:
    """
    Generate secure random API key

    Args:
        length: Key length

    Returns:
        str: Random API key
    """
    return secrets.token_urlsafe(length)


def generate_agent_id() -> str:
    """
    Generate unique agent ID (GUID)

    Returns:
        str: GUID string
    """
    import uuid
    return str(uuid.uuid4())
