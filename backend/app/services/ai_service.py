"""
AI Service Factory
Selects and provides the configured AI provider
"""

import logging
from typing import Optional

from app.config import settings
from app.services.ai_provider import AIServiceProvider
from app.services.yandex_gpt import YandexGPTService
from app.services.deepseek_provider import DeepSeekProvider

logger = logging.getLogger(__name__)


class AIService:
    """
    Factory for AI service providers
    Automatically selects the configured provider
    """

    _instance: Optional[AIServiceProvider] = None

    @classmethod
    def get_provider(cls) -> AIServiceProvider:
        """
        Get the configured AI provider instance (singleton)

        Raises:
            ValueError: If no AI provider is configured or enabled
        """
        if cls._instance is None:
            cls._instance = cls._create_provider()

        return cls._instance

    @classmethod
    def _create_provider(cls) -> AIServiceProvider:
        """
        Create AI provider based on configuration

        Provider selection priority:
        1. deepseek (if enabled)
        2. yandex_gpt (if enabled)
        3. Raise error if none enabled
        """
        provider_name = settings.ai_provider.lower()

        logger.info(f"Initializing AI provider: {provider_name}")

        if provider_name == "deepseek":
            provider = DeepSeekProvider()
            if provider.is_enabled():
                logger.info("✓ DeepSeek AI provider initialized")
                return provider
            else:
                logger.warning("DeepSeek is selected but not configured properly")

        elif provider_name == "yandex_gpt":
            provider = YandexGPTService()
            if provider.is_enabled():
                logger.info("✓ Yandex GPT AI provider initialized")
                return provider
            else:
                logger.warning("Yandex GPT is selected but not configured properly")

        # Fallback: try to find any enabled provider
        logger.warning(f"Provider '{provider_name}' not available, trying fallback...")

        # Try DeepSeek first (free)
        deepseek = DeepSeekProvider()
        if deepseek.is_enabled():
            logger.info("✓ Using DeepSeek AI provider (fallback)")
            return deepseek

        # Try Yandex GPT
        yandex = YandexGPTService()
        if yandex.is_enabled():
            logger.info("✓ Using Yandex GPT AI provider (fallback)")
            return yandex

        # No provider available
        raise ValueError(
            "No AI provider is configured and enabled. "
            "Please configure at least one of: deepseek, yandex_gpt"
        )

    @classmethod
    def is_available(cls) -> bool:
        """Check if any AI provider is available"""
        try:
            provider = cls.get_provider()
            return provider.is_enabled()
        except ValueError:
            return False


# Convenience function
def get_ai_service() -> AIServiceProvider:
    """
    Get the configured AI service provider

    Returns:
        AIServiceProvider instance

    Raises:
        ValueError: If no AI provider is configured
    """
    return AIService.get_provider()
