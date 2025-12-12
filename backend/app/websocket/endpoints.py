"""
WebSocket API Endpoints
Real-time communication with frontend clients
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from fastapi.exceptions import WebSocketException
from jose import jwt, JWTError
from typing import Optional
import logging

from app.websocket.manager import get_connection_manager
from app.core.security import decode_access_token
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_websocket_user(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    Authenticate WebSocket connection via JWT token

    Args:
        websocket: WebSocket connection
        token: JWT token from query parameter

    Returns:
        User information dict

    Raises:
        WebSocketException: If authentication fails
    """
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token required")

    try:
        # Decode JWT token
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
        username = payload.get("username", "unknown")
        role = payload.get("role", "viewer")

        return {
            "user_id": user_id,
            "username": username,
            "role": role
        }

    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")


@router.websocket("/events")
async def websocket_events(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time security events
    Sends new events as they are created

    Query Parameters:
        token: JWT authentication token

    Message Format:
        {
            "type": "event",
            "action": "created",
            "data": {...event data...},
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    manager = get_connection_manager()

    try:
        # Authenticate user
        user_info = await get_websocket_user(websocket, token)
        logger.info(f"User {user_info['username']} connecting to events channel")

        # Connect to events channel
        await manager.connect(websocket, "events", user_info)

        try:
            # Keep connection alive and handle incoming messages
            while True:
                # Wait for messages from client (ping/pong, etc.)
                data = await websocket.receive_text()

                # Handle ping
                if data == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)

        except WebSocketDisconnect:
            logger.info(f"User {user_info['username']} disconnected from events channel")
        finally:
            await manager.disconnect(websocket, "events")

    except WebSocketException as e:
        logger.warning(f"WebSocket connection rejected: {e.reason}")
        await websocket.close(code=e.code, reason=e.reason)


@router.websocket("/alerts")
async def websocket_alerts(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time alerts
    Sends alert updates (created, acknowledged, resolved)

    Message Format:
        {
            "type": "alert",
            "action": "created|acknowledged|resolved",
            "data": {...alert data...},
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    manager = get_connection_manager()

    try:
        user_info = await get_websocket_user(websocket, token)
        logger.info(f"User {user_info['username']} connecting to alerts channel")

        await manager.connect(websocket, "alerts", user_info)

        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)

        except WebSocketDisconnect:
            logger.info(f"User {user_info['username']} disconnected from alerts channel")
        finally:
            await manager.disconnect(websocket, "alerts")

    except WebSocketException as e:
        logger.warning(f"WebSocket connection rejected: {e.reason}")
        await websocket.close(code=e.code, reason=e.reason)


@router.websocket("/incidents")
async def websocket_incidents(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time incidents
    Sends incident updates (created, escalated, closed)

    Message Format:
        {
            "type": "incident",
            "action": "created|updated|escalated|closed",
            "data": {...incident data...},
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    manager = get_connection_manager()

    try:
        user_info = await get_websocket_user(websocket, token)
        logger.info(f"User {user_info['username']} connecting to incidents channel")

        await manager.connect(websocket, "incidents", user_info)

        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)

        except WebSocketDisconnect:
            logger.info(f"User {user_info['username']} disconnected from incidents channel")
        finally:
            await manager.disconnect(websocket, "incidents")

    except WebSocketException as e:
        logger.warning(f"WebSocket connection rejected: {e.reason}")
        await websocket.close(code=e.code, reason=e.reason)


@router.websocket("/agents")
async def websocket_agents(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time agent status
    Sends agent status changes (online, offline, registered)

    Message Format:
        {
            "type": "agent",
            "action": "registered|online|offline|updated",
            "data": {...agent data...},
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    manager = get_connection_manager()

    try:
        user_info = await get_websocket_user(websocket, token)
        logger.info(f"User {user_info['username']} connecting to agents channel")

        await manager.connect(websocket, "agents", user_info)

        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)

        except WebSocketDisconnect:
            logger.info(f"User {user_info['username']} disconnected from agents channel")
        finally:
            await manager.disconnect(websocket, "agents")

    except WebSocketException as e:
        logger.warning(f"WebSocket connection rejected: {e.reason}")
        await websocket.close(code=e.code, reason=e.reason)


@router.websocket("/dashboard")
async def websocket_dashboard(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for dashboard real-time updates
    Sends combined updates (events, alerts, incidents, statistics)

    Message Types:
        - "alert" - New or updated alert
        - "incident" - New or updated incident
        - "agent" - Agent status change
        - "statistics" - Updated statistics
        - "notification" - System notification
    """
    manager = get_connection_manager()

    try:
        user_info = await get_websocket_user(websocket, token)
        logger.info(f"User {user_info['username']} connecting to dashboard channel")

        await manager.connect(websocket, "dashboard", user_info)

        # Send initial statistics
        await manager.send_personal_message({
            "type": "connection",
            "message": "Connected to dashboard channel",
            "user": user_info["username"]
        }, websocket)

        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)

        except WebSocketDisconnect:
            logger.info(f"User {user_info['username']} disconnected from dashboard channel")
        finally:
            await manager.disconnect(websocket, "dashboard")

    except WebSocketException as e:
        logger.warning(f"WebSocket connection rejected: {e.reason}")
        await websocket.close(code=e.code, reason=e.reason)


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for system notifications
    Sends system-wide notifications and alerts

    Message Format:
        {
            "type": "notification",
            "severity": "info|warning|error|critical",
            "data": {...notification data...},
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    manager = get_connection_manager()

    try:
        user_info = await get_websocket_user(websocket, token)
        logger.info(f"User {user_info['username']} connecting to notifications channel")

        await manager.connect(websocket, "notifications", user_info)

        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)

        except WebSocketDisconnect:
            logger.info(f"User {user_info['username']} disconnected from notifications channel")
        finally:
            await manager.disconnect(websocket, "notifications")

    except WebSocketException as e:
        logger.warning(f"WebSocket connection rejected: {e.reason}")
        await websocket.close(code=e.code, reason=e.reason)


@router.websocket("/system/update/stream")
async def websocket_system_update(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for system update progress
    Sends real-time update progress during system updates

    Message Format:
        {
            "type": "progress|log|error|complete",
            "progress": 0-100,
            "message": "Update message...",
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    manager = get_connection_manager()

    try:
        user_info = await get_websocket_user(websocket, token)

        # Only admin can watch update progress
        if user_info.get("role") != "admin":
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Admin access required")

        logger.info(f"User {user_info['username']} connecting to system update channel")

        await manager.connect(websocket, "system_update", user_info)

        # Send initial connection message
        await manager.send_personal_message({
            "type": "connected",
            "message": "Connected to system update channel"
        }, websocket)

        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)

        except WebSocketDisconnect:
            logger.info(f"User {user_info['username']} disconnected from system update channel")
        finally:
            await manager.disconnect(websocket, "system_update")

    except WebSocketException as e:
        logger.warning(f"WebSocket connection rejected: {e.reason}")
        await websocket.close(code=e.code, reason=e.reason)
