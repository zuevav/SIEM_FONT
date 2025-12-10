"""
Database connection and session management
Supports PostgreSQL (primary) and MS SQL Server (legacy)
"""

from typing import Generator
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from app.config import settings

# ============================================================================
# DATABASE ENGINE
# ============================================================================

# Build connection string
DATABASE_URL = settings.get_database_url()

# Build connect_args based on database type
def _get_connect_args():
    """Get database-specific connection arguments"""
    if settings.database_type.lower() == "postgresql":
        return {
            "connect_timeout": settings.query_timeout_sec,
        }
    else:
        # MS SQL Server
        return {
            "timeout": settings.query_timeout_sec,
            "TrustServerCertificate": settings.mssql_trust_cert,
        }

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle_sec,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    echo=settings.debug_sql,  # Вывод SQL запросов в лог
    connect_args=_get_connect_args(),
    execution_options={
        "isolation_level": "READ COMMITTED"
    }
)

# ============================================================================
# SESSION FACTORY
# ============================================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ============================================================================
# BASE CLASS FOR MODELS
# ============================================================================

Base = declarative_base()

# ============================================================================
# DATABASE DEPENDENCY
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependency для получения сессии БД в FastAPI endpoints

    Usage:
        @app.get("/items/")
        async def read_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# DATABASE UTILITIES
# ============================================================================

def init_db():
    """
    Initialize database - create all tables
    NOTE: В production используйте миграции (Alembic)
    """
    # Import all models here to register them with Base
    # from app.models import user, event, alert  # и т.д.

    Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """
    Check if database connection is working

    Returns:
        bool: True if connection successful
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        print(f"  Connection string: {DATABASE_URL}")
        print(f"  Database type: {settings.database_type}")
        return False


def close_db_connection():
    """Close all database connections"""
    engine.dispose()


# ============================================================================
# EVENT LISTENERS FOR CONNECTION POOLING
# ============================================================================

@event.listens_for(pool.Pool, "connect")
def set_sql_mode(dbapi_conn, connection_record):
    """
    Set SQL mode and parameters when connection is created
    """
    # Можно установить параметры сессии MS SQL
    cursor = dbapi_conn.cursor()
    # cursor.execute("SET NOCOUNT ON;")
    cursor.close()


@event.listens_for(pool.Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """
    Called when connection is retrieved from pool
    Useful for logging/monitoring
    """
    pass


@event.listens_for(pool.Pool, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """
    Called when connection is returned to pool
    """
    pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def execute_stored_procedure(
    db: Session,
    procedure_name: str,
    params: dict = None
) -> list:
    """
    Execute SQL Server stored procedure

    Args:
        db: Database session
        procedure_name: Name of stored procedure (e.g., 'security_events.InsertEventsBatch')
        params: Dictionary of parameter names and values

    Returns:
        list: Result sets from procedure

    Example:
        results = execute_stored_procedure(
            db,
            'security_events.GetDashboardStats',
            {'Hours': 24}
        )
    """
    if params is None:
        params = {}

    # Build EXEC statement
    param_str = ", ".join([f"@{k}=:{k}" for k in params.keys()])
    sql = f"EXEC {procedure_name} {param_str}"

    # Execute
    result = db.execute(sql, params)

    # Fetch all result sets
    results = []
    while True:
        try:
            rows = result.fetchall()
            results.append([dict(row) for row in rows])
            if not result.nextset():
                break
        except Exception:
            break

    return results


def execute_raw_sql(db: Session, sql: str, params: dict = None) -> list:
    """
    Execute raw SQL query

    Args:
        db: Database session
        sql: SQL query
        params: Query parameters

    Returns:
        list: Query results as list of dicts
    """
    if params is None:
        params = {}

    result = db.execute(sql, params)
    rows = result.fetchall()

    return [dict(row) for row in rows]


# ============================================================================
# BULK OPERATIONS
# ============================================================================

def bulk_insert_events(db: Session, events: list) -> dict:
    """
    Bulk insert events using stored procedure

    Args:
        db: Database session
        events: List of event dictionaries

    Returns:
        dict: {inserted_count: int, status: str}
    """
    import json

    # Convert events to JSON
    events_json = json.dumps(events)

    # Call stored procedure
    results = execute_stored_procedure(
        db,
        'security_events.InsertEventsBatch',
        {'Events': events_json}
    )

    if results and len(results) > 0:
        return results[0][0] if results[0] else {'InsertedCount': 0, 'Status': 'error'}

    return {'InsertedCount': 0, 'Status': 'error'}


# ============================================================================
# TRANSACTION HELPERS
# ============================================================================

from contextlib import contextmanager

@contextmanager
def db_transaction(db: Session):
    """
    Context manager for database transactions

    Usage:
        with db_transaction(db):
            db.add(item)
            # автоматический commit при выходе
            # автоматический rollback при ошибке
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


# ============================================================================
# PAGINATION
# ============================================================================

from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar('T')

class Page(BaseModel, Generic[T]):
    """Paginated response"""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


def paginate(
    query,
    page: int = 1,
    size: int = 100
) -> tuple:
    """
    Paginate SQLAlchemy query

    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        size: Items per page

    Returns:
        tuple: (items, total_count)
    """
    # Get total count
    total = query.count()

    # Calculate offset
    offset = (page - 1) * size

    # Get items
    items = query.limit(size).offset(offset).all()

    return items, total


# ============================================================================
# INITIALIZATION
# ============================================================================

# Check connection on module load (only if not testing)
if not settings.testing:
    if check_db_connection():
        print(f"✓ Database connection successful ({settings.database_type})")
    else:
        print("✗ Database connection failed!")
        print(f"  Check .env configuration and {settings.database_type} availability")
