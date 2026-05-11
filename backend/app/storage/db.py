from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from app.schemas.models import (
    AgentModelSettings,
    DebateMessage,
    ExternalReference,
    HistoryItem,
    RunRecord,
    RunStatus,
    StructuredBrief,
    StructuredIRV2,
    TemplateInput,
    TimelineStep,
    UploadedDocument,
)


DB_PATH = Path(__file__).resolve().parents[3] / "data" / "ks.sqlite3"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                template_input TEXT NOT NULL,
                rounds INTEGER NOT NULL DEFAULT 3,
                parallel_first_round INTEGER NOT NULL DEFAULT 0,
                model_settings TEXT NOT NULL DEFAULT '{}',
                documents TEXT NOT NULL DEFAULT '[]',
                structured_brief TEXT,
                structured_ir TEXT NOT NULL DEFAULT '{}',
                debate_messages TEXT NOT NULL DEFAULT '[]',
                group_summary TEXT NOT NULL DEFAULT '',
                final_report TEXT NOT NULL DEFAULT '',
                error TEXT NOT NULL DEFAULT '',
                current_step TEXT NOT NULL DEFAULT '',
                timeline TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in db.execute("PRAGMA table_info(runs)").fetchall()
        }
        if "documents" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN documents TEXT NOT NULL DEFAULT '[]'")
        if "model_settings" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN model_settings TEXT NOT NULL DEFAULT '{}'")
        if "rounds" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN rounds INTEGER NOT NULL DEFAULT 3")
        if "parallel_first_round" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN parallel_first_round INTEGER NOT NULL DEFAULT 0")
        if "current_step" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN current_step TEXT NOT NULL DEFAULT ''")
        if "timeline" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN timeline TEXT NOT NULL DEFAULT '[]'")
        if "structured_ir" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN structured_ir TEXT NOT NULL DEFAULT '{}'")
        if "mode" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN mode TEXT NOT NULL DEFAULT 'full'")
        if "selected_agents" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN selected_agents TEXT NOT NULL DEFAULT '[]'")
        if "probe_agent" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN probe_agent TEXT NOT NULL DEFAULT ''")
        if "probe_question" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN probe_question TEXT NOT NULL DEFAULT ''")
        if "source_run_id" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN source_run_id TEXT NOT NULL DEFAULT ''")
        if "ir_warnings" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN ir_warnings TEXT NOT NULL DEFAULT '[]'")
        if "external_references" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN external_references TEXT NOT NULL DEFAULT '[]'")


