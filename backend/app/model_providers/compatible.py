from __future__ import annotations

import json
import socket
import ssl
import time
import urllib.error
import urllib.request


MAX_TRANSIENT_RETRIES = 3


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        allow_insecure_tls: bool = False,
    ) -> None:
        if not api_key:
            raise RuntimeError("模型 API Key 不能为空")
        if not base_url:
            raise RuntimeError("模型 Base URL 不能为空")
        if not model:
            raise RuntimeError("模型 ID 不能为空")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.allow_insecure_tls = allow_insecure_tls

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        on_retry=None,
    ) -> str:
        endpoint = self._chat_endpoint()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.35,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        data = self._post_chat(endpoint, payload, on_retry=on_retry)
        return _extract_openai_compatible_text(data)

    def _post_chat(self, endpoint: str, payload: dict, attempt: int = 0, on_retry=None) -> dict:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=120,
                context=_ssl_context(self.allow_insecure_tls),
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, socket.timeout) as exc:
            if attempt < MAX_TRANSIENT_RETRIES:
                _notify_retry(on_retry, attempt, "读取超时")
                time.sleep(_retry_delay(attempt))
                return self._post_chat(endpoint, payload, attempt + 1, on_retry=on_retry)
            raise RuntimeError(_format_connection_error(exc)) from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if _requires_temperature_one(detail) and payload.get("temperature") != 1:
                retry_payload = {**payload, "temperature": 1}
                _notify_retry(on_retry, attempt, "温度参数调整为 1")
                return self._post_chat(endpoint, retry_payload, on_retry=on_retry)
            if _is_transient_model_error(detail, exc.code):
                if attempt < MAX_TRANSIENT_RETRIES:
                    _notify_retry(on_retry, attempt, _compact_detail(detail))
                    time.sleep(_retry_delay(attempt))
                    return self._post_chat(endpoint, payload, attempt + 1, on_retry=on_retry)
                raise RuntimeError(
                    f"模型服务繁忙：供应商返回临时过载，已自动重试 {MAX_TRANSIENT_RETRIES} 次仍失败。"
                    f"原始错误：{detail}"
                ) from exc
            raise RuntimeError(f"模型请求失败：{detail}") from exc
        except urllib.error.URLError as exc:
            if _is_transient_connection_reason(exc.reason) and attempt < MAX_TRANSIENT_RETRIES:
                _notify_retry(on_retry, attempt, _connection_retry_reason(exc.reason))
                time.sleep(_retry_delay(attempt))
                return self._post_chat(endpoint, payload, attempt + 1, on_retry=on_retry)
            raise RuntimeError(_format_connection_error(exc.reason)) from exc

    def _chat_endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"


class OpenAIResponsesClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        allow_insecure_tls: bool = False,
    ) -> None:
        if not api_key:
            raise RuntimeError("模型 API Key 不能为空")
        if not base_url:
            raise RuntimeError("模型 Base URL 不能为空")
        if not model:
            raise RuntimeError("模型 ID 不能为空")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.allow_insecure_tls = allow_insecure_tls

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        on_retry=None,
    ) -> str:
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
        }
        if max_tokens:
            payload["max_output_tokens"] = max_tokens
        data = _json_request(
            self._responses_endpoint(),
            payload,
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            allow_insecure_tls=self.allow_insecure_tls,
            on_retry=on_retry,
        )
        if data.get("output_text"):
            return str(data["output_text"]).strip()
        chunks: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    chunks.append(content.get("text", ""))
        if chunks:
            return "\n".join(chunks).strip()
        raise RuntimeError("模型响应中没有可用文本")

    def _responses_endpoint(self) -> str:
        if self.base_url.endswith("/responses"):
            return self.base_url
        return f"{self.base_url}/responses"


class AnthropicMessagesClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        allow_insecure_tls: bool = False,
    ) -> None:
        if not api_key:
            raise RuntimeError("模型 API Key 不能为空")
        if not base_url:
            raise RuntimeError("模型 Base URL 不能为空")
        if not model:
            raise RuntimeError("模型 ID 不能为空")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.allow_insecure_tls = allow_insecure_tls

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        on_retry=None,
    ) -> str:
        payload = {
            "model": self.model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": max_tokens or 4096,
            "temperature": 0.35,
        }
        data = _json_request(
            self._messages_endpoint(),
            payload,
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            allow_insecure_tls=self.allow_insecure_tls,
            on_retry=on_retry,
        )
        chunks = [
            item.get("text", "")
            for item in data.get("content", [])
            if item.get("type") == "text"
        ]
        if chunks:
            return "\n".join(chunks).strip()
        raise RuntimeError("模型响应中没有可用文本")

    def _messages_endpoint(self) -> str:
        if self.base_url.endswith("/messages"):
            return self.base_url
        return f"{self.base_url}/messages"


