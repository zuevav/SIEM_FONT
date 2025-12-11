"""
Saved Searches API Endpoints
Handles saving and loading search filters for Events, Alerts, and Incidents
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
import json
import logging

from app.api.deps import get_db, get_current_user
from app.schemas.saved_search import (
    SavedSearchCreate,
    SavedSearchUpdate,
    SavedSearchResponse,
    SavedSearchDetail,
    SavedSearchList
)
from app.schemas.auth import CurrentUser
from app.models.saved_search import SavedSearch, SearchType
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# SAVED SEARCHES CRUD
# ============================================================================

@router.get("", response_model=SavedSearchList)
async def list_saved_searches(
    search_type: Optional[SearchType] = Query(None, description="Filter by search type"),
    include_shared: bool = Query(True, description="Include shared searches"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get all saved searches for current user
    Returns user's own searches + shared searches (if include_shared=True)
    """
    try:
        # Build query
        query = db.query(SavedSearch)

        # Filter by search type if specified
        # FIX BUG-008: Use snake_case column name (search_type), not @property (SearchType)
        if search_type:
            query = query.filter(SavedSearch.search_type == search_type)

        # Filter: user's own searches OR shared searches
        # FIX BUG-008: Use snake_case column names for SQLAlchemy queries
        if include_shared:
            query = query.filter(
                or_(
                    SavedSearch.user_id == current_user.user_id,
                    SavedSearch.is_shared == True
                )
            )
        else:
            query = query.filter(SavedSearch.user_id == current_user.user_id)

        # Order by created date descending
        query = query.order_by(SavedSearch.created_at.desc())

        searches = query.all()

        return SavedSearchList(
            total=len(searches),
            items=[SavedSearchResponse.from_orm(s) for s in searches]
        )

    except Exception as e:
        logger.error(f"Error listing saved searches: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve saved searches"
        )


@router.get("/{search_id}", response_model=SavedSearchDetail)
async def get_saved_search(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get a specific saved search by ID
    User must own the search or it must be shared
    """
    try:
        # FIX BUG-008: Use snake_case column names for SQLAlchemy queries
        search = db.query(SavedSearch).filter(SavedSearch.saved_search_id == search_id).first()

        if not search:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Saved search with ID {search_id} not found"
            )

        # Check permissions: must be owner or search must be shared
        if search.user_id != current_user.user_id and not search.is_shared:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this saved search"
            )

        # Get owner username (User model uses PascalCase - it has @property aliases)
        owner = db.query(User).filter(User.UserId == search.user_id).first()
        username = owner.Username if owner else None

        search_dict = search.to_dict()
        search_dict['username'] = username

        return SavedSearchDetail(**search_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting saved search {search_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve saved search"
        )


@router.post("", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_search(
    search: SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Create a new saved search
    """
    try:
        # Check if search with same name already exists for this user
        # FIX BUG-008: Use snake_case column names for SQLAlchemy queries
        existing = db.query(SavedSearch).filter(
            and_(
                SavedSearch.name == search.name,
                SavedSearch.user_id == current_user.user_id
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You already have a saved search named '{search.name}'"
            )

        # Convert filters dict to JSON string
        filters_json = json.dumps(search.filters)

        # Create new saved search using snake_case attributes
        new_search = SavedSearch(
            name=search.name,
            description=search.description,
            search_type=search.search_type,
            filters=filters_json,
            user_id=current_user.user_id,
            is_shared=search.is_shared
        )

        db.add(new_search)
        db.commit()
        db.refresh(new_search)

        logger.info(f"Saved search '{new_search.name}' created by user {current_user.username}")

        return SavedSearchResponse.from_orm(new_search)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating saved search: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create saved search"
        )


@router.put("/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: int,
    search_update: SavedSearchUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Update a saved search
    Only the owner can update the search
    """
    try:
        # FIX BUG-008: Use snake_case column names for SQLAlchemy queries
        search = db.query(SavedSearch).filter(SavedSearch.saved_search_id == search_id).first()

        if not search:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Saved search with ID {search_id} not found"
            )

        # Check permissions: must be owner
        if search.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own saved searches"
            )

        # Update fields using snake_case attributes
        if search_update.name is not None:
            # Check for name conflict (excluding current search)
            existing = db.query(SavedSearch).filter(
                and_(
                    SavedSearch.name == search_update.name,
                    SavedSearch.user_id == current_user.user_id,
                    SavedSearch.saved_search_id != search_id
                )
            ).first()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"You already have a saved search named '{search_update.name}'"
                )

            search.name = search_update.name

        if search_update.description is not None:
            search.description = search_update.description

        if search_update.search_type is not None:
            search.search_type = search_update.search_type

        if search_update.filters is not None:
            search.filters = json.dumps(search_update.filters)

        if search_update.is_shared is not None:
            search.is_shared = search_update.is_shared

        db.commit()
        db.refresh(search)

        logger.info(f"Saved search '{search.name}' (ID: {search_id}) updated by user {current_user.username}")

        return SavedSearchResponse.from_orm(search)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating saved search {search_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update saved search"
        )


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Delete a saved search
    Only the owner can delete the search
    """
    try:
        # FIX BUG-008: Use snake_case column names for SQLAlchemy queries
        search = db.query(SavedSearch).filter(SavedSearch.saved_search_id == search_id).first()

        if not search:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Saved search with ID {search_id} not found"
            )

        # Check permissions: must be owner
        if search.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own saved searches"
            )

        search_name = search.name
        db.delete(search)
        db.commit()

        logger.info(f"Saved search '{search_name}' (ID: {search_id}) deleted by user {current_user.username}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting saved search {search_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete saved search"
        )
