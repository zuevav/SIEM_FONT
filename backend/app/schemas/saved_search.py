"""
Pydantic schemas for Saved Searches
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class SearchType(str, Enum):
    """Search type enum"""
    EVENTS = "events"
    ALERTS = "alerts"
    INCIDENTS = "incidents"


class SavedSearchCreate(BaseModel):
    """Schema for creating a saved search"""
    name: str = Field(..., min_length=1, max_length=255, description="Search name")
    description: Optional[str] = Field(None, description="Search description")
    search_type: SearchType = Field(..., description="Type of search (events/alerts/incidents)")
    filters: Dict[str, Any] = Field(..., description="Filter parameters as dict")
    is_shared: bool = Field(default=False, description="Share with all users")

    class Config:
        schema_extra = {
            "example": {
                "name": "Critical Windows Events",
                "description": "All critical security events from Windows hosts",
                "search_type": "events",
                "filters": {
                    "source_type": "windows",
                    "severity": 4,
                    "event_code": [4625, 4624]
                },
                "is_shared": True
            }
        }


class SavedSearchUpdate(BaseModel):
    """Schema for updating a saved search"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    search_type: Optional[SearchType] = None
    filters: Optional[Dict[str, Any]] = None
    is_shared: Optional[bool] = None

    class Config:
        schema_extra = {
            "example": {
                "name": "Updated Search Name",
                "is_shared": True
            }
        }


class SavedSearchResponse(BaseModel):
    """Schema for saved search response"""
    id: int = Field(..., description="Saved search ID")
    name: str = Field(..., description="Search name")
    description: Optional[str] = Field(None, description="Search description")
    search_type: str = Field(..., description="Type of search")
    filters: Dict[str, Any] = Field(..., description="Filter parameters")
    user_id: int = Field(..., description="Owner user ID")
    is_shared: bool = Field(..., description="Shared with all users")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "name": "Critical Windows Events",
                "description": "All critical security events from Windows hosts",
                "search_type": "events",
                "filters": {
                    "source_type": "windows",
                    "severity": 4
                },
                "user_id": 1,
                "is_shared": True,
                "created_at": "2024-12-06T10:00:00",
                "updated_at": "2024-12-06T10:00:00"
            }
        }

    @classmethod
    def from_orm(cls, obj):
        """Convert SQLAlchemy object to Pydantic model"""
        return cls(**obj.to_dict())


class SavedSearchDetail(SavedSearchResponse):
    """Detailed saved search with additional info"""
    username: Optional[str] = Field(None, description="Owner username")

    class Config:
        orm_mode = True


class SavedSearchList(BaseModel):
    """List of saved searches"""
    total: int = Field(..., description="Total number of searches")
    items: list[SavedSearchResponse] = Field(..., description="List of searches")

    class Config:
        schema_extra = {
            "example": {
                "total": 2,
                "items": [
                    {
                        "id": 1,
                        "name": "Critical Windows Events",
                        "search_type": "events",
                        "filters": {"severity": 4},
                        "user_id": 1,
                        "is_shared": True,
                        "created_at": "2024-12-06T10:00:00",
                        "updated_at": "2024-12-06T10:00:00"
                    }
                ]
            }
        }
