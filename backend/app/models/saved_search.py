"""
Saved Search Model
Stores user-defined search filters for Events, Alerts, and Incidents
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


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
    SavedSearchId = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Basic Info
    Name = Column(String(255), nullable=False, index=True)
    Description = Column(Text, nullable=True)
    SearchType = Column(Enum(SearchType), nullable=False, index=True)

    # Filter Configuration (stored as JSON)
    Filters = Column(Text, nullable=False)  # JSON string with filter parameters

    # Ownership & Sharing
    UserId = Column(Integer, ForeignKey('users.UserId'), nullable=False, index=True)
    IsShared = Column(Boolean, default=False, nullable=False, index=True)
    # If IsShared=True, all users can see this search

    # Metadata
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)
    UpdatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="saved_searches")

    def __repr__(self):
        return f"<SavedSearch(id={self.SavedSearchId}, name='{self.Name}', type={self.SearchType}, user_id={self.UserId})>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        import json

        filters = {}
        if self.Filters:
            try:
                filters = json.loads(self.Filters)
            except:
                pass

        return {
            "id": self.SavedSearchId,
            "name": self.Name,
            "description": self.Description,
            "search_type": self.SearchType.value if self.SearchType else None,
            "filters": filters,
            "user_id": self.UserId,
            "is_shared": self.IsShared,
            "created_at": self.CreatedAt.isoformat() if self.CreatedAt else None,
            "updated_at": self.UpdatedAt.isoformat() if self.UpdatedAt else None,
        }
