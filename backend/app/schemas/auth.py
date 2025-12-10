"""
Pydantic schemas for Authentication
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """Login request schema"""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=1)

    class Config:
        schema_extra = {
            "example": {
                "username": "admin",
                "password": "Admin123!"
            }
        }


class UserInfo(BaseModel):
    """User information in token response"""
    user_id: int
    username: str
    email: Optional[str]
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserInfo


class PasswordChangeRequest(BaseModel):
    """Password change request"""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)

    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 12:
            raise ValueError('Password must be at least 12 characters long')

        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')

        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')

        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError(f'Password must contain at least one special character')

        return v


class UserCreate(BaseModel):
    """Schema for creating a new user"""
    username: str = Field(..., min_length=3, max_length=100)
    email: Optional[EmailStr]
    password: str = Field(..., min_length=12)
    role: str = Field(default="viewer")
    is_ad_user: bool = False

    @validator('role')
    def validate_role(cls, v):
        """Validate role"""
        allowed_roles = ['admin', 'analyst', 'viewer']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v

    class Config:
        schema_extra = {
            "example": {
                "username": "analyst1",
                "email": "analyst1@company.local",
                "password": "SecurePass123!",
                "role": "analyst"
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating user"""
    email: Optional[EmailStr]
    role: Optional[str]
    is_active: Optional[bool]

    @validator('role')
    def validate_role(cls, v):
        """Validate role"""
        if v is not None:
            allowed_roles = ['admin', 'analyst', 'viewer']
            if v not in allowed_roles:
                raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v


class UserResponse(BaseModel):
    """User response schema"""
    user_id: int
    username: str
    email: Optional[str]
    role: str
    is_ad_user: bool
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        orm_mode = True
        from_attributes = True


class CurrentUser(BaseModel):
    """Current authenticated user"""
    user_id: int
    username: str
    role: str
    is_admin: bool
    is_analyst: bool
    can_write: bool

    class Config:
        orm_mode = True
        from_attributes = True
