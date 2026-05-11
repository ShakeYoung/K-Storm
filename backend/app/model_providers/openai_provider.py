from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from app.model_providers.base import ModelProvider


class OpenAIProvider(ModelProvider):
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required when KS_MODEL_PROVIDER=openai")

    def generate(
        self,
        *,
        agent_key: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        on_retry=None,
    ) -> str:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
        }
        if max_tokens:
            payload["max_output_tokens"] = max_tokens
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI request failed: {detail}") from exc

        text_chunks: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text_chunks.append(content.get("text", ""))
        if not text_chunks:
            raise RuntimeError("OpenAI response did not contain output_text")
        return "\n".join(text_chunks).strip()