def _json_request(
    endpoint: str,
    payload: dict,
    headers: dict[str, str],
    *,
    allow_insecure_tls: bool = False,
    attempt: int = 0,
    on_retry=None,
) -> dict:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=120,
            context=_ssl_context(allow_insecure_tls),
        ) as response:
            return json.loads(response.read().decode("utf-8"))
    except (TimeoutError, socket.timeout) as exc:
        if attempt < MAX_TRANSIENT_RETRIES:
            _notify_retry(on_retry, attempt, "读取超时")
            time.sleep(_retry_delay(attempt))
            return _json_request(
                endpoint,
                payload,
                headers,
                allow_insecure_tls=allow_insecure_tls,
                attempt=attempt + 1,
                on_retry=on_retry,
            )
        raise RuntimeError(_format_connection_error(exc)) from exc
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if _is_transient_model_error(detail, exc.code):
            if attempt < MAX_TRANSIENT_RETRIES:
                _notify_retry(on_retry, attempt, _compact_detail(detail))
                time.sleep(_retry_delay(attempt))
                return _json_request(
                    endpoint,
                    payload,
                    headers,
                    allow_insecure_tls=allow_insecure_tls,
                    attempt=attempt + 1,
                    on_retry=on_retry,
                )
            raise RuntimeError(
                f"模型服务繁忙：供应商返回临时过载，已自动重试 {MAX_TRANSIENT_RETRIES} 次仍失败。"
                f"原始错误：{detail}"
            ) from exc
        raise RuntimeError(f"模型请求失败：{detail}") from exc
    except urllib.error.URLError as exc:
        if _is_transient_connection_reason(exc.reason) and attempt < MAX_TRANSIENT_RETRIES:
            _notify_retry(on_retry, attempt, _connection_retry_reason(exc.reason))
            time.sleep(_retry_delay(attempt))
            return _json_request(
                endpoint,
                payload,
                headers,
                allow_insecure_tls=allow_insecure_tls,
                attempt=attempt + 1,
                on_retry=on_retry,
            )
        raise RuntimeError(_format_connection_error(exc.reason)) from exc


def _format_connection_error(reason: object) -> str:
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return (
            f"模型服务读取超时：已自动重试 {MAX_TRANSIENT_RETRIES} 次仍未返回完整响应。"
            "建议减少上传文档、降低讨论轮次，或更换响应更稳定的模型。"
        )
    if _is_connection_reset_reason(reason):
        return (
            f"模型服务连接被远端重置：已自动重试 {MAX_TRANSIENT_RETRIES} 次仍失败。"
            "通常是供应商网关、代理或网络链路临时断开；请稍后重试，或更换入口模型。"
        )
    if isinstance(reason, ssl.SSLCertVerificationError):
        return (
            "无法连接模型服务：TLS 证书校验失败。通常是代理/公司网络使用了自签名证书、"
            "证书链不完整，或 Base URL 被中间层改写。请检查 Base URL、网络代理和系统证书。"
        )
    text = str(reason)
    if "CERTIFICATE_VERIFY_FAILED" in text or "self-signed certificate" in text:
        return (
            "无法连接模型服务：TLS 证书校验失败。通常是代理/公司网络使用了自签名证书、"
            "证书链不完整，或 Base URL 被中间层改写。请检查 Base URL、网络代理和系统证书。"
        )
    if "timed out" in text.lower():
        return (
            f"模型服务读取超时：已自动重试 {MAX_TRANSIENT_RETRIES} 次仍未返回完整响应。"
            "建议减少上传文档、降低讨论轮次，或更换响应更稳定的模型。"
        )
    if "connection reset by peer" in text.lower():
        return (
            f"模型服务连接被远端重置：已自动重试 {MAX_TRANSIENT_RETRIES} 次仍失败。"
            "通常是供应商网关、代理或网络链路临时断开；请稍后重试，或更换入口模型。"
        )
    return f"无法连接模型服务：{text}"


def _extract_openai_compatible_text(data: dict) -> str:
    choices = data.get("choices") or []
    if choices:
        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
    raise RuntimeError("模型响应中没有可用文本")


def _requires_temperature_one(detail: str) -> bool:
    lowered = detail.lower()
    return "invalid temperature" in lowered and "only 1" in lowered


def _is_transient_model_error(detail: str, status_code: int | None = None) -> bool:
    lowered = detail.lower()
    transient_markers = (
        "engine_overloaded_error",
        "overloaded",
        "try again later",
        "temporarily unavailable",
        "rate_limit",
        "rate limit",
    )
    return (status_code in {429, 500, 502, 503, 504}) or any(
        marker in lowered for marker in transient_markers
    )


def _is_timeout_reason(reason: object) -> bool:
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return True
    return "timed out" in str(reason).lower()


def _is_connection_reset_reason(reason: object) -> bool:
    return isinstance(reason, (ConnectionResetError, BrokenPipeError)) or (
        "connection reset by peer" in str(reason).lower()
    )


def _is_transient_connection_reason(reason: object) -> bool:
    return _is_timeout_reason(reason) or _is_connection_reset_reason(reason)


def _connection_retry_reason(reason: object) -> str:
    if _is_timeout_reason(reason):
        return "读取超时"
    if _is_connection_reset_reason(reason):
        return "连接被远端重置"
    return "临时连接错误"


def _retry_delay(attempt: int) -> float:
    return [2.0, 5.0, 10.0][min(attempt, 2)]


def _notify_retry(on_retry, attempt: int, reason: str) -> None:
    if on_retry:
        on_retry(attempt + 1, MAX_TRANSIENT_RETRIES, reason)


def _compact_detail(detail: str) -> str:
    text = " ".join(detail.split())
    return text[:120] + ("..." if len(text) > 120 else "")


def _ssl_context(allow_insecure_tls: bool) -> ssl.SSLContext | None:
    if not allow_insecure_tls:
        return None
    return ssl._create_unverified_context()
