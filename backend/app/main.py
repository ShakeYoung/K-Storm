from __future__ import annotations

from pathlib import Path
import json
import ssl
import urllib.error
import urllib.request

from fastapi import BackgroundTasks, Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.model_providers.factory import get_model_provider
from app.orchestrator.runner import cancel_run, create_run_record, execute_memory_query, execute_run_safe, rerun, resume_run_safe
from app.schemas.models import (
    HistoryDeleteRequest,
    HistoryItem,
    MemoryQueryRequest,
    MemoryQueryResponse,
    RunCreate,
    RunRecord,
    RunResumeRequest,
    UserModelProvider,
)
from app.storage import db


app = FastAPI(title="K-Storm API", version="0.1.0")

KNOWN_MODEL_PRESETS = {
    "kimi-coding": [
        {"id": "kimi-for-coding", "name": "kimi-for-coding", "model": "kimi-for-coding"},
    ],
    "bailian-coding": [
        {"id": "qwen3.5-plus", "name": "qwen3.5-plus", "model": "qwen3.5-plus"},
        {"id": "kimi-k2.5", "name": "kimi-k2.5", "model": "kimi-k2.5"},
        {"id": "glm-5", "name": "glm-5", "model": "glm-5"},
        {"id": "MiniMax-M2.5", "name": "MiniMax-M2.5", "model": "MiniMax-M2.5"},
        {"id": "qwen3-coder-plus", "name": "qwen3-coder-plus", "model": "qwen3-coder-plus"},
        {"id": "qwen3-coder-next", "name": "qwen3-coder-next", "model": "qwen3-coder-next"},
        {"id": "glm-4.7", "name": "glm-4.7", "model": "glm-4.7"},
    ],
    "volcengine-coding": [
        {"id": "ark-code-latest", "name": "ark-code-latest", "model": "ark-code-latest"},
        {"id": "doubao-seed-2.0-code", "name": "doubao-seed-2.0-code", "model": "doubao-seed-2.0-code"},
        {"id": "doubao-seed-2.0-pro", "name": "doubao-seed-2.0-pro", "model": "doubao-seed-2.0-pro"},
        {"id": "doubao-seed-2.0-lite", "name": "doubao-seed-2.0-lite", "model": "doubao-seed-2.0-lite"},
        {"id": "deepseek-v3.2", "name": "deepseek-v3.2", "model": "deepseek-v3.2"},
        {"id": "kimi-k2.5", "name": "kimi-k2.5", "model": "kimi-k2.5"},
        {"id": "minimax-m2.5", "name": "minimax-m2.5", "model": "minimax-m2.5"},
        {"id": "glm-4.7", "name": "glm-4.7", "model": "glm-4.7"},
    ],
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup() -> None:
    db.init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/models/discover")
def discover_models(provider: UserModelProvider) -> dict[str, list[dict[str, str]]]:
    if provider.id in KNOWN_MODEL_PRESETS:
        return {"models": KNOWN_MODEL_PRESETS[provider.id]}

    if provider.api_type not in {"openai_compatible", "openai_responses", "anthropic_messages"}:
        raise HTTPException(status_code=400, detail=f"暂不支持读取该 API 类型：{provider.api_type}")
    if not provider.api_key or not provider.base_url:
        raise HTTPException(status_code=400, detail="API Key 和 Base URL 不能为空")

    base_url = provider.base_url.rstrip("/")
    if base_url.endswith("/chat/completions"):
        base_url = base_url[: -len("/chat/completions")]
    if base_url.endswith("/responses"):
        base_url = base_url[: -len("/responses")]
    if base_url.endswith("/messages"):
        base_url = base_url[: -len("/messages")]
    endpoint = f"{base_url}/models"
    request = urllib.request.Request(
        endpoint,
        headers={
            **(
                {"x-api-key": provider.api_key, "anthropic-version": "2023-06-01"}
                if provider.api_type == "anthropic_messages"
                else {"Authorization": f"Bearer {provider.api_key}"}
            ),
            "Content-Type": "application/json",
        },
        method="GET",
    )
    try:
        context = ssl._create_unverified_context() if provider.allow_insecure_tls else None
        with urllib.request.urlopen(request, timeout=45, context=context) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"读取模型失败：{detail}") from exc
    except urllib.error.URLError as exc:
        detail = format_connection_error(exc.reason)
        raise HTTPException(status_code=502, detail=detail) from exc

    models = []
    for item in data.get("data", []):
        model_id = item.get("id")
        if model_id:
            models.append({"id": model_id, "name": model_id, "model": model_id})
    return {"models": models}


