from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ProviderError(Exception):
    """Base exception for all provider errors."""

class ProviderRateLimitError(ProviderError):
    pass

class ProviderQuotaError(ProviderError):
    pass

class ProviderTimeoutError(ProviderError):
    pass

class ProviderAuthenticationError(ProviderError):
    pass

class ProviderUnavailableError(ProviderError):
    pass

class ProviderMalformedResponseError(ProviderError):
    pass

class ProviderUnknownError(ProviderError):
    pass

class ModelProvider(ABC):
    """Abstract base class for all LLM design strategy providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'openai', 'ollama')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the model being used (e.g., 'gpt-4o', 'qwen3:8b')."""

    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str, schema: type[BaseModel], max_tokens: int | None = None) -> dict[str, Any]:
        """
        Generate a structured JSON response from the LLM.

        Args:
            system_prompt (str): The system instructions.
            user_prompt (str): The user input/payload.
            schema (Type[BaseModel]): The Pydantic model representing the expected schema.

        Returns:
            Dict[str, Any]: The parsed JSON response matching the schema.

        Raises:
            ProviderError: If generation fails for provider-specific reasons.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the provider is available and properly configured."""
