"""
WebSocket Package
Real-time communication with clients
"""

from app.websocket.manager import ConnectionManager, get_connection_manager
from app.websocket.endpoints import router as websocket_router

__all__ = [
    "ConnectionManager",
    "get_connection_manager",
    "websocket_router",
]
