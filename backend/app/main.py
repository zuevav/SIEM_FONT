"""
SIEM Backend API - Main Application
FastAPI application with REST API and WebSocket support
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
import logging

from app.config import settings
from app.database import engine, check_db_connection, close_db_connection
from app.tasks import get_ai_analyzer_task, get_dashboard_updater_task

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Runs on startup and shutdown
    """
    # Startup
    logger.info("=" * 70)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info("=" * 70)

    # Check database connection
    logger.info("Checking database connection...")
    if check_db_connection():
        logger.info("✓ Database connection successful")
    else:
        logger.error("✗ Database connection failed!")
        logger.warning("API will start but database operations will fail")

    # Log configuration
    logger.info(f"Database: {settings.mssql_server}/{settings.mssql_database}")
    logger.info(f"CORS origins: {settings.cors_origins_list}")
    logger.info(f"AI Provider: {settings.ai_provider}")
    logger.info(f"Email notifications: {'Enabled' if settings.email_enabled else 'Disabled'}")

    # Start background tasks
    logger.info("Starting background tasks...")
    try:
        ai_analyzer = get_ai_analyzer_task()
        await ai_analyzer.start()

        dashboard_updater = get_dashboard_updater_task()
        await dashboard_updater.start()

        logger.info("✓ Background tasks started")
    except Exception as e:
        logger.warning(f"Some background tasks failed to start: {e}")

    logger.info("Application started successfully")
    logger.info("=" * 70)

    yield  # Application runs here

    # Shutdown
    logger.info("=" * 70)
    logger.info("Shutting down application...")

    # Stop background tasks
    try:
        ai_analyzer = get_ai_analyzer_task()
        await ai_analyzer.stop()

        dashboard_updater = get_dashboard_updater_task()
        await dashboard_updater.stop()

        logger.info("✓ Background tasks stopped")
    except Exception as e:
        logger.error(f"Error stopping background tasks: {e}")

    close_db_connection()
    logger.info("✓ Application shutdown complete")
    logger.info("=" * 70)


# ============================================================================
# CREATE APPLICATION
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    description="Security Information and Event Management (SIEM) System",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else "An error occurred"
        },
    )


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "status": "running",
        "docs_url": "/docs" if settings.debug else None,
        "api_prefix": "/api/v1"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    Returns system status and database connectivity
    """
    db_status = "healthy"
    try:
        if not check_db_connection():
            db_status = "unhealthy"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "database": db_status,
        "timestamp": time.time()
    }


@app.get("/info", tags=["Info"])
async def get_info():
    """
    Get system information and configuration (non-sensitive)
    """
    return {
        "application": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
        },
        "features": {
            "ai_analysis": settings.yandex_gpt_enabled,
            "email_notifications": settings.email_enabled,
            "telegram_notifications": settings.telegram_enabled,
            "ad_integration": settings.ad_enabled,
            "cbr_reporting": settings.cbr_reporting_enabled,
        },
        "database": {
            "server": settings.mssql_server,
            "database": settings.mssql_database,
        },
        "limits": {
            "max_events_per_query": settings.max_events_per_query,
            "event_batch_size": settings.event_batch_size,
            "query_timeout_sec": settings.query_timeout_sec,
        },
        "retention": {
            "events_days": settings.retention_days,
            "alerts_days": settings.retention_alerts_days,
            "audit_days": settings.retention_audit_days,
        }
    }


# ============================================================================
# API ROUTES
# ============================================================================

# Import API routers
from app.api.v1 import auth, events, agents, alerts, incidents
from app.websocket import websocket_router

# Authentication router
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

# Events router
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])

# Agents router
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])

# Alerts router
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])

# Incidents router
app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["Incidents"])

# WebSocket router
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])

logger.info("API routers loaded successfully")
logger.info("WebSocket endpoints available at /ws/*")

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
        access_log=True
    )
