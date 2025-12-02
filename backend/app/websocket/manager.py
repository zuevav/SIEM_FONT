"""
WebSocket Manager for Real-time Updates
Broadcasts events, alerts, and agent status changes to connected clients
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages
    Supports multiple channels (rooms) for different data types
    """

    def __init__(self):
        # Active connections per channel
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        # User info per connection
        self.connection_users: Dict[WebSocket, Dict[str, Any]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str = "default", user_info: Optional[Dict] = None):
        """
        Connect a client to a channel

        Args:
            websocket: WebSocket connection
            channel: Channel name (e.g., "events", "alerts", "agents")
            user_info: Optional user information (user_id, username, role)
        """
        await websocket.accept()

        async with self._lock:
            self.active_connections[channel].add(websocket)
            if user_info:
                self.connection_users[websocket] = user_info

        logger.info(f"Client connected to channel '{channel}' (total: {len(self.active_connections[channel])})")

        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "status": "connected",
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)

    async def disconnect(self, websocket: WebSocket, channel: str = "default"):
        """
        Disconnect a client from a channel

        Args:
            websocket: WebSocket connection
            channel: Channel name
        """
        async with self._lock:
            self.active_connections[channel].discard(websocket)
            if websocket in self.connection_users:
                del self.connection_users[websocket]

        logger.info(f"Client disconnected from channel '{channel}' (remaining: {len(self.active_connections[channel])})")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """
        Send a message to a specific client

        Args:
            message: Message dictionary
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            # Connection might be broken, will be cleaned up on next broadcast

    async def broadcast(self, message: Dict[str, Any], channel: str = "default"):
        """
        Broadcast a message to all clients in a channel

        Args:
            message: Message dictionary
            channel: Channel name
        """
        if channel not in self.active_connections or not self.active_connections[channel]:
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        disconnected = set()

        for websocket in self.active_connections[channel].copy():
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                disconnected.add(websocket)
                logger.warning(f"WebSocket disconnected during broadcast to channel '{channel}'")
            except Exception as e:
                disconnected.add(websocket)
                logger.error(f"Error broadcasting to websocket in channel '{channel}': {e}")

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                for websocket in disconnected:
                    self.active_connections[channel].discard(websocket)
                    if websocket in self.connection_users:
                        del self.connection_users[websocket]

    async def broadcast_to_multiple_channels(self, message: Dict[str, Any], channels: list):
        """
        Broadcast a message to multiple channels

        Args:
            message: Message dictionary
            channels: List of channel names
        """
        for channel in channels:
            await self.broadcast(message, channel)

    def get_channel_count(self, channel: str = "default") -> int:
        """Get number of active connections in a channel"""
        return len(self.active_connections.get(channel, set()))

    def get_total_connections(self) -> int:
        """Get total number of active connections across all channels"""
        return sum(len(connections) for connections in self.active_connections.values())

    async def broadcast_event(self, event_data: Dict[str, Any]):
        """
        Broadcast a new security event

        Args:
            event_data: Event information
        """
        message = {
            "type": "event",
            "action": "created",
            "data": event_data
        }
        await self.broadcast(message, "events")

    async def broadcast_alert(self, alert_data: Dict[str, Any], action: str = "created"):
        """
        Broadcast an alert (created, updated, resolved)

        Args:
            alert_data: Alert information
            action: Action type (created, updated, acknowledged, resolved)
        """
        message = {
            "type": "alert",
            "action": action,
            "data": alert_data
        }
        await self.broadcast_to_multiple_channels(message, ["alerts", "dashboard"])

    async def broadcast_incident(self, incident_data: Dict[str, Any], action: str = "created"):
        """
        Broadcast an incident (created, updated, closed)

        Args:
            incident_data: Incident information
            action: Action type (created, updated, escalated, closed)
        """
        message = {
            "type": "incident",
            "action": action,
            "data": incident_data
        }
        await self.broadcast_to_multiple_channels(message, ["incidents", "dashboard"])

    async def broadcast_agent_status(self, agent_data: Dict[str, Any], action: str = "updated"):
        """
        Broadcast agent status change

        Args:
            agent_data: Agent information
            action: Action type (registered, online, offline, updated)
        """
        message = {
            "type": "agent",
            "action": action,
            "data": agent_data
        }
        await self.broadcast_to_multiple_channels(message, ["agents", "dashboard"])

    async def broadcast_statistics(self, stats_data: Dict[str, Any]):
        """
        Broadcast dashboard statistics update

        Args:
            stats_data: Statistics information
        """
        message = {
            "type": "statistics",
            "action": "updated",
            "data": stats_data
        }
        await self.broadcast(message, "dashboard")

    async def broadcast_notification(self, notification_data: Dict[str, Any], severity: str = "info"):
        """
        Broadcast a system notification

        Args:
            notification_data: Notification information
            severity: Notification severity (info, warning, error, critical)
        """
        message = {
            "type": "notification",
            "severity": severity,
            "data": notification_data
        }
        # Broadcast to all channels
        for channel in self.active_connections.keys():
            await self.broadcast(message, channel)


# Global connection manager instance
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    return manager
