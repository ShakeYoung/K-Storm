from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    CREATED = "CREATED"
    TEMPLATE_VALIDATED = "TEMPLATE_VALIDATED"
    INTAKE_RUNNING = "INTAKE_RUNNING"
    DEBATE_RUNNING = "DEBATE_RUNNING"
    GROUP_SUMMARY_RUNNING = "GROUP_SUMMARY_RUNNING"
    FINAL_REPORT_RUNNING = "FINAL_REPORT_RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class DiscussionMode(StrEnum):
    FULL_DELIBERATION = "full"
    FOCUSED_PANEL = "focused"
    QUICK_PROBE = "quick"
    MEMORY_QUERY = "memory"


class TemplateInput(BaseModel):
    field: str = Field(..., min_length=1)
    background: str = Field(..., min_length=1)
    existing_basis: str = Field(..., min_length=1)
    extension_points: str = ""
    core_question: str = ""
    platforms: str = ""
    constraints: str = ""
    target_output: str = ""
    preferred_direction: str = ""
    avoid_direction: str = ""


class StructuredBrief(BaseModel):
    research_context: str
    known_facts: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    opportunity_points: list[str] = Field(default_factory=list)
    intake_synthesis: str = ""


class TimelineStep(BaseModel):
    key: str
    label: str
    status: str = "pending"
    started_at: str = ""
    estimated_done_at: str = ""
    finished_at: str = ""
    is_overall: bool = False
    estimate_seconds: int = 0


class DebateMessage(BaseModel):
    round: int
    agent: str
    title: str
    content: str
    model_label: str = ""
    ir_summary: str = ""
    claims: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)


class EvidenceRef(BaseModel):
    id: str
    source_type: str = "briefing"
    source_id: str = ""
    source_title: str = ""
    quote_or_summary: str = ""
    supports: str = ""


class CritiquePoint(BaseModel):
    id: str
    target_id: str = ""
    dimension: str = ""
    severity: str = "medium"
    content: str = ""
    mitigation: str = ""


class ExternalReference(BaseModel):
    id: str
    source_type: str = "paper"  # paper / blog / dataset / book / other
    title: str = ""
    authors: str = ""
    url: str = ""
    year: str = ""
    cited_viewpoint: str = ""  # 引用该论据支撑的观点
    citing_agent: str = ""  # 引用该论据的 Agent
    round: int = 0


class CandidateDirection(BaseModel):
    id: str
    title: str
    research_question: str = ""
    rationale: str = ""
    novelty: str = ""
    feasibility: str = ""
    risks: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    priority: int = 0
    priority_reason: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    critique_refs: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class StructuredIRV2(BaseModel):
    version: str = "1.5"
    decision_summary: str = ""
    key_claims: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    critique_points: list[CritiquePoint] = Field(default_factory=list)
    candidate_directions: list[CandidateDirection] = Field(default_factory=list)


class UserModel(BaseModel):
    id: str
    name: str
    model: str
    context_window: str = ""


class UserModelProvider(BaseModel):
    id: str
    name: str
    category: str = "api"
    api_key: str = ""
    base_url: str = ""
    api_type: str = "openai_compatible"
    allow_insecure_tls: bool = False
    models: list[UserModel] = Field(default_factory=list)


class AgentModelSettings(BaseModel):
    providers: list[UserModelProvider] = Field(default_factory=list)
    assignments: dict[str, str] = Field(default_factory=dict)


class UploadedDocument(BaseModel):
    id: str
    name: str
    doc_type: str = "other"
    content: str = ""
    note: str = ""


class RunCreate(BaseModel):
    template_input: TemplateInput
    mode: DiscussionMode = DiscussionMode.FULL_DELIBERATION
    rounds: int = Field(default=3, ge=1, le=5)
    parallel_first_round: bool = False
    selected_agents: list[str] = Field(default_factory=list)
    probe_agent: str = ""
    probe_question: str = ""
    source_run_id: str = ""
    model_settings: AgentModelSettings | None = None
    documents: list[UploadedDocument] = Field(default_factory=list)


class RunResumeRequest(BaseModel):
    rounds: int = Field(default=3, ge=1, le=5)
    parallel_first_round: bool = False
    model_settings: AgentModelSettings | None = None


class RunRecord(BaseModel):
    run_id: str
    status: RunStatus
    mode: DiscussionMode = DiscussionMode.FULL_DELIBERATION
    template_input: TemplateInput
    rounds: int = 3
    parallel_first_round: bool = False
    selected_agents: list[str] = Field(default_factory=list)
    probe_agent: str = ""
    probe_question: str = ""
    source_run_id: str = ""
    model_settings: AgentModelSettings = Field(default_factory=AgentModelSettings)
    structured_brief: StructuredBrief | None = None
    structured_ir: StructuredIRV2 | None = None
    ir_warnings: list[str] = Field(default_factory=list)
    external_references: list[ExternalReference] = Field(default_factory=list)
    documents: list[UploadedDocument] = Field(default_factory=list)
    debate_messages: list[DebateMessage] = Field(default_factory=list)
    group_summary: str = ""
    final_report: str = ""
    error: str = ""
    current_step: str = ""
    timeline: list[TimelineStep] = Field(default_factory=list)
    created_at: str
    updated_at: str


class HistoryItem(BaseModel):
    run_id: str
    status: RunStatus
    mode: DiscussionMode = DiscussionMode.FULL_DELIBERATION
    source_run_id: str = ""
    field: str
    target_output: str
    decision_summary: str = ""
    candidate_titles: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class HistoryDeleteRequest(BaseModel):
    run_ids: list[str] = Field(default_factory=list)


class MemoryQueryRequest(BaseModel):
    source_run_id: str
    question: str = Field(..., min_length=1)
    agent_key: str = "reviewer"


class MemoryQueryResponse(BaseModel):
    answer: str
    source_run_id: str
    source_field: str = ""
    agent_key: str = ""


JsonDict = dict[str, Any]
