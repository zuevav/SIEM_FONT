"""
Database module re-export for backwards compatibility.
Actual implementation is in app.database
"""

from app.database import (
    Base,
    engine,
    SessionLocal,
    get_db,
    init_db,
    check_db_connection,
    close_db_connection,
    db_transaction,
    paginate,
    Page,
)

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "check_db_connection",
    "close_db_connection",
    "db_transaction",
    "paginate",
    "Page",
]
