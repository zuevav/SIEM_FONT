"""
Business logic services
Email notifications, FreeScout integration, Threat Intelligence, etc.
"""

from app.services.ai_service import AIService, get_ai_service

__all__ = [
    "AIService",
    "get_ai_service",
]
