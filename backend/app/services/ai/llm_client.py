"""
Multi-provider AI service base — every provider in ai_provider_config.py
exposes an OpenAI-compatible chat completions API, so one client shape
(openai.OpenAI with a per-provider base_url) serves all of them.
"""

import os
from abc import ABC

from openai import OpenAI

from backend.app.core.ai_provider_config import (
    AI_REQUEST_TIMEOUT_SECONDS,
    AI_SDK_MAX_RETRIES,
    ServiceModelConfig,
)


class MultiProviderAIService(ABC):

    def __init__(self, config: ServiceModelConfig) -> None:
        api_key = os.getenv(config.connection.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"{config.connection.api_key_env} environment variable not set "
                f"(required for {config.connection.name}/{config.model})"
            )
        self._client = OpenAI(
            base_url=config.connection.base_url,
            api_key=api_key,
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
            max_retries=AI_SDK_MAX_RETRIES,
        )
        self._model = config.model
        self._temperature = config.temperature
        self._top_p = config.top_p
        self._extra_body = config.extra_body

    def _create(self, messages: list[dict], max_tokens: int):
        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": self._temperature,
            "top_p": self._top_p,
            "messages": messages,
        }
        if self._extra_body:
            kwargs["extra_body"] = self._extra_body
        return self._client.chat.completions.create(**kwargs)

    def _call(self, system: str, user: str, max_tokens: int = 2048) -> str:
        response = self._create(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens,
        )
        return response.choices[0].message.content or ""

    def _chat(self, system: str, messages: list[dict], max_tokens: int = 2048) -> str:
        response = self._create(
            [{"role": "system", "content": system}] + messages,
            max_tokens,
        )
        return response.choices[0].message.content or ""
