import json
from typing import Any

import requests
from pydantic import BaseModel

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.providers.base_provider import (
    ModelProvider,
    ProviderMalformedResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnknownError,
)


class OllamaProvider(ModelProvider):
    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return OLLAMA_MODEL

    def health_check(self) -> bool:
        if not OLLAMA_BASE_URL:
            return False
        try:
            # Short timeout for local check
            resp = requests.get(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                # Check if requested model (or its latest tag) is installed
                return any(self.model_name in m for m in models)
            return False
        except requests.RequestException:
            return False

    def generate_json(self, system_prompt: str, user_prompt: str, schema: type[BaseModel], max_tokens: int | None = None) -> dict[str, Any]:
        url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"

        schema_str = json.dumps(schema.model_json_schema())
        system_instruction = f"{system_prompt}\n\nYou must respond ONLY with raw JSON matching this schema exactly: {schema_str}"

        payload = {
            "model": self.model_name,
            "format": "json",
            "options": {
                "temperature": 0.2,
                **({"num_predict": max_tokens} if max_tokens else {})
            },
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }

        try:
            response = requests.post(url, json=payload, timeout=300)
        except requests.exceptions.Timeout:
            raise ProviderTimeoutError("Ollama request timed out. Model may be loading.")
        except requests.exceptions.RequestException as e:
            raise ProviderUnavailableError(f"Ollama network error: {e}")

        if response.status_code != 200:
            data = response.json() if response.text else {}
            if response.status_code >= 500:
                raise ProviderUnavailableError(f"Ollama Server Error: {data}")
            else:
                raise ProviderUnknownError(f"Ollama HTTP {response.status_code}: {data}")

        data = response.json()
        if "message" not in data or "content" not in data["message"]:
            raise ProviderMalformedResponseError("Ollama response missing message content.")

        content = data["message"]["content"]
        try:
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError:
            raise ProviderMalformedResponseError("Ollama returned invalid JSON string.")
