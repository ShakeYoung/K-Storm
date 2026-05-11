from __future__ import annotations

import os

from app.model_providers.base import ModelProvider
from app.model_providers.mock import MockModelProvider
from app.model_providers.openai_provider import OpenAIProvider
from app.model_providers.router import AgentModelRouter
from app.schemas.models import AgentModelSettings


def get_model_provider(settings: AgentModelSettings | None = None) -> ModelProvider:
    if settings and settings.providers:
        return AgentModelRouter(settings, fallback=MockModelProvider())

    provider = os.getenv("KS_MODEL_PROVIDER", "mock").lower()
    if provider == "openai":
        return OpenAIProvider()
    return MockModelProvider()
