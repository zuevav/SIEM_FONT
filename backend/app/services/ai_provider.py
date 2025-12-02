"""
Base AI Service Provider Interface
Abstract class for AI providers (Yandex GPT, DeepSeek, OpenAI, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class AIServiceProvider(ABC):
    """
    Abstract base class for AI service providers
    All AI providers must implement these methods
    """

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if this AI provider is configured and enabled"""
        pass

    @abstractmethod
    async def analyze_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a security event and classify it

        Args:
            event_data: Dictionary with event information

        Returns:
            {
                "ai_processed": bool,
                "ai_is_attack": bool,
                "ai_score": float (0-100),
                "ai_category": str,
                "ai_description": str,
                "ai_confidence": float (0-100)
            }
        """
        pass

    @abstractmethod
    async def analyze_alert(self, alert_data: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze an alert and provide recommendations

        Args:
            alert_data: Dictionary with alert information
            events: List of related events

        Returns:
            {
                "ai_analysis": dict,
                "ai_recommendations": str,
                "ai_confidence": float
            }
        """
        pass

    @abstractmethod
    async def analyze_incident(
        self,
        incident_data: Dict[str, Any],
        alerts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze an incident and provide comprehensive assessment

        Args:
            incident_data: Dictionary with incident information
            alerts: List of related alerts

        Returns:
            {
                "ai_summary": str,
                "ai_timeline": dict,
                "ai_root_cause": str,
                "ai_impact_assessment": str,
                "ai_recommendations": str
            }
        """
        pass

    @abstractmethod
    async def generate_cbr_report(self, incident_data: Dict[str, Any]) -> str:
        """
        Generate incident report in format suitable for CBR (Central Bank of Russia)

        Args:
            incident_data: Dictionary with incident information

        Returns:
            Formatted report text in Russian
        """
        pass

    def get_provider_name(self) -> str:
        """Get the name of this AI provider"""
        return self.__class__.__name__