def create_run(
    run_id: str,
    template_input: TemplateInput,
    documents: list[UploadedDocument] | None = None,
    model_settings: AgentModelSettings | None = None,
    rounds: int = 3,
    parallel_first_round: bool = False,
    mode: str = "full",
    selected_agents: list[str] | None = None,
    probe_agent: str = "",
    probe_question: str = "",
    source_run_id: str = "",
) -> RunRecord:
    now = utc_now()
    document_payload = json.dumps(
        [document.model_dump() for document in documents or []],
        ensure_ascii=False,
    )
    model_settings_payload = sanitized_model_settings(model_settings).model_dump_json()
    selected_agents_payload = json.dumps(selected_agents or [], ensure_ascii=False)
    with connect() as db:
        db.execute(
            """
            INSERT INTO runs (
                run_id, status, mode, template_input, rounds, parallel_first_round,
                model_settings, documents, selected_agents, probe_agent, probe_question,
                source_run_id, debate_messages, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                RunStatus.CREATED.value,
                mode,
                template_input.model_dump_json(),
                rounds,
                1 if parallel_first_round else 0,
                model_settings_payload,
                document_payload,
                selected_agents_payload,
                probe_agent,
                probe_question,
                source_run_id,
                "[]",
                now,
                now,
            ),
        )
    return get_run(run_id)


def update_run(run_id: str, **values: object) -> RunRecord:
    if not values:
        return get_run(run_id)
    force = bool(values.pop("_force", False))

    with connect() as db:
        current = db.execute("SELECT status FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if not force and current is not None and current["status"] == RunStatus.CANCELED.value:
        next_status = values.get("status")
        if not (isinstance(next_status, RunStatus) and next_status == RunStatus.CANCELED):
            return get_run(run_id)

    encoded: dict[str, object] = {"updated_at": utc_now()}
    for key, value in values.items():
        if hasattr(value, "model_dump_json"):
            encoded[key] = value.model_dump_json()
        elif isinstance(value, list):
            encoded[key] = json.dumps(
                [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in value
                ],
                ensure_ascii=False,
            )
        elif isinstance(value, RunStatus):
            encoded[key] = value.value
        else:
            encoded[key] = value

    assignments = ", ".join(f"{key} = ?" for key in encoded)
    with connect() as db:
        db.execute(
            f"UPDATE runs SET {assignments} WHERE run_id = ?",
            [*encoded.values(), run_id],
        )
    return get_run(run_id)


def get_run(run_id: str) -> RunRecord:
    with connect() as db:
        row = db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        raise KeyError(run_id)
    return row_to_run(row)


def list_history(limit: int = 30) -> list[HistoryItem]:
    with connect() as db:
        rows = db.execute(
            """
            SELECT run_id, status, mode, source_run_id, template_input, structured_ir, created_at, updated_at
            FROM runs
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    items: list[HistoryItem] = []
    for row in rows:
        template = TemplateInput.model_validate_json(row["template_input"])
        structured_ir = None
        if row["structured_ir"] and row["structured_ir"] != "{}":
            try:
                structured_ir = StructuredIRV2.model_validate_json(row["structured_ir"])
            except Exception:
                structured_ir = None
        items.append(
            HistoryItem(
                run_id=row["run_id"],
                status=row["status"],
                mode=row["mode"] if "mode" in row.keys() else "full",
                source_run_id=row["source_run_id"] if "source_run_id" in row.keys() else "",
                field=template.field,
                target_output=template.target_output,
                decision_summary=structured_ir.decision_summary if structured_ir else "",
                candidate_titles=[
                    candidate.title
                    for candidate in (structured_ir.candidate_directions if structured_ir else [])[:3]
                ],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
    return items


def delete_runs(run_ids: list[str]) -> int:
    if not run_ids:
        return 0
    placeholders = ", ".join("?" for _ in run_ids)
    with connect() as db:
        cursor = db.execute(
            f"DELETE FROM runs WHERE run_id IN ({placeholders})",
            run_ids,
        )
        return cursor.rowcount


def history_location() -> dict[str, str]:
    return {
        "folder": str(DB_PATH.parent),
        "database": str(DB_PATH),
    }


def row_to_run(row: sqlite3.Row) -> RunRecord:
    from app.schemas.models import DiscussionMode

    structured_raw = row["structured_brief"]
    structured_ir_raw = row["structured_ir"] or "{}"
    messages_raw = json.loads(row["debate_messages"] or "[]")
    documents_raw = json.loads(row["documents"] or "[]")
    timeline_raw = json.loads(row["timeline"] or "[]")
    selected_agents_raw = json.loads(row["selected_agents"] if "selected_agents" in row.keys() else "[]")
    structured_ir = None
    if structured_ir_raw and structured_ir_raw != "{}":
        try:
            structured_ir = StructuredIRV2.model_validate_json(structured_ir_raw)
        except Exception:
            structured_ir = None
    return RunRecord(
        run_id=row["run_id"],
        status=row["status"],
        mode=row["mode"] if "mode" in row.keys() else "full",
        template_input=TemplateInput.model_validate_json(row["template_input"]),
        rounds=row["rounds"],
        parallel_first_round=bool(row["parallel_first_round"]),
        selected_agents=selected_agents_raw,
        probe_agent=row["probe_agent"] if "probe_agent" in row.keys() else "",
        probe_question=row["probe_question"] if "probe_question" in row.keys() else "",
        source_run_id=row["source_run_id"] if "source_run_id" in row.keys() else "",
        model_settings=AgentModelSettings.model_validate_json(row["model_settings"] or "{}"),
        structured_brief=(
            StructuredBrief.model_validate_json(structured_raw)
            if structured_raw
            else None
        ),
        structured_ir=structured_ir,
        ir_warnings=json.loads(row["ir_warnings"] if "ir_warnings" in row.keys() else "[]"),
        external_references=[ExternalReference.model_validate(item) for item in json.loads(row["external_references"] if "external_references" in row.keys() else "[]")],
        documents=[UploadedDocument.model_validate(item) for item in documents_raw],
        debate_messages=[DebateMessage.model_validate(item) for item in messages_raw],
        group_summary=row["group_summary"],
        final_report=row["final_report"],
        error=row["error"],
        current_step=row["current_step"],
        timeline=[TimelineStep.model_validate(item) for item in timeline_raw],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def sanitized_model_settings(settings: AgentModelSettings | None) -> AgentModelSettings:
    if settings is None:
        return AgentModelSettings()
    payload = settings.model_dump()
    for provider in payload.get("providers", []):
        provider["api_key"] = ""
    return AgentModelSettings.model_validate(payload)
