"""
Saved Search Model
Stores user-defined search filters for Events, Alerts, and Incidents
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class SearchType(str, enum.Enum):
    """Type of search (which entity)"""
    EVENTS = "events"
    ALERTS = "alerts"
    INCIDENTS = "incidents"


class SavedSearch(Base):
    """
    Saved Search Model
    Allows users to save filter configurations for quick access
    """
    __tablename__ = "saved_searches"
    __table_args__ = {'schema': 'config'}

    # Primary Key
    saved_search_id = Column('saved_search_id', Integer, primary_key=True, index=True, autoincrement=True)

    # Basic Info
    name = Column('name', String(255), nullable=False, index=True)
    description = Column('description', Text, nullable=True)
    search_type = Column('search_type', Enum(SearchType), nullable=False, index=True)

    # Filter Configuration (stored as JSON)
    filters = Column('filters', Text, nullable=False)  # JSON string with filter parameters

    # Ownership & Sharing
    user_id = Column('user_id', Integer, ForeignKey('config.users.user_id'), nullable=False, index=True)
    is_shared = Column('is_shared', Boolean, default=False, nullable=False, index=True)
    # If is_shared=True, all users can see this search

    # Metadata
    created_at = Column('created_at', DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="saved_searches")

    # Backward compatibility properties
    @property
    def SavedSearchId(self):
        return self.saved_search_id

    @property
    def Name(self):
        return self.name

    @property
    def Description(self):
        return self.description

    @property
    def SearchType(self):
        return self.search_type

    @property
    def Filters(self):
        return self.filters

    @property
    def UserId(self):
        return self.user_id

    @property
    def IsShared(self):
        return self.is_shared

    @property
    def CreatedAt(self):
        return self.created_at

    @property
    def UpdatedAt(self):
        return self.updated_at

    def __repr__(self):
        return f"<SavedSearch(id={self.saved_search_id}, name='{self.name}', type={self.search_type}, user_id={self.user_id})>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        import json

        filters_dict = {}
        if self.filters:
            try:
                filters_dict = json.loads(self.filters)
            except:
                pass

        return {
            "id": self.saved_search_id,
            "name": self.name,
            "description": self.description,
            "search_type": self.search_type.value if self.search_type else None,
            "filters": filters_dict,
            "user_id": self.user_id,
            "is_shared": self.is_shared,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
