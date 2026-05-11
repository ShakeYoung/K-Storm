from __future__ import annotations

from dataclasses import dataclass

from app.model_providers.base import ModelProvider
from app.model_providers.compatible import (
    AnthropicMessagesClient,
    OpenAICompatibleClient,
    OpenAIResponsesClient,
)
from app.model_providers.mock import MockModelProvider
from app.schemas.models import AgentModelSettings, UserModel, UserModelProvider


@dataclass(frozen=True)
class ResolvedModel:
    provider: UserModelProvider
    model: UserModel


class AgentModelRouter(ModelProvider):
    def __init__(self, settings: AgentModelSettings | None, fallback: ModelProvider | None = None) -> None:
        self.settings = settings or AgentModelSettings()
        self.fallback = fallback or MockModelProvider()
        self._resolved = self._resolve_assignments()

    def generate(
        self,
        *,
        agent_key: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        on_retry=None,
    ) -> str:
        resolved = self._resolved.get(agent_key)
        if resolved is None:
            return self.fallback.generate(
                agent_key=agent_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                on_retry=on_retry,
            )
        client = self._client_for(resolved)
        return client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            on_retry=on_retry,
        )

    def label_for(self, agent_key: str) -> str:
        resolved = self._resolved.get(agent_key)
        if resolved is None:
            return self.fallback.label_for(agent_key)
        return f"{resolved.provider.name} / {resolved.model.name}"

    def _resolve_assignments(self) -> dict[str, ResolvedModel]:
        providers = {provider.id: provider for provider in self.settings.providers}
        resolved: dict[str, ResolvedModel] = {}
        for agent_key, ref in self.settings.assignments.items():
            if not ref or ":" not in ref:
                continue
            provider_id, model_id = ref.split(":", 1)
            provider = providers.get(provider_id)
            if provider is None:
                continue
            model = next((item for item in provider.models if item.id == model_id), None)
            if model is None:
                continue
            resolved[agent_key] = ResolvedModel(provider=provider, model=model)
        return resolved

    def _client_for(self, resolved: ResolvedModel):
        kwargs = {
            "api_key": resolved.provider.api_key,
            "base_url": resolved.provider.base_url,
            "model": resolved.model.model,
            "allow_insecure_tls": resolved.provider.allow_insecure_tls,
        }
        if resolved.provider.api_type == "openai_compatible":
            return OpenAICompatibleClient(**kwargs)
        if resolved.provider.api_type == "openai_responses":
            return OpenAIResponsesClient(**kwargs)
        if resolved.provider.api_type == "anthropic_messages":
            return AnthropicMessagesClient(**kwargs)
        raise RuntimeError(f"暂不支持的 API 类型：{resolved.provider.api_type}")