def format_connection_error(reason: object) -> str:
    if isinstance(reason, ssl.SSLCertVerificationError):
        return (
            "无法连接供应商：TLS 证书校验失败。通常是代理/公司网络使用了自签名证书、"
            "证书链不完整，或 Base URL 被中间层改写。请检查 Base URL、网络代理和系统证书。"
        )
    text = str(reason)
    if "CERTIFICATE_VERIFY_FAILED" in text or "self-signed certificate" in text:
        return (
            "无法连接供应商：TLS 证书校验失败。通常是代理/公司网络使用了自签名证书、"
            "证书链不完整，或 Base URL 被中间层改写。请检查 Base URL、网络代理和系统证书。"
        )
    return f"无法连接供应商：{text}"


@app.get("/")
def index() -> FileResponse:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Static UI not found")
    return FileResponse(index_file)


@app.post("/api/runs", response_model=RunRecord)
def create_run(payload: RunCreate, background_tasks: BackgroundTasks) -> RunRecord:
    provider = get_model_provider(payload.model_settings)
    run = create_run_record(payload)
    if payload.mode.value != "memory" or payload.source_run_id:
        background_tasks.add_task(
            execute_run_safe,
            run,
            payload.rounds,
            provider,
            payload.documents,
            payload.parallel_first_round,
            payload.mode,
            payload.selected_agents,
            payload.probe_agent,
            payload.probe_question,
        )
    return run


@app.get("/api/runs/{run_id}", response_model=RunRecord)
def get_run(run_id: str) -> RunRecord:
    try:
        return db.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.get("/api/runs/{run_id}/messages")
def get_messages(run_id: str):
    try:
        return db.get_run(run_id).debate_messages
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.get("/api/runs/{run_id}/report")
def get_report(run_id: str) -> dict[str, str]:
    try:
        run = db.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return {"run_id": run.run_id, "report": run.final_report}


@app.post("/api/runs/{run_id}/rerun", response_model=RunRecord)
def rerun_run(run_id: str) -> RunRecord:
    try:
        source = db.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return rerun(source, get_model_provider())


@app.post("/api/runs/{run_id}/cancel", response_model=RunRecord)
def cancel_existing_run(run_id: str) -> RunRecord:
    try:
        return cancel_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@app.post("/api/runs/{run_id}/resume", response_model=RunRecord)
def resume_existing_run(run_id: str, payload: RunResumeRequest, background_tasks: BackgroundTasks) -> RunRecord:
    try:
        source = db.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    if source.status not in {"FAILED", "CANCELED"}:
        raise HTTPException(status_code=400, detail="只有失败或已停止的运行可以继续分析")
    provider = get_model_provider(payload.model_settings)
    updated = db.update_run(
        run_id,
        rounds=payload.rounds,
        parallel_first_round=payload.parallel_first_round,
        model_settings=db.sanitized_model_settings(payload.model_settings),
        error="",
        current_step="准备从失败位置继续",
        _force=True,
    )
    background_tasks.add_task(
        resume_run_safe,
        updated,
        payload.rounds,
        provider,
        payload.parallel_first_round,
    )
    return updated


@app.post("/api/runs/{run_id}/references")
def regenerate_references(run_id: str, payload: dict | None = Body(default=None)) -> RunRecord:
    try:
        source = db.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    from app.orchestrator.runner import extract_references
    merge = (payload or {}).get("merge", False)
    existing = source.external_references if merge else None
    external_references = extract_references(source.debate_messages, existing)
    return db.update_run(run_id, external_references=external_references)


@app.get("/api/history", response_model=list[HistoryItem])
def history() -> list[HistoryItem]:
    return db.list_history()


@app.get("/api/history/location")
def history_location() -> dict[str, str]:
    return db.history_location()


@app.post("/api/history/delete")
def delete_history(payload: HistoryDeleteRequest) -> dict[str, int]:
    return {"deleted": db.delete_runs(payload.run_ids)}


@app.post("/api/memory/query", response_model=MemoryQueryResponse)
def memory_query(payload: MemoryQueryRequest) -> MemoryQueryResponse:
    try:
        source_run = db.get_run(payload.source_run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="源 Run 不存在") from exc
    if source_run.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="源 Run 尚未完成，无法作为记忆源")
    provider = get_model_provider()
    answer = execute_memory_query(source_run, payload.question, payload.agent_key, provider)
    return MemoryQueryResponse(
        answer=answer,
        source_run_id=source_run.run_id,
        source_field=source_run.template_input.field,
        agent_key=payload.agent_key,
    )
