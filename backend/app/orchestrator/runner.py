from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
import json
import re
from uuid import uuid4

from app.agents.registry import (
    DISCUSSION_AGENTS,
    GROUP_SUMMARIZER,
    INTAKE_AGENT,
    MODERATOR_AGENT,
    OUTPUT_AGENT,
    AgentSpec,
)
from app.model_providers.base import ModelProvider
from app.schemas.models import (
    DebateMessage,
    DiscussionMode,
    ResearchStage,
    RunCreate,
    RunRecord,
    RunStatus,
    StructuredBrief,
    StructuredIRV2,
    TemplateInput,
    TimelineStep,
    UploadedDocument,
)
from app.storage import db

_CANCELED_RUNS: set[str] = set()

STEP_ESTIMATES = {
    "template": 5,
    "doc_extract": 120,
    "intake": 180,
    "handoff": 5,
    "debate": 180,
    "group_summary": 120,
    "final_report": 240,
}
OUTPUT_LIMITS = {
    "intake": 3500,
    "doc_extract": 900,
    "debate": 4000,
    "moderator": 3500,
    "group_summary": 4200,
    "final_report": 6000,
}

DOC_INLINE_THRESHOLD_CHARS = 12000
DOC_EXTRACT_HEAD_CHARS = 6000
DOC_EXTRACT_TAIL_CHARS = 2000
DOC_SUMMARY_MAX_CHARS = 420
INTAKE_DOC_SUMMARY_BUDGET = 9000

END_MARKERS = {
    "debate": "<<<END_OF_AGENT_MESSAGE>>>",
    "moderator": "<<<END_OF_MODERATOR_MESSAGE>>>",
    "group_summary": "<<<END_OF_GROUP_SUMMARY>>>",
    "final_report": "<<<END_OF_FINAL_REPORT>>>",
    "quick": "<<<END_OF_QUICK_PROBE>>>",
    "doc_extract": "<<<END_OF_DOC_EXTRACT>>>",
    "intake": "<<<END_OF_INTAKE>>>",
}


class IncompleteModelOutput(RuntimeError):
    pass


def strip_end_markers(text: str) -> str:
    cleaned = str(text or "")
    for marker in END_MARKERS.values():
        cleaned = cleaned.replace(marker, "")
    return cleaned.strip()


def generate_validated(
    provider: ModelProvider,
    *,
    agent_key: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int | None,
    on_retry,
    kind: str,
    stage_label: str,
    attempts: int = 2,
) -> str:
    """Generate text and validate structural completeness before advancing workflow.

    Strategy for truncated outputs (has body but missing end marker/sections):
    - On 2nd attempt, only ask the model to *continue* and append the missing
      sections, rather than regenerating the entire output from scratch.
    - This is much faster because the continuation prompt is tiny compared to
      the full original prompt.
    """
    last_text = ""
    last_body = ""  # tracks the accumulated body for truncation-continuation
    last_errors: list[str] = []
    marker = END_MARKERS.get(kind, "")
    prompt = user_prompt
    is_continuation = False

    for attempt in range(attempts):
        text = provider.generate(
            agent_key=agent_key,
            system_prompt=system_prompt,
            user_prompt=prompt,
            max_tokens=max_tokens,
            on_retry=on_retry,
        )
        text = text or ""

        # If this was a continuation request, prepend the original body
        if is_continuation:
            text = last_body + "\n\n" + text
            is_continuation = False

        last_text = text
        last_errors = validate_output_complete(last_text, kind)
        if not last_errors:
            return strip_end_markers(last_text)

        # P2: detect truncation vs empty output
        body = strip_end_markers(last_text)
        truncation_threshold = {"debate": 500, "moderator": 400, "group_summary": 400, "final_report": 600, "quick": 150, "doc_extract": 60, "intake": 100}.get(kind, 200)
        is_truncation = len(body) >= truncation_threshold

        if is_truncation and attempt < attempts - 1:
            # Truncation: save body, ask for continuation only
            last_body = body
            is_continuation = True
            missing_desc = "; ".join(last_errors)
            prompt = f"""你上一条输出被截断了,缺少:{missing_desc}

请直接续写以下内容的缺失部分(不要重复已有内容):

--- 已有输出(最后几行) ---
{body[-800:]}

--- 请从这里续写 ---
补全所有缺失小节,最后必须以 {marker} 结束。"""
        elif attempt < attempts - 1:
            # Empty/very short output: full retry with correction hints
            prompt = f"""你上一条输出没有通过完整性校验,问题如下:
{chr(10).join('- ' + item for item in last_errors)}

请重新完整输出本阶段内容,不要解释校验错误,不要省略必需小节。最后必须以 {marker} 结束。

原始任务如下:
{user_prompt}
"""

    preview = " ".join(last_text.split())[:180]
    raise IncompleteModelOutput(f"{stage_label}输出不完整:{'; '.join(last_errors)}。最后一次输出片段:{preview}")


def validate_output_complete(text: str, kind: str) -> list[str]:
    raw = str(text or "").strip()
    errors: list[str] = []
    marker = END_MARKERS.get(kind)
    if marker and marker not in raw:
        errors.append(f"缺少结束标记 {marker}")
    body = strip_end_markers(raw)
    if len(body) < {"debate": 300, "moderator": 300, "group_summary": 400, "final_report": 800, "quick": 200, "doc_extract": 80, "intake": 150}.get(kind, 200):
        errors.append("正文过短,疑似截断")
    if kind == "debate":
        if "### 给结构化 IR 的要点摘要" not in body:
            errors.append("缺少结构化 IR 摘要小节")
        if "### 外部引用" not in body:
            errors.append("缺少外部引用小节")
        elif not _has_valid_reference_lines(body):
            errors.append("外部引用小节缺少合法引用行")
        for key in ["关键主张", "支撑依据", "风险或反驳点", "建议进入 IR"]:
            if key not in body:
                errors.append(f"IR 摘要缺少字段:{key}")
    elif kind == "moderator":
        for key in ["冲突", "遗漏", "第 2 轮", "给结构化 IR 的要点摘要"]:
            if key not in body:
                errors.append(f"Moderator 输出缺少:{key}")
    elif kind == "group_summary":
        if "```json" not in body.lower() and not body.lstrip().startswith("{"):
            errors.append("结构化 IR 缺少 JSON 块")
        if '"candidate_directions"' not in body:
            errors.append("结构化 IR JSON 缺少 candidate_directions")
        if "## 结构化 IR 文档" not in body:
            errors.append("结构化 IR 缺少 Markdown 文档段")
    elif kind == "final_report":
        if not body.startswith("#"):
            errors.append("最终报告缺少 Markdown 标题")
        for key in ["下一步", "证据", "风险"]:
            if key not in body:
                errors.append(f"最终报告缺少核心板块:{key}")
    elif kind == "doc_extract":
        bullet_count = len(re.findall(r"[\n\r]\s*[-*•·]\s+", body)) + (1 if re.match(r"\s*[-*•·]\s+", body) else 0)
        if bullet_count < 2:
            errors.append("文档摘要至少需要 2 条 bullet 要点")
    elif kind == "intake":
        if "##" not in body and "**" not in body:
            errors.append("intake 输出缺少结构化 Markdown 格式")
    return errors


def _has_valid_reference_lines(text: str) -> bool:
    marker = "### 外部引用"
    idx = text.find(marker)
    if idx < 0:
        return False
    section = text[idx + len(marker):]
    next_idx = section.find("\n###")
    if next_idx >= 0:
        section = section[:next_idx]
    for line in section.splitlines():
        line = line.strip().lstrip("-•* ")
        if re.match(r"\[(paper|blog|dataset|book|other)\]\s*[^|]{3,}\s*\|\s*[^|]+\s*\|", line, re.IGNORECASE):
            return True
    return False


def infer_research_stage(template: TemplateInput, explicit_stage: ResearchStage | str = ResearchStage.AUTO) -> ResearchStage:
    if explicit_stage and str(explicit_stage) != ResearchStage.AUTO.value:
        return ResearchStage(str(explicit_stage))
    text = "\n".join([
        template.background,
        template.existing_basis,
        template.extension_points,
        template.core_question,
        template.platforms,
        template.constraints,
        template.target_output,
        template.preferred_direction,
    ])
    rich_signals = sum(bool(v.strip()) for v in [template.platforms, template.constraints, template.target_output, template.extension_points, template.core_question])
    has_results = bool(re.search(r"\b\d+(?:\.\d+)?\s*(g/l|mg/l|%|倍|fold|cells?|样本|天|h|小时)\b", text, re.IGNORECASE))
    design_terms = len(re.findall(r"对照|重复|构建|培养|测序|流式|western|qPCR|动物|模型|readout|干预|验证", text, re.IGNORECASE))
    pivot_terms = len(re.findall(r"转向|偏差|换题|不成立|失败|卡住|瓶颈|止损", text, re.IGNORECASE))
    if pivot_terms >= 2:
        return ResearchStage.PIVOT_EVALUATION
    if has_results or design_terms >= 5:
        return ResearchStage.RESULT_DIAGNOSIS
    if rich_signals >= 3 and len(template.existing_basis.strip()) > 80:
        return ResearchStage.PLAN_REFINEMENT
    return ResearchStage.TOPIC_EXPLORATION


def research_stage_label(stage: ResearchStage | str) -> str:
    value = str(stage)
    return {
        ResearchStage.AUTO.value: "自动判断",
        ResearchStage.TOPIC_EXPLORATION.value: "选题探索",
        ResearchStage.PLAN_REFINEMENT.value: "方案收敛",
        ResearchStage.RESULT_DIAGNOSIS.value: "结果诊断",
        ResearchStage.PIVOT_EVALUATION.value: "转向评估",
    }.get(value, value)


def stage_goal_text(stage: ResearchStage | str) -> str:
    value = str(stage)
    return {
        ResearchStage.TOPIC_EXPLORATION.value: "当前阶段以探索新方向和候选课题为主,可以给出课题名称建议。",
        ResearchStage.PLAN_REFINEMENT.value: "当前阶段以推进和完善现有课题为主,不要把重新推荐新课题作为主轴。",
        ResearchStage.RESULT_DIAGNOSIS.value: "当前阶段以解释结果、定位瓶颈、设计补充实验为主,不要通篇转成新选题推荐。",
        ResearchStage.PIVOT_EVALUATION.value: "当前阶段以判断是否需要局部修正或转向为主;若当前路线偏差较大,可在报告后段给出转向建议。",
    }.get(value, "请根据当前科研阶段组织输出。")


def start_run(payload: RunCreate, provider: ModelProvider) -> RunRecord:
    run = create_run_record(payload)
    if payload.mode == DiscussionMode.MEMORY_QUERY and not payload.source_run_id:
        return run
    # memory 模式有 source_run_id 时,路由到 focused 执行路径(execute_run_safe 会处理)
    execute_run_safe(
        run,
        payload.rounds,
        provider,
        payload.documents,
        payload.parallel_first_round,
        mode=payload.mode,
        selected_agents=payload.selected_agents,
        probe_agent=payload.probe_agent,
        probe_question=payload.probe_question,
    )
    return db.get_run(run.run_id)


def create_run_record(payload: RunCreate) -> RunRecord:
    run_id = f"ks_{uuid4().hex[:10]}"
    inferred_stage = infer_research_stage(payload.template_input, payload.research_stage)
    return db.create_run(
        run_id,
        payload.template_input,
        payload.documents,
        payload.model_settings,
        payload.rounds,
        payload.parallel_first_round,
        mode=payload.mode.value if isinstance(payload.mode, DiscussionMode) else str(payload.mode),
        research_stage=inferred_stage.value,
        selected_agents=payload.selected_agents,
        probe_agent=payload.probe_agent,
        probe_question=payload.probe_question,
        source_run_id=payload.source_run_id,
        run_name=payload.run_name,
    )


def execute_run_safe(
    run: RunRecord,
    rounds: int,
    provider: ModelProvider,
    documents: list[UploadedDocument] | None = None,
    parallel_first_round: bool = False,
    mode: DiscussionMode = DiscussionMode.FULL_DELIBERATION,
    selected_agents: list[str] | None = None,
    probe_agent: str = "",
    probe_question: str = "",
) -> None:
    try:
        if mode == DiscussionMode.FOCUSED_PANEL or mode == DiscussionMode.MEMORY_QUERY:
            execute_focused_panel(run, rounds, provider, documents or [], selected_agents or [])
        elif mode == DiscussionMode.QUICK_PROBE:
            execute_quick_probe(run, provider, documents or [], probe_agent, probe_question)
        else:
            execute_run(run, rounds, provider, documents or [], parallel_first_round)
    except RunCanceled:
        return
    except Exception as exc:
        failed_run = db.get_run(run.run_id)
        if failed_run.status == RunStatus.CANCELED:
            return
        step = failed_run.current_step or "未知步骤"
        timeline = fail_timeline_step(failed_run.timeline, step)
        db.update_run(
            run.run_id,
            status=RunStatus.FAILED,
            error=f"{step}:{str(exc)}",
            timeline=timeline,
        )


def execute_focused_panel(
    run: RunRecord,
    rounds: int,
    provider: ModelProvider,
    documents: list[UploadedDocument],
    selected_agents: list[str],
) -> RunRecord:
    """Focused Panel 模式:仅选定 Agent 参与,1-2 轮,精简 IR + 报告。"""
    ensure_not_canceled(run.run_id)
    timeline = build_timeline(rounds, False, documents)
    run = update_run_checked(run.run_id, timeline=timeline)

    # 1. Template 验证
    timeline = start_timeline_step(run.timeline, "template")
    run = update_run_checked(run.run_id, status=RunStatus.TEMPLATE_VALIDATED, current_step="校验模板", timeline=timeline)
    timeline = finish_timeline_step(run.timeline, "template")

    # 2. Intake(精简版 briefing)
    documents, timeline, run = summarize_documents_if_needed(run, provider, documents, timeline)
    timeline = start_timeline_step(timeline, "intake")
    run = update_run_checked(run.run_id, status=RunStatus.INTAKE_RUNNING, current_step=f"入口 Agent 整理模板({provider.label_for(INTAKE_AGENT.key)})", timeline=timeline)
    structured_brief = build_structured_brief(run.template_input, documents)
    intake_note = generate_validated(
        provider,
        agent_key=INTAKE_AGENT.key,
        system_prompt=INTAKE_AGENT.system_prompt,
        user_prompt=intake_prompt(run.template_input, documents),
        max_tokens=OUTPUT_LIMITS["intake"],
        on_retry=retry_callback(run.run_id, "intake", "入口 Agent"),
        kind="intake",
        stage_label="入口 Agent",
    )
    ensure_not_canceled(run.run_id)
    structured_brief.intake_synthesis = intake_note
    # 注入记忆上下文(如果有源 run)
    if run.source_run_id:
        try:
            source = db.get_run(run.source_run_id)
            memory_parts = []
            sb = source.structured_brief
            if sb:
                if sb.known_facts:
                    memory_parts.append("已知事实:" + ";".join(sb.known_facts[:6]))
                if sb.unknowns:
                    memory_parts.append("未知问题:" + ";".join(sb.unknowns[:4]))
                if sb.constraints:
                    memory_parts.append("约束条件:" + ";".join(sb.constraints[:4]))
                if sb.opportunity_points:
                    memory_parts.append("机会点:" + ";".join(sb.opportunity_points[:4]))
            if source.group_summary:
                memory_parts.append("\n结构化 IR 摘要:\n" + source.group_summary[:1500])
            if source.debate_messages:
                samples = [f"[{m.agent} · 第{m.round}轮]:{m.content[:300]}" for m in source.debate_messages[:4]]
                memory_parts.append("\n讨论摘要:\n" + "\n".join(samples))
            if memory_parts:
                structured_brief.intake_synthesis += "\n\n## 记忆上下文(来自历史讨论:" + source.template_input.field + ")\n\n" + "\n".join(memory_parts)
        except Exception:
            pass  # source run 不存在时静默跳过
    timeline = finish_timeline_step(timeline, "intake")
    run = update_run_checked(run.run_id, structured_brief=structured_brief, timeline=timeline)

    # 3. 选定 Agent 讨论
    agents = [a for a in DISCUSSION_AGENTS if a.key in selected_agents]
    if not agents:
        agents = DISCUSSION_AGENTS[:2]  # fallback: 前 2 个

    messages: list[DebateMessage] = []
    timeline = start_timeline_step(timeline, "handoff")
    run = update_run_checked(run.run_id, status=RunStatus.DEBATE_RUNNING, current_step="传送到讨论组", timeline=timeline)
    timeline = finish_timeline_step(timeline, "handoff")
    run = update_run_checked(run.run_id, timeline=timeline)

    for round_number in range(1, rounds + 1):
        for agent in agents:
            timeline = start_timeline_step(run.timeline, debate_step_key(round_number, agent))
            step_label = f"第 {round_number} 轮 · {agent.display_name}({provider.label_for(agent.key)})"
            run = update_run_checked(run.run_id, current_step=step_label, timeline=timeline)
            ensure_not_canceled(run.run_id)
            note = generate_validated(
                provider,
                agent_key=agent.key,
                system_prompt=agent.system_prompt,
                user_prompt=debate_prompt(
                    template=run.template_input,
                    brief=structured_brief,
                    round_number=round_number,
                    agent=agent,
                    history=messages,
                    independent_first_round=(round_number == 1),
                    mode_context=("本次是追问讨论,请在已有历史结论的基础上回答新问题,不需要做全面的选题评估。" if run.mode == "memory" else "你正在参加聚焦讨论,请针对讨论问题给出你的专业视角,不需要做全面的选题评估。"),
                    research_stage=run.research_stage,
                ),
                max_tokens=OUTPUT_LIMITS["debate"],
                on_retry=retry_callback(run.run_id, debate_step_key(round_number, agent), step_label),
                kind="debate",
                stage_label=step_label,
            )
            ensure_not_canceled(run.run_id)
            messages.append(
                DebateMessage(
                    round=round_number,
                    agent=agent.display_name,
                    title=f"第 {round_number} 轮 · {agent.role}",
                    content=note,
                    model_label=provider.label_for(agent.key),
                    ir_summary=_extract_ir_summary(note),
                    claims=_extract_claims(note),
                    concerns=_extract_concerns(note),
                )
            )
            timeline = finish_timeline_step(run.timeline, debate_step_key(round_number, agent))
            run = update_run_checked(run.run_id, debate_messages=messages, timeline=timeline)

    # 4. 精简 IR(按模式选择 prompt)
    is_memory = run.mode == "memory"
    s_prompt = summary_prompt_focused if is_memory else summary_prompt
    timeline = start_timeline_step(timeline, "group_summary")
    run = update_run_checked(run.run_id, status=RunStatus.GROUP_SUMMARY_RUNNING, current_step=f"精简 IR({provider.label_for(GROUP_SUMMARIZER.key)})", timeline=timeline)
    group_summary = generate_validated(
        provider,
        agent_key=GROUP_SUMMARIZER.key,
        system_prompt=GROUP_SUMMARIZER.system_prompt,
        user_prompt=s_prompt(run.template_input, structured_brief, messages, run.research_stage),
        max_tokens=OUTPUT_LIMITS["group_summary"],
        on_retry=retry_callback(run.run_id, "group_summary", "精简 IR"),
        kind="group_summary",
        stage_label="精简 IR",
    )
    ensure_not_canceled(run.run_id)
    structured_ir = parse_structured_ir_v2(group_summary, run.template_input, structured_brief, messages)
    group_summary = clean_structured_ir_markdown(group_summary)
    ir_warnings = validate_structured_ir(structured_ir) if structured_ir else []
    timeline = finish_timeline_step(timeline, "group_summary")
    # 提取外部引用(memory 模式合并源 run 的引用)
    existing_refs = None
    if is_memory and run.source_run_id:
        try:
            source = db.get_run(run.source_run_id)
            existing_refs = source.external_references
        except KeyError:
            pass
    external_references = extract_references(messages, existing_refs)
    run = update_run_checked(run.run_id, group_summary=group_summary, structured_ir=structured_ir, ir_warnings=ir_warnings, external_references=external_references, timeline=timeline)

    # 5. 最终报告(按模式选择 prompt)
    if is_memory:
        source_summary = ""
        if run.source_run_id:
            try:
                source = db.get_run(run.source_run_id)
                if source.group_summary:
                    source_summary = source.group_summary[:600]
            except KeyError:
                pass
        r_prompt = lambda **kw: report_prompt_memory(source_summary=source_summary, **kw)
        report_label = "追问分析报告"
    else:
        r_prompt = report_prompt_focused
        report_label = "聚焦分析报告"
    timeline = start_timeline_step(timeline, "final_report")
    run = update_run_checked(run.run_id, status=RunStatus.FINAL_REPORT_RUNNING, current_step=f"{report_label}({provider.label_for(OUTPUT_AGENT.key)})", timeline=timeline)
    final_report = clean_final_report(generate_validated(
        provider,
        agent_key=OUTPUT_AGENT.key,
        system_prompt=OUTPUT_AGENT.system_prompt,
        user_prompt=r_prompt(template=run.template_input, brief=structured_brief, messages=messages, group_summary=group_summary, structured_ir=structured_ir, research_stage=run.research_stage),
        max_tokens=OUTPUT_LIMITS["final_report"],
        on_retry=retry_callback(run.run_id, "final_report", report_label),
        kind="final_report",
        stage_label=report_label,
    ))
    ensure_not_canceled(run.run_id)
    timeline = finish_timeline_step(timeline, "final_report")
    timeline = finish_timeline_step(timeline, "overall")
    return update_run_checked(run.run_id, status=RunStatus.COMPLETED, current_step="分析完成", final_report=final_report, timeline=timeline)


def execute_quick_probe(
    run: RunRecord,
    provider: ModelProvider,
    documents: list[UploadedDocument],
    probe_agent_key: str,
    probe_question: str,
) -> RunRecord:
    """Quick Probe 模式:单 Agent 单次问答。"""
    ensure_not_canceled(run.run_id)
    timeline = build_timeline(1, False, documents)
    run = update_run_checked(run.run_id, timeline=timeline)

    # 1. Template 验证
    timeline = start_timeline_step(run.timeline, "template")
    run = update_run_checked(run.run_id, status=RunStatus.TEMPLATE_VALIDATED, current_step="校验模板", timeline=timeline)
    timeline = finish_timeline_step(run.timeline, "template")

    # 2. 精简 Intake
    timeline = start_timeline_step(timeline, "intake")
    run = update_run_checked(run.run_id, status=RunStatus.INTAKE_RUNNING, current_step="入口 Agent 快速整理", timeline=timeline)
    structured_brief = build_structured_brief(run.template_input, documents)
    brief_summary = f"研究上下文:{structured_brief.research_context}。已知事实:{';'.join(structured_brief.known_facts[:5])}"
    timeline = finish_timeline_step(timeline, "intake")
    run = update_run_checked(run.run_id, structured_brief=structured_brief, timeline=timeline)

    # 3. 找到目标 Agent
    agent = next((a for a in DISCUSSION_AGENTS if a.key == probe_agent_key), None)
    if not agent:
        agent = DISCUSSION_AGENTS[0]  # fallback

    # 4. 单次问答
    messages: list[DebateMessage] = []
    timeline = start_timeline_step(timeline, debate_step_key(1, agent))
    step_label = f"Quick Probe · {agent.display_name}({provider.label_for(agent.key)})"
    run = update_run_checked(run.run_id, status=RunStatus.DEBATE_RUNNING, current_step=step_label, timeline=timeline)
    ensure_not_canceled(run.run_id)

    question_context = probe_question or run.template_input.core_question or run.template_input.background
    user_prompt = f"""用户问题:{question_context}

研究背景:{run.template_input.background}
已有基础:{run.template_input.existing_basis}
Briefing 摘要:{brief_summary}

请用中文 Markdown 直接回答上述问题,内容具体、可执行,避免空泛套话。
最后一行必须输出:<<<END_OF_QUICK_PROBE>>>"""

    note = generate_validated(
        provider,
        agent_key=agent.key,
        system_prompt=agent.system_prompt,
        user_prompt=user_prompt,
        max_tokens=2600,
        on_retry=retry_callback(run.run_id, debate_step_key(1, agent), step_label),
        kind="quick",
        stage_label=step_label,
    )
    ensure_not_canceled(run.run_id)
    messages.append(
        DebateMessage(
            round=1,
            agent=agent.display_name,
            title=f"Quick Probe · {agent.role}",
            content=note,
            model_label=provider.label_for(agent.key),
        )
    )
    timeline = finish_timeline_step(run.timeline, debate_step_key(1, agent))
    timeline = finish_timeline_step(timeline, "overall")
    return update_run_checked(run.run_id, status=RunStatus.COMPLETED, current_step="快速探测完成", debate_messages=messages, timeline=timeline)


def resume_run_safe(
    run: RunRecord,
    rounds: int,
    provider: ModelProvider,
    parallel_first_round: bool = False,
) -> None:
    try:
        resume_run(run, rounds, provider, run.documents, parallel_first_round)
    except RunCanceled:
        return
    except Exception as exc:
        failed_run = db.get_run(run.run_id)
        if failed_run.status == RunStatus.CANCELED:
            return
        step = failed_run.current_step or "未知步骤"
        timeline = fail_timeline_step(failed_run.timeline, step)
        db.update_run(
            run.run_id,
            status=RunStatus.FAILED,
            error=f"{step}:{str(exc)}",
            timeline=timeline,
        )


def rerun(source: RunRecord, provider: ModelProvider) -> RunRecord:
    payload = RunCreate(
        template_input=source.template_input,
        documents=source.documents,
        rounds=source.rounds,
        parallel_first_round=source.parallel_first_round,
        model_settings=source.model_settings,
        mode=source.mode,
        selected_agents=source.selected_agents,
        probe_agent=source.probe_agent,
        probe_question=source.probe_question,
        source_run_id=source.source_run_id,
    )
    return start_run(payload, provider)


def execute_memory_query(
    source_run: RunRecord,
    question: str,
    agent_key: str,
    provider: ModelProvider,
) -> str:
    """基于历史 run 的记忆回答用户问题,不创建新 run。"""
    from app.agents.registry import DISCUSSION_AGENTS, INTAKE_AGENT, MODERATOR_AGENT, OUTPUT_AGENT, GROUP_SUMMARIZER

    # 找到目标 agent
    all_agents = list(DISCUSSION_AGENTS) + [INTAKE_AGENT, MODERATOR_AGENT, GROUP_SUMMARIZER, OUTPUT_AGENT]
    agent = next((a for a in all_agents if a.key == agent_key), None)
    if not agent:
        agent = DISCUSSION_AGENTS[0]

    # 构建记忆上下文
    brief = source_run.structured_brief
    memory_parts = []

    if brief:
        memory_parts.append(f"研究上下文:{brief.research_context}")
        if brief.known_facts:
            memory_parts.append(f"已知事实:{';'.join(brief.known_facts[:6])}")
        if brief.unknowns:
            memory_parts.append(f"未知问题:{';'.join(brief.unknowns[:4])}")
        if brief.constraints:
            memory_parts.append(f"约束条件:{';'.join(brief.constraints[:4])}")
        if brief.opportunity_points:
            memory_parts.append(f"机会点:{';'.join(brief.opportunity_points[:4])}")
        if brief.intake_synthesis:
            memory_parts.append(f"\n入口整合 Briefing:\n{brief.intake_synthesis[:2000]}")

    if source_run.group_summary:
        memory_parts.append(f"\n结构化 IR 摘要:\n{source_run.group_summary[:2000]}")

    # 精选辩论摘要(最多 4 条)
    if source_run.debate_messages:
        debate_samples = []
        for msg in source_run.debate_messages[:6]:
            content_preview = msg.content[:400]
            debate_samples.append(f"[{msg.agent} · 第{msg.round}轮]:{content_preview}")
        memory_parts.append(f"\n讨论记录摘要:\n" + "\n".join(debate_samples))

    memory_text = "\n".join(memory_parts)

    user_prompt = f"""你是一个科研头脑风暴系统中的 {agent.display_name}({agent.role})。
用户基于之前的一次完整讨论,提出了一个新的后续问题。请基于记忆中的上下文来回答。

## 记忆上下文(来自历史讨论:{source_run.template_input.field})

{memory_text}

## 用户的新问题

{question}

请用中文 Markdown 直接回答,内容具体、可执行。如果记忆中的信息不足以完整回答,请明确指出缺少什么,并给出基于已有信息的最佳判断。"""

    return generate_validated(
        provider,
        agent_key=agent.key,
        system_prompt=agent.system_prompt,
        user_prompt=user_prompt + "\n\n最后一行必须输出:<<<END_OF_QUICK_PROBE>>>",
        max_tokens=3000,
        on_retry=None,
        kind="quick",
        stage_label="记忆查询",
    )


class RunCanceled(RuntimeError):
    pass


def cancel_run(run_id: str) -> RunRecord:
    _CANCELED_RUNS.add(run_id)
    run = db.get_run(run_id)
    timeline = cancel_timeline_step(run.timeline)
    return db.update_run(
        run_id,
        status=RunStatus.CANCELED,
        current_step="用户已停止分析",
        error="",
        timeline=timeline,
    )


def ensure_not_canceled(run_id: str) -> None:
    if run_id in _CANCELED_RUNS:
        raise RunCanceled(run_id)
    if db.get_run(run_id).status == RunStatus.CANCELED:
        _CANCELED_RUNS.add(run_id)
        raise RunCanceled(run_id)


def update_run_checked(run_id: str, **values: object) -> RunRecord:
    ensure_not_canceled(run_id)
    updated = db.update_run(run_id, **values)
    ensure_not_canceled(run_id)
    return updated


def resume_run(
    run: RunRecord,
    rounds: int,
    provider: ModelProvider,
    documents: list[UploadedDocument] | None = None,
    parallel_first_round: bool = False,
) -> RunRecord:
    _CANCELED_RUNS.discard(run.run_id)
    documents = documents or []
    timeline = run.timeline or build_timeline(rounds, parallel_first_round, documents)
    timeline = prepare_timeline_for_resume(timeline, rounds, parallel_first_round, documents)
    run = db.update_run(
        run.run_id,
        status=RunStatus.TEMPLATE_VALIDATED,
        current_step="准备从失败位置继续",
        error="",
        timeline=timeline,
        _force=True,
    )
    ensure_not_canceled(run.run_id)

    structured_brief = run.structured_brief
    if structured_brief is None:
        timeline = start_timeline_step(run.timeline, "template")
        timeline = finish_timeline_step(timeline, "template")
        run = update_run_checked(
            run.run_id,
            status=RunStatus.TEMPLATE_VALIDATED,
            current_step="创建运行并校验模板",
            timeline=timeline,
        )
        structured_brief, timeline, run = run_intake_step(run, provider, documents, timeline)
    else:
        timeline = run.timeline

    messages = list(run.debate_messages)
    timeline = ensure_handoff_step(timeline)
    run = update_run_checked(run.run_id, status=RunStatus.DEBATE_RUNNING, timeline=timeline)

    for round_number in range(1, rounds + 1):
        for agent in DISCUSSION_AGENTS:
            if has_agent_message(messages, round_number, agent):
                timeline = finish_timeline_step(timeline, debate_step_key(round_number, agent))
                continue
            messages, timeline, run = run_debate_agent(
                run,
                structured_brief,
                provider,
                messages,
                timeline,
                round_number,
                agent,
                independent_first_round=parallel_first_round and round_number == 1,
            )
        if round_number == 1 and not has_agent_message(messages, 1, MODERATOR_AGENT):
            messages, timeline, run = run_moderator_step(run, structured_brief, provider, messages, timeline)

    group_summary = run.group_summary
    if not group_summary:
        group_summary, timeline, run = run_group_summary_step(
            run,
            structured_brief,
            provider,
            messages,
            timeline,
        )
        if not run.external_references:
            external_references = extract_references(messages)
            run = update_run_checked(run.run_id, external_references=external_references)
    elif not run.structured_ir:
        structured_ir = parse_structured_ir_v2(group_summary, run.template_input, structured_brief, messages)
        ir_warnings = validate_structured_ir(structured_ir) if structured_ir else []
        external_references = extract_references(messages)
        run = update_run_checked(run.run_id, structured_ir=structured_ir, ir_warnings=ir_warnings, external_references=external_references)

    if not run.external_references:
        external_references = extract_references(messages)
        run = update_run_checked(run.run_id, external_references=external_references)

    if not run.final_report:
        _, timeline, run = run_final_report_step(
            run,
            structured_brief,
            provider,
            messages,
            group_summary,
            timeline,
        )

    return run


def execute_run(
    run: RunRecord,
    rounds: int,
    provider: ModelProvider,
    documents: list[UploadedDocument] | None = None,
    parallel_first_round: bool = False,
) -> RunRecord:
    documents = documents or []
    ensure_not_canceled(run.run_id)
    timeline = build_timeline(rounds, parallel_first_round, documents)
    run = update_run_checked(run.run_id, timeline=timeline)
    timeline = start_timeline_step(run.timeline, "template")
    run = update_run_checked(
        run.run_id,
        status=RunStatus.TEMPLATE_VALIDATED,
        current_step="创建运行并校验模板",
        timeline=timeline,
    )
    timeline = finish_timeline_step(run.timeline, "template")

    documents, timeline, run = summarize_documents_if_needed(run, provider, documents, timeline)
    timeline = start_timeline_step(timeline, "intake")
    intake_step = f"入口 Agent 整理模板与上传文档({provider.label_for(INTAKE_AGENT.key)})"
    run = update_run_checked(
        run.run_id,
        status=RunStatus.INTAKE_RUNNING,
        current_step=intake_step,
        timeline=timeline,
    )
    structured_brief = build_structured_brief(run.template_input, documents)
    intake_note = generate_validated(
        provider,
        agent_key=INTAKE_AGENT.key,
        system_prompt=INTAKE_AGENT.system_prompt,
        user_prompt=intake_prompt(run.template_input, documents),
        max_tokens=OUTPUT_LIMITS["intake"],
        on_retry=retry_callback(run.run_id, "intake", intake_step),
        kind="intake",
        stage_label=intake_step,
    )
    ensure_not_canceled(run.run_id)
    structured_brief.intake_synthesis = intake_note
    structured_brief.opportunity_points.append("入口 Agent 已整合模板和上传文档,讨论组以入口整合 briefing 为准。")
    timeline = finish_timeline_step(timeline, "intake")
    run = update_run_checked(run.run_id, structured_brief=structured_brief, timeline=timeline)

    messages: list[DebateMessage] = []
    timeline = start_timeline_step(timeline, "handoff")
    run = update_run_checked(
        run.run_id,
        status=RunStatus.DEBATE_RUNNING,
        current_step="信息传送到讨论组",
        timeline=timeline,
    )
    timeline = finish_timeline_step(timeline, "handoff")
    run = update_run_checked(run.run_id, timeline=timeline)
    if parallel_first_round:
        messages, timeline, run = run_first_round_in_parallel(
            run,
            structured_brief,
            provider,
            messages,
            timeline,
        )
    else:
        messages, timeline, run = run_debate_round_serial(
            run,
            structured_brief,
            provider,
            messages,
            timeline,
            1,
        )

    timeline = start_timeline_step(timeline, "moderator_round1")
    run = update_run_checked(
        run.run_id,
        current_step="Moderator 汇总第 1 轮冲突与遗漏",
        timeline=timeline,
    )
    moderator_note = generate_validated(
        provider,
        agent_key=MODERATOR_AGENT.key,
        system_prompt=MODERATOR_AGENT.system_prompt,
        user_prompt=moderator_prompt(run.template_input, structured_brief, messages, run.research_stage),
        max_tokens=OUTPUT_LIMITS["moderator"],
        on_retry=retry_callback(run.run_id, "moderator_round1", "Moderator 汇总第 1 轮冲突与遗漏"),
        kind="moderator",
        stage_label="Moderator 汇总第 1 轮冲突与遗漏",
    )
    ensure_not_canceled(run.run_id)
    messages.append(
        DebateMessage(
            round=1,
            agent=MODERATOR_AGENT.display_name,
            title=f"第 1 轮 · {MODERATOR_AGENT.role}",
            content=moderator_note,
            model_label=provider.label_for(MODERATOR_AGENT.key),
            ir_summary=_extract_ir_summary(moderator_note),
            claims=_extract_claims(moderator_note),
            concerns=_extract_concerns(moderator_note),
        )
    )
    timeline = finish_timeline_step(timeline, "moderator_round1")
    run = update_run_checked(run.run_id, debate_messages=messages, timeline=timeline)

    for round_number in range(2, rounds + 1):
        messages, timeline, run = run_debate_round_serial(
            run,
            structured_brief,
            provider,
            messages,
            timeline,
            round_number,
        )

    timeline = start_timeline_step(timeline, "group_summary")
    run = update_run_checked(
        run.run_id,
        status=RunStatus.GROUP_SUMMARY_RUNNING,
        current_step=f"结构化 IR({provider.label_for(GROUP_SUMMARIZER.key)})",
        timeline=timeline,
    )
    group_summary = generate_validated(
        provider,
        agent_key=GROUP_SUMMARIZER.key,
        system_prompt=GROUP_SUMMARIZER.system_prompt,
        user_prompt=summary_prompt(run.template_input, structured_brief, messages, run.research_stage),
        max_tokens=OUTPUT_LIMITS["group_summary"],
        on_retry=retry_callback(run.run_id, "group_summary", "结构化 IR"),
        kind="group_summary",
        stage_label="结构化 IR",
    )
    ensure_not_canceled(run.run_id)
    structured_ir = parse_structured_ir_v2(group_summary, run.template_input, structured_brief, messages)
    group_summary = clean_structured_ir_markdown(group_summary)
    ir_warnings = validate_structured_ir(structured_ir) if structured_ir else []
    timeline = finish_timeline_step(timeline, "group_summary")
    run = update_run_checked(
        run.run_id,
        group_summary=group_summary,
        structured_ir=structured_ir,
        ir_warnings=ir_warnings,
        timeline=timeline,
    )

    timeline = start_timeline_step(timeline, "final_report")
    run = update_run_checked(
        run.run_id,
        status=RunStatus.FINAL_REPORT_RUNNING,
        current_step=f"出口模型生成最终报告({provider.label_for(OUTPUT_AGENT.key)})",
        timeline=timeline,
    )
    final_report = clean_final_report(generate_validated(
        provider,
        agent_key=OUTPUT_AGENT.key,
        system_prompt=OUTPUT_AGENT.system_prompt,
        user_prompt=report_prompt(run.template_input, structured_brief, messages, group_summary, structured_ir, run.research_stage),
        max_tokens=OUTPUT_LIMITS["final_report"],
        on_retry=retry_callback(run.run_id, "final_report", "出口模型生成最终报告"),
        kind="final_report",
        stage_label="出口模型生成最终报告",
    ))
    ensure_not_canceled(run.run_id)
    timeline = finish_timeline_step(timeline, "final_report")
    timeline = finish_timeline_step(timeline, "overall")
    return update_run_checked(
        run.run_id,
        status=RunStatus.COMPLETED,
        final_report=final_report,
        current_step="运行完成",
        timeline=timeline,
    )


def run_intake_step(
    run: RunRecord,
    provider: ModelProvider,
    documents: list[UploadedDocument],
    timeline: list[TimelineStep],
) -> tuple[StructuredBrief, list[TimelineStep], RunRecord]:
    documents, timeline, run = summarize_documents_if_needed(run, provider, documents, timeline)
    timeline = start_timeline_step(timeline, "intake")
    intake_step = f"入口 Agent 整理模板与上传文档({provider.label_for(INTAKE_AGENT.key)})"
    run = update_run_checked(
        run.run_id,
        status=RunStatus.INTAKE_RUNNING,
        current_step=intake_step,
        timeline=timeline,
    )
    structured_brief = build_structured_brief(run.template_input, documents)
    intake_note = generate_validated(
        provider,
        agent_key=INTAKE_AGENT.key,
        system_prompt=INTAKE_AGENT.system_prompt,
        user_prompt=intake_prompt(run.template_input, documents),
        max_tokens=OUTPUT_LIMITS["intake"],
        on_retry=retry_callback(run.run_id, "intake", intake_step),
        kind="intake",
        stage_label=intake_step,
    )
    ensure_not_canceled(run.run_id)
    structured_brief.intake_synthesis = intake_note
    structured_brief.opportunity_points.append("入口 Agent 已整合模板和上传文档,讨论组以入口整合 briefing 为准。")
    timeline = finish_timeline_step(timeline, "intake")
    run = update_run_checked(run.run_id, structured_brief=structured_brief, timeline=timeline)
    return structured_brief, timeline, run


def ensure_handoff_step(timeline: list[TimelineStep]) -> list[TimelineStep]:
    if timeline_step_status(timeline, "handoff") == "completed":
        return timeline
    timeline = start_timeline_step(timeline, "handoff")
    return finish_timeline_step(timeline, "handoff")


def run_debate_agent(
    run: RunRecord,
    structured_brief: StructuredBrief,
    provider: ModelProvider,
    messages: list[DebateMessage],
    timeline: list[TimelineStep],
    round_number: int,
    agent: AgentSpec,
    *,
    independent_first_round: bool = False,
) -> tuple[list[DebateMessage], list[TimelineStep], RunRecord]:
    ensure_not_canceled(run.run_id)
    step_key = debate_step_key(round_number, agent)
    current_step = (
        f"{agent.display_name} 独立发言(第 1 轮)"
        if independent_first_round
        else f"{agent.display_name} 发言(第 {round_number} 轮)"
    )
    timeline = start_timeline_step(timeline, step_key)
    run = update_run_checked(
        run.run_id,
        status=RunStatus.DEBATE_RUNNING,
        current_step=current_step,
        timeline=timeline,
    )
    content = generate_validated(
        provider,
        agent_key=agent.key,
        system_prompt=agent.system_prompt,
        user_prompt=debate_prompt(
            template=run.template_input,
            brief=structured_brief,
            round_number=round_number,
            agent=agent,
            history=[] if independent_first_round else messages,
            independent_first_round=independent_first_round,
            research_stage=run.research_stage,
        ),
        max_tokens=OUTPUT_LIMITS["debate"],
        on_retry=retry_callback(run.run_id, step_key, current_step),
        kind="debate",
        stage_label=current_step,
    )
    ensure_not_canceled(run.run_id)
    messages.append(debate_message(round_number, agent, content, provider))
    timeline = finish_timeline_step(timeline, step_key)
    run = update_run_checked(run.run_id, debate_messages=messages, timeline=timeline)
    return messages, timeline, run


def run_moderator_step(
    run: RunRecord,
    structured_brief: StructuredBrief,
    provider: ModelProvider,
    messages: list[DebateMessage],
    timeline: list[TimelineStep],
) -> tuple[list[DebateMessage], list[TimelineStep], RunRecord]:
    timeline = start_timeline_step(timeline, "moderator_round1")
    run = update_run_checked(
        run.run_id,
        status=RunStatus.DEBATE_RUNNING,
        current_step="Moderator 汇总第 1 轮冲突与遗漏",
        timeline=timeline,
    )
    moderator_note = generate_validated(
        provider,
        agent_key=MODERATOR_AGENT.key,
        system_prompt=MODERATOR_AGENT.system_prompt,
        user_prompt=moderator_prompt(run.template_input, structured_brief, messages, run.research_stage),
        max_tokens=OUTPUT_LIMITS["moderator"],
        on_retry=retry_callback(run.run_id, "moderator_round1", "Moderator 汇总第 1 轮冲突与遗漏"),
        kind="moderator",
        stage_label="Moderator 汇总第 1 轮冲突与遗漏",
    )
    ensure_not_canceled(run.run_id)
    messages.append(
        DebateMessage(
            round=1,
            agent=MODERATOR_AGENT.display_name,
            title=f"第 1 轮 · {MODERATOR_AGENT.role}",
            content=moderator_note,
            model_label=provider.label_for(MODERATOR_AGENT.key),
            ir_summary=_extract_ir_summary(moderator_note),
            claims=_extract_claims(moderator_note),
            concerns=_extract_concerns(moderator_note),
        )
    )
    timeline = finish_timeline_step(timeline, "moderator_round1")
    run = update_run_checked(run.run_id, debate_messages=messages, timeline=timeline)
    return messages, timeline, run


def run_group_summary_step(
    run: RunRecord,
    structured_brief: StructuredBrief,
    provider: ModelProvider,
    messages: list[DebateMessage],
    timeline: list[TimelineStep],
) -> tuple[str, list[TimelineStep], RunRecord]:
    timeline = start_timeline_step(timeline, "group_summary")
    run = update_run_checked(
        run.run_id,
        status=RunStatus.GROUP_SUMMARY_RUNNING,
        current_step=f"结构化 IR({provider.label_for(GROUP_SUMMARIZER.key)})",
        timeline=timeline,
    )
    group_summary = generate_validated(
        provider,
        agent_key=GROUP_SUMMARIZER.key,
        system_prompt=GROUP_SUMMARIZER.system_prompt,
        user_prompt=summary_prompt(run.template_input, structured_brief, messages, run.research_stage),
        max_tokens=OUTPUT_LIMITS["group_summary"],
        on_retry=retry_callback(run.run_id, "group_summary", "结构化 IR"),
        kind="group_summary",
        stage_label="结构化 IR",
    )
    ensure_not_canceled(run.run_id)
    structured_ir = parse_structured_ir_v2(group_summary, run.template_input, structured_brief, messages)
    group_summary = clean_structured_ir_markdown(group_summary)
    ir_warnings = validate_structured_ir(structured_ir) if structured_ir else []
    timeline = finish_timeline_step(timeline, "group_summary")
    run = update_run_checked(run.run_id, group_summary=group_summary, structured_ir=structured_ir, ir_warnings=ir_warnings, timeline=timeline)
    return group_summary, timeline, run


def run_final_report_step(
    run: RunRecord,
    structured_brief: StructuredBrief,
    provider: ModelProvider,
    messages: list[DebateMessage],
    group_summary: str,
    timeline: list[TimelineStep],
) -> tuple[str, list[TimelineStep], RunRecord]:
    timeline = start_timeline_step(timeline, "final_report")
    run = update_run_checked(
        run.run_id,
        status=RunStatus.FINAL_REPORT_RUNNING,
        current_step=f"出口模型生成最终报告({provider.label_for(OUTPUT_AGENT.key)})",
        timeline=timeline,
    )
    final_report = clean_final_report(generate_validated(
        provider,
        agent_key=OUTPUT_AGENT.key,
        system_prompt=OUTPUT_AGENT.system_prompt,
        user_prompt=report_prompt(
            run.template_input,
            structured_brief,
            messages,
            group_summary,
            run.structured_ir,
            run.research_stage,
        ),
        max_tokens=OUTPUT_LIMITS["final_report"],
        on_retry=retry_callback(run.run_id, "final_report", "出口模型生成最终报告"),
        kind="final_report",
        stage_label="出口模型生成最终报告",
    ))
    ensure_not_canceled(run.run_id)
    timeline = finish_timeline_step(timeline, "final_report")
    timeline = finish_timeline_step(timeline, "overall")
    run = update_run_checked(
        run.run_id,
        status=RunStatus.COMPLETED,
        final_report=final_report,
        current_step="运行完成",
        timeline=timeline,
    )
    return final_report, timeline, run


def run_debate_round_serial(
    run: RunRecord,
    structured_brief: StructuredBrief,
    provider: ModelProvider,
    messages: list[DebateMessage],
    timeline: list[TimelineStep],
    round_number: int,
) -> tuple[list[DebateMessage], list[TimelineStep], RunRecord]:
    for agent in DISCUSSION_AGENTS:
        ensure_not_canceled(run.run_id)
        current_step = f"{agent.display_name} 发言(第 {round_number} 轮)"
        step_key = debate_step_key(round_number, agent)
        timeline = start_timeline_step(timeline, step_key)
        run = update_run_checked(run.run_id, current_step=current_step, timeline=timeline)
        content = generate_validated(
            provider,
            agent_key=agent.key,
            system_prompt=agent.system_prompt,
            user_prompt=debate_prompt(
                template=run.template_input,
                brief=structured_brief,
                round_number=round_number,
                agent=agent,
                history=messages,
                independent_first_round=False,
                research_stage=run.research_stage,
            ),
            max_tokens=OUTPUT_LIMITS["debate"],
            on_retry=retry_callback(run.run_id, step_key, current_step),
            kind="debate",
            stage_label=current_step,
        )
        ensure_not_canceled(run.run_id)
        messages.append(debate_message(round_number, agent, content, provider))
        timeline = finish_timeline_step(timeline, step_key)
        run = update_run_checked(run.run_id, debate_messages=messages, timeline=timeline)
    return messages, timeline, run


def run_first_round_in_parallel(
    run: RunRecord,
    structured_brief: StructuredBrief,
    provider: ModelProvider,
    messages: list[DebateMessage],
    timeline: list[TimelineStep],
) -> tuple[list[DebateMessage], list[TimelineStep], RunRecord]:
    futures = {}
    for agent in DISCUSSION_AGENTS:
        timeline = start_timeline_step(timeline, debate_step_key(1, agent))
    run = update_run_checked(
        run.run_id,
        current_step="第 1 轮并行独立发言",
        timeline=timeline,
    )
    with ThreadPoolExecutor(max_workers=len(DISCUSSION_AGENTS)) as executor:
        for agent in DISCUSSION_AGENTS:
            futures[
                executor.submit(
                    generate_validated,
                    provider,
                    agent_key=agent.key,
                    system_prompt=agent.system_prompt,
                    user_prompt=debate_prompt(
                        template=run.template_input,
                        brief=structured_brief,
                        round_number=1,
                        agent=agent,
                        history=[],
                        independent_first_round=True,
                        research_stage=run.research_stage,
                    ),
                    max_tokens=OUTPUT_LIMITS["debate"],
                    on_retry=retry_callback(
                        run.run_id,
                        debate_step_key(1, agent),
                        f"{agent.display_name} 独立发言(第 1 轮)",
                    ),
                    kind="debate",
                    stage_label=f"{agent.display_name} 独立发言(第 1 轮)",
                )
            ] = agent
        for future in as_completed(futures):
            ensure_not_canceled(run.run_id)
            agent = futures[future]
            current_step = f"{agent.display_name} 发言(第 1 轮)"
            try:
                content = future.result()
            except Exception as exc:
                run = update_run_checked(run.run_id, current_step=current_step)
                raise RuntimeError(f"{current_step}失败:{exc}") from exc
            ensure_not_canceled(run.run_id)
            messages.append(debate_message(1, agent, content, provider))
            timeline = finish_timeline_step(timeline, debate_step_key(1, agent))
            run = update_run_checked(
                run.run_id,
                current_step="第 1 轮并行独立发言",
                debate_messages=messages,
                timeline=timeline,
            )
    return messages, timeline, run


def debate_message(
    round_number: int,
    agent: AgentSpec,
    content: str,
    provider: ModelProvider,
) -> DebateMessage:
    return DebateMessage(
        round=round_number,
        agent=agent.display_name,
        title=f"第 {round_number} 轮 · {agent.role}",
        content=content,
        model_label=provider.label_for(agent.key),
        ir_summary=_extract_ir_summary(content),
        claims=_extract_claims(content),
        concerns=_extract_concerns(content),
    )


def debate_step_key(round_number: int, agent: AgentSpec) -> str:
    return f"debate_r{round_number}_{agent.key}"


def build_timeline(
    rounds: int,
    parallel_first_round: bool = False,
    documents: list[UploadedDocument] | None = None,
) -> list[TimelineStep]:
    intake_estimate = estimate_intake_seconds(documents or [])
    needs_doc_extract = needs_hybrid_intake(documents or [])
    steps = [
        TimelineStep(
            key="overall",
            label="整体头脑风暴",
            status="running",
            started_at=now_iso(),
            is_overall=True,
        ),
        TimelineStep(key="template", label="创建运行并校验模板"),
        *(
            [TimelineStep(key="doc_extract", label="预提取上传文档摘要", estimate_seconds=STEP_ESTIMATES["doc_extract"])]
            if needs_doc_extract
            else []
        ),
        TimelineStep(
            key="intake",
            label="入口模型整理模板与上传文档",
            estimate_seconds=intake_estimate,
        ),
        TimelineStep(key="handoff", label="信息传送到讨论组"),
    ]
    for round_number in range(1, rounds + 1):
        for agent in DISCUSSION_AGENTS:
            steps.append(
                TimelineStep(
                    key=debate_step_key(round_number, agent),
                    label=(
                        f"{agent.display_name} 独立发言(第 1 轮)"
                        if parallel_first_round and round_number == 1
                        else f"{agent.display_name} 发言(第 {round_number} 轮)"
                    ),
                )
            )
        if round_number == 1:
            steps.append(TimelineStep(key="moderator_round1", label="Moderator 汇总第 1 轮冲突与遗漏"))
    steps.extend(
        [
            TimelineStep(key="group_summary", label="结构化 IR", estimate_seconds=180),
            TimelineStep(key="final_report", label="出口模型生成最终报告", estimate_seconds=240),
        ]
    )
    return reschedule_timeline(steps)


def prepare_timeline_for_resume(
    timeline: list[TimelineStep],
    rounds: int,
    parallel_first_round: bool = False,
    documents: list[UploadedDocument] | None = None,
) -> list[TimelineStep]:
    existing = {step.key: step for step in timeline}
    prepared: list[TimelineStep] = []
    for expected in build_timeline(rounds, parallel_first_round, documents):
        current = existing.get(expected.key)
        if current is None:
            prepared.append(expected)
            continue
        if current.status == "completed":
            prepared.append(current)
            continue
        if current.key == "overall":
            prepared.append(
                expected.model_copy(
                    update={
                        "status": "running",
                        "started_at": current.started_at or expected.started_at,
                        "finished_at": "",
                    }
                )
            )
            continue
        prepared.append(
            expected.model_copy(
                update={
                    "status": "pending",
                    "started_at": "",
                    "finished_at": "",
                    "estimated_done_at": "",
                }
            )
        )
    return reschedule_timeline(prepared)


def timeline_step_status(timeline: list[TimelineStep], key: str) -> str:
    step = next((item for item in timeline if item.key == key), None)
    return step.status if step else "pending"


def has_agent_message(messages: list[DebateMessage], round_number: int, agent: AgentSpec) -> bool:
    return any(
        message.round == round_number and message.agent == agent.display_name
        for message in messages
    )


def estimate_intake_seconds(documents: list[UploadedDocument]) -> int:
    total_chars = total_document_chars(documents)
    if total_chars <= 0:
        return STEP_ESTIMATES["intake"]
    if needs_hybrid_intake(documents):
        summary_chars = min(INTAKE_DOC_SUMMARY_BUDGET, len(documents) * DOC_SUMMARY_MAX_CHARS)
        extra_blocks = (summary_chars + 3999) // 4000
        return min(720, STEP_ESTIMATES["intake"] + extra_blocks * 45)
    extra_blocks = (total_chars + 5999) // 6000
    return min(900, STEP_ESTIMATES["intake"] + extra_blocks * 90)


def start_timeline_step(timeline: list[TimelineStep], key: str) -> list[TimelineStep]:
    now = now_iso()
    updated = []
    for step in timeline:
        if step.key == key and step.status == "pending":
            step = step.model_copy(update={"status": "running", "started_at": now})
        updated.append(step)
    return reschedule_timeline(updated)


def finish_timeline_step(timeline: list[TimelineStep], key: str) -> list[TimelineStep]:
    now = now_iso()
    updated = []
    for step in timeline:
        if step.key == key:
            step = step.model_copy(update={"status": "completed", "finished_at": now})
        updated.append(step)
    return reschedule_timeline(updated)


def update_timeline_label(timeline: list[TimelineStep], key: str, label: str) -> list[TimelineStep]:
    updated = []
    for step in timeline:
        if step.key == key:
            step = step.model_copy(update={"label": label})
        updated.append(step)
    return reschedule_timeline(updated)


def retry_callback(run_id: str, step_key: str, base_label: str):
    def _callback(attempt: int, max_retries: int, reason: str) -> None:
        label = f"{base_label}(第 {attempt}/{max_retries} 次重试:{reason})"
        try:
            latest = db.get_run(run_id)
            timeline = update_timeline_label(latest.timeline, step_key, label)
            db.update_run(run_id, current_step=label, timeline=timeline)
        except Exception:
            pass

    return _callback


def fail_timeline_step(timeline: list[TimelineStep], current_label: str) -> list[TimelineStep]:
    now = now_iso()
    updated = []
    failed = False
    for step in timeline:
        if step.status == "running" or (not failed and step.label == current_label):
            step = step.model_copy(update={"status": "failed", "finished_at": now})
            failed = True
        if step.key == "overall":
            step = step.model_copy(update={"status": "failed", "finished_at": now})
        updated.append(step)
    return reschedule_timeline(updated)


def cancel_timeline_step(timeline: list[TimelineStep]) -> list[TimelineStep]:
    now = now_iso()
    updated = []
    for step in timeline:
        if step.key == "overall":
            step = step.model_copy(update={"status": "canceled", "finished_at": now})
        elif step.status == "running":
            step = step.model_copy(update={"status": "canceled", "finished_at": now})
        updated.append(step)
    return reschedule_timeline(updated)


def reschedule_timeline(timeline: list[TimelineStep]) -> list[TimelineStep]:
    anchor = now_dt()
    for step in timeline:
        if step.is_overall:
            if not step.started_at:
                step.started_at = now_iso(anchor)
            continue
        if step.status == "completed" and step.finished_at:
            anchor = parse_iso(step.finished_at)
            continue
        if step.status in {"failed", "canceled"} and step.finished_at:
            anchor = parse_iso(step.finished_at)
            continue
        if step.status == "running":
            if not step.started_at:
                step.started_at = now_iso(anchor)
            estimated = parse_iso(step.started_at) + timedelta(seconds=estimate_for_step(step))
            step.estimated_done_at = now_iso(estimated)
            anchor = estimated
            continue
        estimated = anchor + timedelta(seconds=estimate_for_step(step))
        step.estimated_done_at = now_iso(estimated)
        anchor = estimated

    overall = next((step for step in timeline if step.key == "overall"), None)
    if overall:
        if all(step.status == "completed" for step in timeline if not step.is_overall):
            overall.status = "completed"
            overall.finished_at = next(
                (step.finished_at for step in reversed(timeline) if not step.is_overall and step.finished_at),
                now_iso(),
            )
        elif any(step.status == "failed" for step in timeline if not step.is_overall):
            overall.status = "failed"
        elif any(step.status == "canceled" for step in timeline if not step.is_overall):
            overall.status = "canceled"
        else:
            overall.status = "running"
        if overall.status != "completed":
            overall.estimated_done_at = now_iso(anchor)
    return timeline


def estimate_for_step(step: TimelineStep) -> int:
    if step.estimate_seconds:
        return step.estimate_seconds
    if step.key.startswith("debate_"):
        return STEP_ESTIMATES["debate"]
    return STEP_ESTIMATES.get(step.key, 60)


def now_dt() -> datetime:
    return datetime.now(UTC)


def now_iso(value: datetime | None = None) -> str:
    return (value or now_dt()).isoformat()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def build_structured_brief(
    template: TemplateInput,
    documents: list[UploadedDocument] | None = None,
) -> StructuredBrief:
    documents = documents or []
    known_facts = [
        item
        for item in [
            f"研究领域为:{template.field}",
            f"已有研究基础:{template.existing_basis}",
            f"可用技术平台:{template.platforms}" if template.platforms else "",
            f"目标产出:{template.target_output}" if template.target_output else "",
        ]
        if item
    ]
    for document in documents:
        summary_hint = f",摘要:{_compact(document.summary, 120)}" if document.summary else ""
        known_facts.append(
            f"上传文档:{document.name}({document.doc_type}),注释:{document.note or '无'}{summary_hint}"
        )
    unknowns = [
        item
        for item in [
            template.core_question or "核心科学问题尚需从背景和已有基础中进一步提炼。",
            "创新边界、关键机制链条和最小验证实验仍需讨论组收敛。",
        ]
        if item
    ]
    constraints = [
        item.strip()
        for item in template.constraints.replace(";", ";").split(";")
        if item.strip()
    ] or ["用户暂未提供明确资源限制,讨论中需要主动提示周期、经费、样本和平台风险。"]
    opportunity_points = [
        item
        for item in [
            template.extension_points,
            f"偏好方向:{template.preferred_direction}" if template.preferred_direction else "",
            f"避免方向:{template.avoid_direction}" if template.avoid_direction else "",
        ]
        if item
    ]
    return StructuredBrief(
        research_context=template.background,
        known_facts=known_facts,
        unknowns=unknowns,
        constraints=constraints,
        opportunity_points=opportunity_points,
    )


def _document_window(content: str) -> str:
    text = (content or "").strip()
    if len(text) <= DOC_EXTRACT_HEAD_CHARS + DOC_EXTRACT_TAIL_CHARS:
        return text
    head = text[:DOC_EXTRACT_HEAD_CHARS].rstrip()
    tail = text[-DOC_EXTRACT_TAIL_CHARS:].lstrip()
    return f"{head}\n\n[...中间内容已省略以控制 intake 成本...]\n\n{tail}"


def total_document_chars(documents: list[UploadedDocument]) -> int:
    return sum(len((document.content or "").strip()) for document in documents)


def needs_hybrid_intake(documents: list[UploadedDocument]) -> bool:
    return total_document_chars(documents) > DOC_INLINE_THRESHOLD_CHARS


def document_extract_prompt(document: UploadedDocument) -> str:
    excerpt = _document_window(document.content or "") or "无可读取文本"
    return f"""
请为入口 briefing 提取单份文档摘要,目标是服务后续科研讨论,而不是复写全文。

文档名称:{document.name}
文档类型:{document.doc_type}
用户注释:{document.note or '无'}

文档内容窗口:
<document>
{excerpt}
</document>

输出要求:
1. 只保留对科研选题/方案推进必要的信息。
2. 优先提取:研究目标、实验设计、关键数据/现象、已验证结论、限制条件、待验证问题。
3. 删除重复背景和无关细节,不编造文档中不存在的数据。
4. 输出 5-8 条中文短 bullet,每条尽量 30-80 字,总长度控制在 180-420 中文字。
5. 最后一行必须输出:<<<END_OF_DOC_EXTRACT>>>
""".strip()


def _fallback_doc_summary(document: UploadedDocument) -> str:
    excerpt = _document_window(document.content or "") or "无可读取文本"
    lines = [l.strip() for l in excerpt.splitlines() if l.strip()]
    preview = "\n".join(lines[:6])
    return f"[摘要提取失败,以下为原文头尾裁切片段]\n{preview}".strip()


def _is_tabular_document(document: UploadedDocument) -> bool:
    name = (document.name or "").lower()
    if name.endswith((".csv", ".tsv", ".tsv.gz", ".csv.gz")):
        return True
    if document.doc_type == "experiment-data":
        content = (document.content or "")[:4000]
        lines = [l for l in content.splitlines() if l.strip()]
        if len(lines) >= 3:
            sep_counts = [l.count(",") + l.count("\t") for l in lines[:5]]
            if all(c >= 2 for c in sep_counts):
                return True
    return False


def _deterministic_table_summary(document: UploadedDocument) -> str:
    content = (document.content or "").strip()
    if not content:
        return "[空文档]"
    lines = content.splitlines()
    total_rows = len(lines)
    sep = "\t" if "\t" in (lines[0] if lines else "") else ","
    header = lines[0].strip() if lines else ""
    columns = [c.strip().strip('"') for c in header.split(sep)] if header else []
    sample_head = "\n".join(lines[:4])
    sample_tail = "\n".join(lines[-3:]) if total_rows > 6 else ""
    parts = [
        f"表格维度:{total_rows} 行 × {len(columns)} 列",
        f"列名:{', '.join(columns[:20])}" if columns else "",
    ]
    if document.note and document.note.strip():
        parts.append(f"用户注释:{document.note.strip()}")
    parts.append(f"头部示例:\n{sample_head}")
    if sample_tail:
        parts.append(f"尾部示例:\n{sample_tail}")
    return "\n".join(p for p in parts if p)


def summarize_documents_if_needed(
    run: RunRecord,
    provider: ModelProvider,
    documents: list[UploadedDocument],
    timeline: list[TimelineStep],
) -> tuple[list[UploadedDocument], list[TimelineStep], RunRecord]:
    if not documents or not needs_hybrid_intake(documents):
        return documents, timeline, run

    step_key = "doc_extract"
    timeline = start_timeline_step(timeline, step_key)
    run = update_run_checked(
        run.run_id,
        status=RunStatus.INTAKE_RUNNING,
        current_step="预提取上传文档摘要",
        timeline=timeline,
    )

    summarized: list[UploadedDocument] = [document.model_copy(deep=True) for document in documents]
    # Phase 1: deterministic table summaries (no LLM needed)
    for i, document in enumerate(summarized):
        if not (document.summary or "").strip() and _is_tabular_document(document):
            summarized[i] = summarized[i].model_copy(
                update={"summary": _compact(_deterministic_table_summary(document), DOC_SUMMARY_MAX_CHARS)}
            )
    run = update_run_checked(run.run_id, documents=summarized)
    # Phase 2: LLM-based summaries for remaining non-tabular docs
    pending_indices = [index for index, document in enumerate(summarized) if not (document.summary or "").strip()]
    if not pending_indices:
        timeline = finish_timeline_step(timeline, step_key)
        run = update_run_checked(run.run_id, documents=summarized, timeline=timeline)
        return summarized, timeline, run

    max_workers = min(2, max(1, len(pending_indices)))
    futures = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for index in pending_indices:
            document = summarized[index]
            futures[
                executor.submit(
                    generate_validated,
                    provider,
                    agent_key=INTAKE_AGENT.key,
                    system_prompt=INTAKE_AGENT.system_prompt,
                    user_prompt=document_extract_prompt(document),
                    max_tokens=OUTPUT_LIMITS["doc_extract"],
                    on_retry=retry_callback(run.run_id, step_key, f"预提取上传文档摘要({document.name})"),
                    kind="doc_extract",
                    stage_label=f"文档摘要提取:{document.name}",
                )
            ] = index
        for future in as_completed(futures):
            ensure_not_canceled(run.run_id)
            index = futures[future]
            try:
                summary = future.result()
            except Exception as exc:
                document = summarized[index]
                summary = _fallback_doc_summary(document)
            summarized[index] = summarized[index].model_copy(update={"summary": _compact(summary, DOC_SUMMARY_MAX_CHARS)})
            run = update_run_checked(run.run_id, documents=summarized)

    timeline = finish_timeline_step(timeline, step_key)
    run = update_run_checked(run.run_id, documents=summarized, timeline=timeline)
    return summarized, timeline, run


def budget_document_summaries(documents: list[UploadedDocument], max_chars: int = INTAKE_DOC_SUMMARY_BUDGET) -> list[str]:
    entries = []
    for document in documents:
        payload = "\n".join(
            item
            for item in [
                f"文档名称:{document.name}",
                f"文档类型:{document.doc_type}",
                f"用户注释:{document.note or '无'}",
                f"摘要:{document.summary}" if document.summary else "",
            ]
            if item
        )
        if payload:
            entries.append(payload)
    if not entries:
        return []

    kept: list[str] = []
    used = 0
    for entry in entries:
        if used + len(entry) <= max_chars:
            kept.append(entry)
            used += len(entry)
            continue
        remaining = max_chars - used
        if remaining <= 120:
            break
        kept.append(_compact(entry, remaining))
        break
    return kept


def intake_prompt(template: TemplateInput, documents: list[UploadedDocument]) -> str:
    use_hybrid = needs_hybrid_intake(documents)
    if use_hybrid:
        document_entries = budget_document_summaries(documents)
        document_text = "\n\n".join(document_entries)
        intake_source_note = "以下内容为上传文档的预提取摘要与用户注释,不再包含文档全文。"
        reading_requirement = "请基于模板 + 文档摘要形成高密度入口 briefing;如果文档摘要中信息不足,请明确保留不确定性。"
    else:
        document_text = "\n\n".join(
            [
                "\n".join(
                    [
                        f"文档名称:{document.name}",
                        f"文档类型:{document.doc_type}",
                        f"用户注释:{document.note or '无'}",
                        "文档全文如下:",
                        "<document>",
                        document.content or "无可读取文本",
                        "</document>",
                    ]
                )
                for document in documents
            ]
        )
        intake_source_note = "以下内容包含上传文档全文。"
        reading_requirement = "请完整阅读用户模板和所有上传文档,形成一份只供讨论组使用的入口整合 briefing。"
    return f"""
{template_prompt(template)}

上传文档:
{intake_source_note}
{document_text or '无上传文档。'}

{reading_requirement}
要求:
1. 先分别提炼 design、experiment-data、other 文档中的关键事实、实验设计、已有结果、限制条件和待验证点。
2. 再合并用户模板,整理成可靠、可控、尽量不流失重点的前置信息。
3. 明确区分"已知事实""用户设想""从文档推断的机会点""仍不确定的问题"。
4. 不得编造文档中不存在的数据或结论。
5. 输出中文 Markdown,结构清晰,供后续讨论 Agent 直接使用;后续讨论组不会再看到文档全文。
6. 严格控制长度:优先高密度信息,不写长篇报告;建议 1800-3000 中文字,最多不超过 4000 中文字。
7. 对每份上传文档只保留对选题讨论必要的信息:核心设计、关键数据、已验证结论、约束和待验证问题;删除重复背景和无关细节。
8. 最后一行必须输出:<<<END_OF_INTAKE>>>
""".strip()


def template_prompt(template: TemplateInput) -> str:
    return "\n".join(
        [
            f"研究领域:{template.field}",
            f"实验大背景:{template.background}",
            f"已有研究基础:{template.existing_basis}",
            f"初步想法:{template.extension_points}",
            f"核心科学问题:{template.core_question}",
            f"可用技术平台:{template.platforms}",
            f"资源限制:{template.constraints}",
            f"目标产出:{template.target_output}",
            f"偏好方向:{template.preferred_direction}",
            f"避免方向:{template.avoid_direction}",
        ]
    )


def debate_prompt(
    *,
    template: TemplateInput,
    brief: StructuredBrief,
    round_number: int,
    agent: AgentSpec,
    history: list[DebateMessage],
    independent_first_round: bool = False,
    mode_context: str = "",
    research_stage: ResearchStage | str = ResearchStage.AUTO,
) -> str:
    round_tasks = {
        1: "独立提出观点,不要重复其他 Agent 的职责;本轮不需要回应其他 Agent。",
        2: "优先回应 Moderator 指出的冲突点、遗漏点,再针对前面观点进行反驳、补充和修正。",
        3: "给出最终推荐、优先级判断和可执行建议。",
    }
    history_text = _debate_history_text(history[-8:])

    # P1: R1 只保留精简 briefing,R2/R3 通过 moderator 补充的 history 获取完整上下文
    if round_number == 1:
        top_facts = ";".join(brief.known_facts[:5])
        brief_section = f"""结构化 briefing(精简):
- 研究上下文:{brief.research_context}
- 核心已知事实:{top_facts}
- 关键未知问题:{";".join(brief.unknowns[:3])}

入口 Agent 整合 briefing(以此为主要前置信息,不得假设还能读取上传文档全文):
{brief.intake_synthesis or "入口 Agent 未提供额外整合内容。"}"""
    else:
        brief_section = f"""结构化 briefing:
- 研究上下文:{brief.research_context}
- 已知事实:{";".join(brief.known_facts)}
- 未知问题:{";".join(brief.unknowns)}
- 约束:{";".join(brief.constraints)}
- 机会点:{";".join(brief.opportunity_points)}

入口 Agent 整合 briefing:
{brief.intake_synthesis or "入口 Agent 未提供额外整合内容。"}"""

    return f"""
{template_prompt(template)}

{brief_section}

当前轮次:第 {round_number} 轮
本轮任务:{round_tasks.get(round_number, "继续收敛并给出优先级判断。")}
当前 Agent:{agent.display_name} / {agent.role}
科研阶段:{research_stage_label(research_stage)}
阶段目标:{stage_goal_text(research_stage)}
执行方式:{"第 1 轮并行独立发言,不读取其他 Agent 当轮内容。" if independent_first_round else "按讨论顺序串行推进。"}

已有讨论:
{history_text or "暂无,当前 Agent 是本次讨论的早期发言者。"}

{mode_context}
全局原则:
- 若用户已提供较完整的当前课题、实验设计或实验结果,默认目标是帮助其推进、完善、诊断和创新当前路线。
- 除非当前路线存在明显结构性缺陷,否则不要把"重新推荐新课题"作为主要输出。
- 如发现更优方向偏差较大,可将其作为"转向建议"或"备选方向"提出,而不是替代当前主轴。

输出要求:
- 用中文 Markdown 输出,观点主体控制在 800-1500 字,内容具体、可执行,避免空泛套话。
- 不要逐条复述已知事实,直接给出你的判断和建议。
- 追加以下结构化小节:

### 给结构化 IR 的要点摘要
- 关键主张:
- 支撑依据:
- 风险或反驳点:
- 建议进入 IR 的下一步动作:

该小节控制在 80-150 中文字,不要复述全文。

### 外部引用
每条一行,格式:[类型] 标题 | 作者/来源 | 链接 | 年份 | 支撑的观点
类型: paper / blog / dataset / book / other
- 至少 1 条外部论据(论文、预印本、技术博客、公共数据集均可)。
- 标题必填;记不清信息时链接写"待确认"。
- 不要编造不存在的论文、作者或链接。

最后一行必须输出:<<<END_OF_AGENT_MESSAGE>>>
""".strip()


DEBATE_HISTORY_PER_AGENT_BUDGET = 3500


def _debate_history_text(messages: list[DebateMessage]) -> str:
    """Compressed debate history for R2/R3 prompts.

    Each agent's output is reduced to IR summary + claims + concerns,
    with a higher per-agent budget than moderator (agents need more detail
    for rebuttals). Falls back to head+tail excerpt if no structured fields.
    """
    parts: list[str] = []
    for message in messages:
        sections: list[str] = []
        ir = message.ir_summary or _extract_ir_summary(message.content)
        if ir:
            sections.append(f"[IR 摘要]\n{ir}")
        claims = message.claims or _extract_claims(message.content)
        if claims:
            sections.append("[核心主张]\n" + "\n".join(f"- {c}" for c in claims))
        concerns = message.concerns or _extract_concerns(message.content)
        if concerns:
            sections.append("[主要顾虑]\n" + "\n".join(f"- {c}" for c in concerns))
        if not sections:
            sections.append("[全文裁切]\n" + _compact(message.content, DEBATE_HISTORY_PER_AGENT_BUDGET))
        body = "\n\n".join(sections)
        if len(body) > DEBATE_HISTORY_PER_AGENT_BUDGET:
            body = body[:DEBATE_HISTORY_PER_AGENT_BUDGET] + "..."
        parts.append(f"[Round {message.round} | {message.agent}]\n{body}")
    return "\n\n".join(parts)


def moderator_prompt(
    template: TemplateInput,
    brief: StructuredBrief,
    messages: list[DebateMessage],
    research_stage: ResearchStage | str = ResearchStage.AUTO,
) -> str:
    first_round = [message for message in messages if message.round == 1]
    return f"""
请基于第 1 轮独立发言,生成 Moderator 汇总。

科研阶段:{research_stage_label(research_stage)}
阶段目标:{stage_goal_text(research_stage)}

你必须输出:
1. 各 Agent 已形成的互补点
2. 明显冲突或优先级分歧
3. 候选方向聚类:把相似想法合并成 A/B/C/D 方向,并指出哪些只是换皮重复
4. 每个候选方向的初步支持证据、最弱证据点、最大可行性风险
5. 仍缺失的信息、关键变量或实验控制
6. 第 2 轮每个 Agent 必须回应的具体问题
7. 如果当前阶段不是"选题探索",必须优先围绕用户现有课题推进;只有在发现明显方向偏差时,才把转向建议放在最后。
8. 末尾追加"### 给结构化 IR 的要点摘要",控制在 120-220 中文字,并明确列出候选方向、冲突点和待审查点。
9. 最后一行必须输出:<<<END_OF_MODERATOR_MESSAGE>>>

用户模板:
{template_prompt(template)}

入口 briefing:
{brief.intake_synthesis or brief.model_dump_json()}

第 1 轮发言(压缩摘要):
{_moderator_messages_text(first_round)}
""".strip()


def summary_prompt(
    template: TemplateInput,
    brief: StructuredBrief,
    messages: list[DebateMessage],
    research_stage: ResearchStage | str = ResearchStage.AUTO,
) -> str:
    return f"""
请基于以下模板、入口 briefing 和讨论摘要生成 V1.5 结构化 IR(Intermediate Representation)。
它不是普通总结,而是研究方向决策结构体:必须把候选方向、证据、批判点和排序理由绑定起来。

科研阶段:{research_stage_label(research_stage)}
阶段目标:{stage_goal_text(research_stage)}

输出硬性要求:
1. 必须先输出一个 ```json fenced code block,且必须是合法 JSON。
2. JSON 顶层字段必须包含:
   - version: "1.5"
   - decision_summary: 字符串
   - key_claims: 字符串数组
   - evidence_refs: 数组,每项含 id/source_type/source_id/source_title/quote_or_summary/supports
   - critique_points: 数组,每项含 id/target_id/dimension/severity/content/mitigation
   - candidate_directions: 数组,每项含 id/title/research_question/rationale/novelty/feasibility/risks/alternatives/priority/priority_reason/evidence_refs/critique_refs/next_actions
3. candidate_directions 需要 3-5 个方向;priority 用 1 表示最推荐,数字越大优先级越低。
4. 每个候选方向必须绑定至少 1 个 evidence_refs 和至少 1 个 critique_refs。
5. evidence_refs 可以来自 uploaded_document、template、intake_briefing、agent_debate;没有逐字引用时,用 quote_or_summary 写"证据摘要"。
6. critique 不能只写泛泛风险,必须进入排序判断:创新性、证据强度、可行性、资源约束、替代路线至少覆盖其中 3 类。
7. JSON 后再输出"## 结构化 IR 文档",中文 Markdown,控制在 1200-2200 中文字之间。
8. Markdown 只保留:决策摘要、候选方向排序、证据链、批判点、主要风险、替代路线、下一步动作。
9. 不要逐字复述 Agent 发言,不要生成 mermaid/graph/code block。
10. 如果当前阶段不是"选题探索",candidate_directions 应优先表达"推进路径 / 解释路径 / 诊断路径 / 调整路径",不要机械地改写成新课题名称。
11. 最后一行必须输出:<<<END_OF_GROUP_SUMMARY>>>

{template_prompt(template)}

入口 briefing 摘要:
{briefing_for_report(brief)}

讨论摘要:
{ir_feedback_text(messages)}
""".strip()


def summary_prompt_focused(
    template: TemplateInput,
    brief: StructuredBrief,
    messages: list[DebateMessage],
    research_stage: ResearchStage | str = ResearchStage.AUTO,
) -> str:
    """Focused / Memory 模式的精简 IR prompt:只要求决策摘要、核心观点和少量候选方向。"""
    return f"""
请基于以下模板、入口 briefing 和讨论摘要生成精简版结构化 IR。
本次是聚焦/追问讨论,不需要完整的选题评估,只需要提炼讨论的核心发现。

科研阶段:{research_stage_label(research_stage)}
阶段目标:{stage_goal_text(research_stage)}

输出硬性要求:
1. 必须先输出一个 ```json fenced code block,且必须是合法 JSON。
2. JSON 顶层字段必须包含:
   - version: "1.5-lite"
   - decision_summary: 字符串,本次讨论的核心结论
   - key_claims: 字符串数组,各 Agent 的关键主张
   - evidence_refs: 数组,每项含 id/source_type/source_title/quote_or_summary/supports
   - candidate_directions: 数组(2-3 个即可),每项含 id/title/rationale/evidence_refs
3. evidence_refs 尽量关联到具体的 Agent 发言或 briefing 内容。
4. JSON 后再输出中文 Markdown 摘要,控制在 600-1200 字之间,包含:核心结论、各视角要点、待解决问题。
5. 最后一行必须输出:<<<END_OF_GROUP_SUMMARY>>>

{template_prompt(template)}

入口 briefing 摘要:
{briefing_for_report(brief)}

讨论摘要:
{ir_feedback_text(messages)}
""".strip()


def report_prompt(
    template: TemplateInput,
    brief: StructuredBrief,
    messages: list[DebateMessage],
    group_summary: str,
    structured_ir: StructuredIRV2 | None = None,
    research_stage: ResearchStage | str = ResearchStage.AUTO,
) -> str:
    return f"""
请生成 K-Storm 最终 Markdown 报告。报告定位是"开题/组会科研设计讨论稿",不是只列选题的清单。

科研阶段:{research_stage_label(research_stage)}
阶段目标:{stage_goal_text(research_stage)}

必须包含以下板块:
1. 用户输入摘要:说明研究背景、已有基础、资源约束和目标产出。
2. 前置信息整合:把入口 briefing 中的已有数据、上传文档重点、可用技术平台和不能丢失的事实压缩成研究出发点。
3. 核心科学问题提炼:给出 1 个主问题和 2-4 个子问题。
4. 机制框架与可检验假设:说明变量关系、可能因果链条、关键 readout,以及哪些环节最值得验证。
5. 根据科研阶段组织主体内容:
   - 选题探索:可以输出"推荐选题 Top 3-5"。
   - 方案收敛 / 结果诊断 / 转向评估:主体应围绕当前课题推进、完善、诊断和修正,不要通篇都落在新课题命名上。
6. 如果当前阶段是选题探索,则每个 Top 方向包含题目名称、科学问题、创新点、可行性、实验路线、关键验证实验、风险点、替代方案、适合产出类型。
7. 每个核心方向或推进路径的支持证据:
   - 必须从 V1.5 决策结构体的 evidence_refs 中按 ID 提取该方向绑定的证据。
   - 每条证据写明:来源类型(template / intake_briefing / uploaded_document / agent_debate)、来源标题、引用摘要、支撑点。
   - 如果某个方向的 evidence_refs 引用了不存在的 ID,标注"证据引用异常"。
   - 如果某个方向没有任何证据绑定,标注"该方向缺乏支撑证据"并说明风险。
8. 每个核心方向或推进路径的批判审查:必须写最强创新点、最弱证据点、最大可行性风险、与已有基础匹配度、替代路线。
9. 证据链与实验设计:把 Top 方向或当前主路线串成可执行的最小实验包,说明样本/模型/分组/指标/判定标准。
10. 风险、替代路线与收敛条件:指出失败风险、资源瓶颈、阴性结果如何解释,以及何时应转向备选方案。
11. 综合优先级排序:用简短矩阵比较创新性、证据强度、可行性、周期、风险和产出潜力;排序必须与 V1.5 决策结构体一致。
12. 下一步 2-4 周行动计划:给出按周推进的具体任务。
13. 可直接用于开题/组会的表达版本:写成 2-4 段正式但不夸张的汇报表述。
14. 若当前路线与讨论结果的较优方向偏差较大,可在报告最后增加"转向建议"小节,但不要让它成为全文主轴。

长度要求:
1. 总长度控制在 4500-7000 中文字之间。
2. 不要把主要篇幅都放在 Top 选题列表;背景复盘、机制框架、证据链、实验路径、风险替代方案合计至少占全文一半。
3. 每个 Top 选题短小但完整,避免长篇综述。
4. 不要重复粘贴结构化 IR 原文,要把 IR 转化为用户可直接讨论的研究方案。

禁止输出任何对话式收尾、追加服务推荐或下一步代写邀请,例如"如果你愿意""我下一步可以""可继续整理成 PPT""基金版本"等。
报告只用于开题与组会讨论,不要主动扩展到基金申请场景,除非用户目标产出中明确写了基金。

用户模板:
{template_prompt(template)}

入口 briefing 摘要:
{briefing_for_report(brief)}

结构化 IR(已压缩,必须以此为主,不要扩写成论文全文):
{_compact(group_summary, 4200)}

V1.5 决策结构体(最终报告必须优先消费它的候选方向、证据绑定、批判点和排序理由):
{structured_ir.model_dump_json(indent=2) if structured_ir else "无结构化 JSON,仅可使用 Markdown IR。"}

讨论记录摘要(仅用于核对,不要逐字复述):
{discussion_digest(messages)}

最后一行必须输出:<<<END_OF_FINAL_REPORT>>>
""".strip()


def briefing_for_report(brief: StructuredBrief) -> str:
    return "\n".join(
        [
            f"- 研究上下文:{brief.research_context}",
            f"- 已知事实:{_join_limited(brief.known_facts, 8)}",
            f"- 未知问题:{_join_limited(brief.unknowns, 6)}",
            f"- 约束:{_join_limited(brief.constraints, 6)}",
            f"- 机会点:{_join_limited(brief.opportunity_points, 6)}",
            "- 入口模型整合摘要:",
            _compact(brief.intake_synthesis, 2400) if brief.intake_synthesis else "无额外整合摘要。",
        ]
    )


def discussion_digest(messages: list[DebateMessage]) -> str:
    parts = []
    for message in messages:
        evidence = message.claims or message.concerns
        if evidence:
            content = ";".join(evidence[:4])
        else:
            content = _compact(message.content, 500)
        parts.append(f"[Round {message.round} | {message.agent}] {content}")
    return "\n".join(parts)


def report_prompt_focused(
    template: TemplateInput,
    brief: StructuredBrief,
    messages: list[DebateMessage],
    group_summary: str,
    structured_ir: StructuredIRV2 | None = None,
    research_stage: ResearchStage | str = ResearchStage.AUTO,
) -> str:
    """Focused Panel 模式的报告 prompt:针对特定问题的深度分析,不做选题推荐。"""
    return f"""请生成聚焦分析报告。这不是选题推荐报告,而是针对特定问题的深度分析。

科研阶段:{research_stage_label(research_stage)}
阶段目标:{stage_goal_text(research_stage)}

必须包含以下板块:
1. 问题背景:简要回溯本次讨论聚焦的问题和研究上下文。
2. 各 Agent 核心观点:按 Agent 分别陈述,突出各自视角的独特贡献和关键论据。
3. 共识与分歧:明确各 Agent 之间的一致观点和冲突观点,分析冲突原因。
4. 关键证据与约束:列出本次讨论中出现的关键支撑论据和限制条件。
   - 从 V1.5 决策结构体的 evidence_refs 中按 ID 提取每条证据。
   - 每条证据写明:来源类型、来源标题、引用摘要、支撑点。
   - 如果某条 evidence_ref 引用了不存在的 ID,标注"证据引用异常"。
   - 如果某条证据为空绑定,标注"缺乏支撑证据"并说明风险。
5. 行动建议:针对讨论问题的具体下一步,2-4 条,可执行、有优先级。

长度要求:
1. 总长度控制在 2000-3500 中文字之间。
2. 重点放在各视角对比和证据分析上。
3. 不要输出选题推荐列表、优先级排序矩阵、实验设计包。

禁止输出选题推荐、开题/组会表达版本、行动计划时间表。
禁止输出任何对话式收尾。

用户模板:
{template_prompt(template)}

入口 briefing 摘要:
{briefing_for_report(brief)}

结构化 IR:
{_compact(group_summary, 3000)}

V1.5 决策结构体(按 evidence_refs ID 提取证据):
{structured_ir.model_dump_json(indent=2) if structured_ir else "无结构化 JSON。"}

讨论记录摘要(仅用于核对):
{discussion_digest(messages)}

最后一行必须输出:<<<END_OF_FINAL_REPORT>>>
""".strip()


def report_prompt_memory(
    template: TemplateInput,
    brief: StructuredBrief,
    messages: list[DebateMessage],
    group_summary: str,
    structured_ir: StructuredIRV2 | None = None,
    source_summary: str = "",
    research_stage: ResearchStage | str = ResearchStage.AUTO,
) -> str:
    """Memory Query 模式的报告 prompt:基于历史讨论的追问分析。"""
    return f"""请生成追问分析报告。这不是从零开始的选题分析,而是基于已有历史讨论对新问题的深度回答。

科研阶段:{research_stage_label(research_stage)}
阶段目标:{stage_goal_text(research_stage)}

必须包含以下板块:
1. 源讨论回顾:简要引用源讨论的核心结论(2-3 句),为读者建立上下文。
2. 新问题分析:基于记忆上下文,各 Agent 对新问题的回答和观点。
3. 与历史结论的对比:新发现 vs 已知事实,明确哪些结论被强化、哪些被修正、哪些是新出现的。
4. 更新后的判断:如果新信息改变了某些结论,明确指出改变的内容和原因;如果没有改变,说明为什么原有判断仍然成立。
5. 下一步建议:针对新问题的后续行动,2-3 条。

长度要求:
1. 总长度控制在 2000-3500 中文字之间。
2. 重点放在新旧对比和判断更新上。
3. 不要输出完整的选题推荐、从零开始的背景分析、机制框架。

禁止输出选题推荐列表、优先级排序矩阵、实验设计包、开题/组会表达版本。
禁止输出任何对话式收尾。

{"源讨论核心结论:" + source_summary if source_summary else "无源讨论信息。"}

用户模板:
{template_prompt(template)}

入口 briefing 摘要:
{briefing_for_report(brief)}

结构化 IR:
{_compact(group_summary, 3000)}

V1.5 决策结构体(按 evidence_refs ID 提取证据):
{structured_ir.model_dump_json(indent=2) if structured_ir else "无结构化 JSON。"}

讨论记录摘要(仅用于核对):
{discussion_digest(messages)}

最后一行必须输出:<<<END_OF_FINAL_REPORT>>>
""".strip()


def parse_structured_ir_v2(
    raw_text: str,
    template: TemplateInput,
    brief: StructuredBrief,
    messages: list[DebateMessage],
) -> StructuredIRV2:
    data = _extract_json_object(raw_text)
    if data:
        try:
            return StructuredIRV2.model_validate(data)
        except Exception:
            pass
    return fallback_structured_ir_v2(template, brief, messages, raw_text)


def clean_structured_ir_markdown(raw_text: str) -> str:
    # 0. Strip end markers first
    text = strip_end_markers(raw_text)
    # 1. Remove properly closed ```json ... ``` blocks
    text = re.sub(r"```json\s*.*?\s*```", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    # 2. Remove unclosed ```json ... (model hit max_tokens)
    text = re.sub(r"```json\s*", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    # 3. If model output a lone JSON object (no markdown wrapper), strip it entirely
    #    so the frontend doesn't render raw JSON
    if text.startswith("{") and '"version"' in text[:200]:
        # Pure JSON output - try to extract anything after a closing brace + markdown marker
        marker = "## 结构化 IR 文档"
        if marker in text:
            return text[text.index(marker):].strip()
        # No markdown at all - return empty so frontend shows fallback
        return ""
    # 4. Normal case: extract markdown section after marker
    marker = "## 结构化 IR 文档"
    if marker in text:
        return text[text.index(marker):].strip()
    return text


def _extract_json_object(text: str) -> dict | None:
    fenced = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    candidates = [fenced.group(1)] if fenced else []
    if not candidates:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            candidates.append(text[start:end + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def fallback_structured_ir_v2(
    template: TemplateInput,
    brief: StructuredBrief,
    messages: list[DebateMessage],
    raw_text: str,
) -> StructuredIRV2:
    # 基础证据:模板和 briefing(始终存在)
    base_evidence = [
        {
            "id": "E-template-1",
            "source_type": "template",
            "source_id": "template_input",
            "source_title": "用户模板",
            "quote_or_summary": _compact(template.existing_basis or template.background, 260),
            "supports": "研究背景、已有基础和资源约束的主依据。",
        },
        {
            "id": "E-briefing-1",
            "source_type": "intake_briefing",
            "source_id": "structured_brief",
            "source_title": "入口模型整合 briefing",
            "quote_or_summary": _compact(brief.intake_synthesis or brief.research_context, 360),
            "supports": "候选方向和实验路径的前置信息。",
        },
    ]

    # 从 discussion messages 中为不同方向提取差异化证据
    per_agent_evidence: list[dict] = []
    for idx, msg in enumerate(messages[:8]):
        content_preview = _compact(msg.content, 200)
        if not content_preview:
            continue
        per_agent_evidence.append({
            "id": f"E-debate-{idx + 1}",
            "source_type": "agent_debate",
            "source_id": f"round-{msg.round}-{msg.agent}",
            "source_title": f"{msg.agent} · 第{msg.round}轮",
            "quote_or_summary": content_preview,
            "supports": f"{msg.agent} 在讨论中提出的相关论据。",
        })

    all_evidence = base_evidence + per_agent_evidence

    # Fallback critique
    critique_points = [
        {
            "id": "C-evidence-1",
            "target_id": "D1",
            "dimension": "证据强度",
            "severity": "medium",
            "content": "模型未能输出合法 IR JSON,系统按 Markdown 与讨论摘要回退构建;证据绑定需要人工复核。",
            "mitigation": "优先核对上传文档和入口 briefing 中与 Top 方向相关的关键事实。",
        }
    ]

    # 为每个 candidate 方向分配差异化证据
    candidates = []
    for index, title in enumerate(_candidate_titles_from_text(raw_text)[:5], start=1):
        # 按方向 index 轮转分配 agent debate 证据
        dir_evidence = ["E-template-1", "E-briefing-1"]
        # 每个方向分配 1-2 条不同的 debate 证据
        agent_start = (index - 1) % max(len(per_agent_evidence), 1)
        for offset in range(min(2, len(per_agent_evidence))):
            agent_idx = (agent_start + offset) % len(per_agent_evidence) if per_agent_evidence else -1
            if agent_idx >= 0:
                dir_evidence.append(per_agent_evidence[agent_idx]["id"])

        candidates.append({
            "id": f"D{index}",
            "title": title,
            "research_question": title,
            "rationale": "来自结构化 IR Markdown 与讨论摘要的回退抽取,需要在下一轮复核证据链。",
            "novelty": "需结合 Novelty Agent 的主张进一步确认。",
            "feasibility": "需结合 Feasibility Agent 的资源约束判断。",
            "risks": ["证据绑定不完整", "排序理由需要复核"],
            "alternatives": ["保留为备选方向,等待补充证据后再排序"],
            "priority": index,
            "priority_reason": "按 IR 文本出现顺序暂定。",
            "evidence_refs": dir_evidence,
            "critique_refs": ["C-evidence-1"],
            "next_actions": ["复核证据来源", "补齐关键验证实验"],
        })

    if not candidates:
        candidates.append({
            "id": "D1",
            "title": template.core_question or template.field,
            "research_question": template.core_question or f"围绕{template.field}形成可验证课题方向",
            "rationale": _compact(raw_text or brief.intake_synthesis, 420),
            "novelty": "需从讨论记录中继续提炼。",
            "feasibility": "需结合用户资源约束继续评估。",
            "risks": ["候选方向尚未充分聚类"],
            "alternatives": ["缩小问题范围,先做最小验证实验"],
            "priority": 1,
            "priority_reason": "唯一可回退方向。",
            "evidence_refs": ["E-template-1", "E-briefing-1"],
            "critique_refs": ["C-evidence-1"],
            "next_actions": ["人工复核 IR", "补充候选方向聚类"],
        })

    return StructuredIRV2.model_validate({
        "version": "1.5",
        "decision_summary": _compact(raw_text or brief.intake_synthesis, 500),
        "key_claims": _fallback_key_claims(messages),
        "evidence_refs": all_evidence,
        "critique_points": critique_points,
        "candidate_directions": candidates,
    })


def extract_references(messages: list[DebateMessage], existing: list | None = None) -> list:
    """从 debate_messages 中提取 ExternalReference 列表。
    优先从"### 外部引用"小节提取;如果没有该小节,则 fallback 到正则全文匹配。
    existing: 已有的引用列表(用于记忆合并去重)。
    """
    from app.schemas.models import ExternalReference

    existing_urls = {r.url for r in existing} if existing else set()
    refs: list[ExternalReference] = list(existing) if existing else []
    ref_counter = len(refs)

    def _add_ref(source_type, title, authors, url, year, viewpoint, agent, round_num):
        nonlocal ref_counter
        if not title:
            return
        normalized_url = url.rstrip("/") if url and url != "待确认" else ""
        if normalized_url and normalized_url in existing_urls:
            return
        if not normalized_url and any(r.title == title for r in refs):
            return
        ref_counter += 1
        refs.append(ExternalReference(
            id=f"REF-{ref_counter}",
            source_type=source_type,
            title=title,
            authors=authors,
            url=url,
            year=year,
            cited_viewpoint=viewpoint,
            citing_agent=agent,
            round=round_num,
        ))
        if normalized_url:
            existing_urls.add(normalized_url)

    # ── 第一遍:尝试从"### 外部引用"小节提取 ──
    has_explicit_section = False
    for message in messages:
        content = message.content
        marker = "### 外部引用"
        marker_idx = content.find(marker)
        if marker_idx < 0:
            marker = "## 外部引用"
            marker_idx = content.find(marker)
        if marker_idx < 0:
            continue

        has_explicit_section = True
        section = content[marker_idx + len(marker):].strip()
        next_section = section.find("\n###")
        if next_section >= 0:
            section = section[:next_section]

        for line in section.split("\n"):
            line = line.strip().lstrip("-•*").strip()
            if not line or line == "无" or line.lower() == "none":
                continue

            source_type = "other"
            type_match = re.match(r"\[(paper|blog|dataset|book|other)\]\s*", line, re.IGNORECASE)
            if type_match:
                source_type = type_match.group(1).lower()
                line = line[type_match.end():]

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                continue

            _add_ref(
                source_type=source_type,
                title=parts[0].strip(),
                authors=parts[1].strip() if len(parts) > 1 else "",
                url=parts[2].strip() if len(parts) > 2 else "",
                year=parts[3].strip() if len(parts) > 3 else "",
                viewpoint=parts[4].strip() if len(parts) > 4 else "",
                agent=message.agent,
                round_num=message.round,
            )

    # ── 第二遍:如果没有显式小节,用正则全文 fallback 提取 ──
    if not has_explicit_section or (not refs if existing is None else len(refs) == len(existing)):
        _fallback_extract(messages, _add_ref)

    return refs


def _fallback_extract(messages, add_fn):
    """从消息全文中用正则匹配可能的外部引用:URL、论文引用格式等。"""
    # 匹配严格格式的论文引用,只接受完整括号或逗号分隔的标准格式:
    #   Author et al. (YYYY)   Author & Author (YYYY)   Author (YYYY)
    #   Author et al., YYYY
    #   (Author et al., YYYY)  (Author, YYYY)
    # 不匹配残缺括号如 "Heuts 2008)"
    citation_pattern = re.compile(
        r"(?:"
        r"[A-Z][a-z]+\s+et\s+al\.?\s*\(\d{4}\)"          # Author et al. (YYYY)
        r"|[A-Z][a-z]+\s+(?:&|and)\s+[A-Z][a-z]+\s*\(\d{4}\)"  # Author & Author (YYYY)
        r"|[A-Z][a-z]+\s*\(\d{4}\)"                        # Author (YYYY)
        r"|[A-Z][a-z]+\s+et\s+al\.?,\s*\d{4}"              # Author et al., YYYY
        r"|\([A-Z][a-z]+\s+et\s+al\.?,\s*\d{4}\)"          # (Author et al., YYYY)
        r"|\([A-Z][a-z]+,\s*\d{4}\)"                        # (Author, YYYY) - 逗号必须
        r")"
    )
    # 匹配 URL
    url_pattern = re.compile(r'https?://[^\s)\]">,。,]+')
    # 匹配中文论文标题(书名号或引号包裹的标题 + 作者/年份)
    cn_paper_pattern = re.compile(r'[《\u201c""](\S{4,}?)[》\u201d""].*?(\d{4})')
    # 匹配 arXiv ID
    arxiv_pattern = re.compile(r'(?:arXiv:?\s*|arxiv\.org/abs/)(\d{4}\.\d{4,5})', re.IGNORECASE)

    for message in messages:
        content = message.content
        # 预处理:截掉 IR 摘要部分,避免 fallback 从中误提取引用
        ir_idx = content.find("### 给结构化 IR")
        if ir_idx < 0:
            ir_idx = content.find("给结构化 IR")
        if ir_idx > 0:
            content = content[:ir_idx]

        # 1. 提取 URL
        for match in url_pattern.finditer(content):
            url = match.group(0).rstrip(".,;\uff0c\u3002\uff1b")
            # 跳过明显不是引用的 URL(如 example.com 占位符)
            if any(skip in url.lower() for skip in ["example.com", "localhost", "127.0.0.1"]):
                continue
            # 从 URL 推断类型
            source_type = "other"
            url_lower = url.lower()
            if any(k in url_lower for k in ["arxiv", "doi", "pubmed", "semanticscholar", "scholar", "springer", "nature", "science", "pnas", "aclweb", "openreview"]):
                source_type = "paper"
            elif any(k in url_lower for k in ["blog", "medium", "substack", "wordpress", "ghost"]):
                source_type = "blog"
            elif any(k in url_lower for k in ["github", "huggingface", "kaggle", "zenodo"]):
                source_type = "dataset"

            # 尝试从 URL 前后的文本中提取上下文
            start = max(0, match.start() - 80)
            end = min(len(content), match.end() + 40)
            context = content[start:end].replace("\n", " ").strip()
            # 提取标题:URL 前最近的标题性文字
            before_text = content[max(0, match.start() - 160):match.start()]
            title = ""
            # 优先找粗体标题
            bold_match = re.search(r'\*\*([^*]{4,80})\*\*\s*$', before_text)
            if bold_match:
                title = bold_match.group(1)
            else:
                # 找书名号
                cn_match = re.search(r'[《\u201c](\S{4,60}?)[》\u201d]\s*$', before_text)
                if cn_match:
                    title = cn_match.group(1)
                    source_type = "paper"
                else:
                    # 找最近一行有意义的文字作为标题
                    line_match = re.search(r'([\u4e00-\u9fff\w][\u4e00-\u9fff\w\s]{4,80}?)\s*[::\n]?', before_text)
                    if line_match:
                        title = line_match.group(1).strip().split('\n')[-1].strip()
            if not title:
                title = url.split("/")[-1].replace("-", " ").strip()[:80]
            if not title or len(title) < 3:
                title = "[待补充标题]"

            add_fn(
                source_type=source_type,
                title=title[:120],
                authors="",
                url=url,
                year="",
                viewpoint=context[:120],
                agent=message.agent,
                round_num=message.round,
            )

        # 2. 提取 arXiv ID
        for match in arxiv_pattern.finditer(content):
            arxiv_id = match.group(1)
            # 检查是否已被 URL 提取覆盖
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
            if any(r.url == arxiv_url for r in refs if hasattr(add_fn, '__self__')):
                continue
            # 提取上下文
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 60)
            context = content[start:end].replace("\n", " ").strip()
            # 尝试找 arXiv 前的论文标题
            before_text = content[max(0, match.start() - 150):match.start()]
            title = f"arXiv:{arxiv_id}"
            bold_match = re.search(r'\*\*([^*]{4,80})\*\*\s*$', before_text)
            if bold_match:
                title = bold_match.group(1)

            add_fn(
                source_type="paper",
                title=title[:120],
                authors="",
                url=arxiv_url,
                year="",
                viewpoint=context[:120],
                agent=message.agent,
                round_num=message.round,
            )

        # 3. 提取中文论文/书籍引用(《》或引号 + 年份)
        for match in cn_paper_pattern.finditer(content):
            title = match.group(1)
            year = match.group(2) if match.group(2) else ""
            # 避免误匹配普通书名号内容
            if len(title) < 4:
                continue
            start = max(0, match.start() - 40)
            end = min(len(content), match.end() + 40)
            context = content[start:end].replace("\n", " ").strip()
            add_fn(
                source_type="book" if len(title) > 10 else "paper",
                title=title,
                authors="",
                url="",
                year=year,
                viewpoint=context[:120],
                agent=message.agent,
                round_num=message.round,
            )

        # 4. 提取英文论文引用格式 (Author et al., YYYY)
        for match in citation_pattern.finditer(content):
            cite_text = match.group(0).strip()
            if len(cite_text) < 6:
                continue
            # 提取年份
            year_match = re.search(r'(\d{4})', cite_text)
            year = year_match.group(1) if year_match else ""
            # 提取作者:去掉年份、括号、标点,只保留字母和空格
            author_part = re.sub(r'[\d()\[\],;:.]', ' ', cite_text)
            author_part = re.sub(r'\s+', ' ', author_part).strip()
            # 去掉末尾残留的 et al / & 等,规范化为纯字母+空格
            author_part = author_part.replace('&', 'and')
            # 验证 author_part 确实像人名(纯字母+空格,不含特殊字符)
            if not author_part or not re.match(r'^[A-Za-z\s]{2,40}$', author_part):
                continue
            # 截取上下文:短距离,且排除 IR 摘要等无关小节
            start = max(0, match.start() - 80)
            end = min(len(content), match.end() + 60)
            context = content[start:end].replace("\n", " ").strip()
            # 如果 context 包含 IR 摘要标记,截断到该标记之前
            ir_marker = context.find("给结构化 IR")
            if ir_marker > 0:
                context = context[:ir_marker].strip()
            # 找引用附近的粗体或书名号内容作为标题
            before_text = content[max(0, match.start() - 160):match.start()]
            cite_title = ""
            bold_match = re.search(r'\*\*([^*]{4,80})\*\*\s*$', before_text)
            if bold_match:
                cite_title = bold_match.group(1)
            else:
                cn_match = re.search(r'[《\u201c](\S{4,60}?)[》\u201d]\s*$', before_text)
                if cn_match:
                    cite_title = cn_match.group(1)
            if not cite_title:
                cite_title = f"{author_part} ({year})" if "et al" in author_part else f"{author_part} 等 ({year})"
            add_fn(
                source_type="paper",
                title=cite_title[:120],
                authors=author_part,
                url="",
                year=year,
                viewpoint=context[:120],
                agent=message.agent,
                round_num=message.round,
            )


def validate_structured_ir(ir: StructuredIRV2) -> list[str]:
    """检查 structured_ir 中证据绑定的完整性,返回 warning 列表。"""
    warnings: list[str] = []
    valid_ids = {e.id for e in ir.evidence_refs}
    fallback_ids = {"E-template-1", "E-briefing-1"}

    for direction in ir.candidate_directions:
        # 悬空引用检测
        for ref_id in direction.evidence_refs:
            if ref_id not in valid_ids:
                warnings.append(f"方向 [{direction.title}] 的 evidence_ref [{ref_id}] 不存在于 evidence_refs 列表中")

        # 空绑定检测
        if not direction.evidence_refs:
            warnings.append(f"方向 [{direction.title}] 没有任何证据绑定")

        # 通用引用检测(只有 fallback 的两个基础引用)
        non_fallback = [r for r in direction.evidence_refs if r not in fallback_ids]
        if direction.evidence_refs and not non_fallback:
            warnings.append(f"方向 [{direction.title}] 只有通用引用(模板/briefing),缺少讨论证据")

    # 检查 critique_refs
    critique_ids = {c.id for c in ir.critique_points}
    for direction in ir.candidate_directions:
        for ref_id in direction.critique_refs:
            if ref_id not in critique_ids:
                warnings.append(f"方向 [{direction.title}] 的 critique_ref [{ref_id}] 不存在于 critique_points 列表中")

    return warnings


def _candidate_titles_from_text(text: str) -> list[str]:
    titles = []
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if re.match(r"^(Top\s*\d+|方向\s*[A-E\d]+|候选方向|D\d+)", stripped, flags=re.IGNORECASE):
            cleaned = re.sub(r"^(Top\s*\d+[::.\s-]*|方向\s*[A-E\d]+[::.\s-]*|候选方向\s*\d*[::.\s-]*|D\d+[::.\s-]*)", "", stripped, flags=re.IGNORECASE)
            if cleaned:
                titles.append(cleaned[:120])
    return titles


def _fallback_key_claims(messages: list[DebateMessage]) -> list[str]:
    claims: list[str] = []
    for message in messages:
        claims.extend(message.claims[:2])
        if len(claims) >= 6:
            break
    if claims:
        return claims[:6]
    return [_compact(message.ir_summary or message.content, 160) for message in messages[:4] if message.content]


def ir_feedback_text(messages: list[DebateMessage]) -> str:
    parts = []
    for message in messages:
        summary = message.ir_summary or _extract_ir_summary(message.content)
        if not summary:
            summary = ";".join((message.claims or [])[:2] + (message.concerns or [])[:2])
        if not summary:
            summary = _compact(message.content, 420)
        parts.append(f"[Round {message.round} | {message.agent}]\n{summary}")
    return "\n\n".join(parts)


def _join_limited(items: list[str], limit: int) -> str:
    selected = [item for item in items if item][:limit]
    return ";".join(selected) if selected else "无"


def clean_final_report(report: str) -> str:
    # Strip any lingering end markers from stale data
    cleaned = strip_end_markers(report)
    lines = cleaned.strip().splitlines()
    cleaned: list[str] = []
    forbidden = re.compile(
        r"(如果你愿意|我下一步可以|下一步可以继续|可以继续把|PPT式|PPT 式|组会\s*10\s*分钟|基金版本|基金申请书|继续整理成)",
        re.IGNORECASE,
    )
    for line in lines:
        if forbidden.search(line):
            break
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _extract_ir_summary(content: str) -> str:
    marker = "给结构化 IR 的要点摘要"
    if marker not in content:
        return ""
    tail = content.split(marker, 1)[1]
    tail = re.sub(r"^[::\s#-]+", "", tail.strip())
    stop = re.search(r"\n#{1,6}\s+", tail)
    if stop:
        tail = tail[: stop.start()]
    return tail.strip()[:900]


MODERATOR_PER_AGENT_BUDGET = 2800


def _moderator_messages_text(messages: list[DebateMessage]) -> str:
    """Compressed view of debate messages for moderator prompt.

    Each agent's output is reduced to: IR summary + key claims + key concerns.
    Falls back to head+tail excerpt if structured fields are empty.
    Total per-agent output is capped at MODERATOR_PER_AGENT_BUDGET chars.
    """
    parts: list[str] = []
    for message in messages:
        sections: list[str] = []
        ir = message.ir_summary or _extract_ir_summary(message.content)
        if ir:
            sections.append(f"[IR 摘要]\n{ir}")
        claims = message.claims or _extract_claims(message.content)
        if claims:
            sections.append("[核心主张]\n" + "\n".join(f"- {c}" for c in claims))
        concerns = message.concerns or _extract_concerns(message.content)
        if concerns:
            sections.append("[主要顾虑]\n" + "\n".join(f"- {c}" for c in concerns))
        if not sections:
            sections.append("[全文裁切]\n" + _compact(message.content, MODERATOR_PER_AGENT_BUDGET))
        body = "\n\n".join(sections)
        if len(body) > MODERATOR_PER_AGENT_BUDGET:
            body = body[:MODERATOR_PER_AGENT_BUDGET] + "..."
        parts.append(f"[Round {message.round} | {message.agent}]\n{body}")
    return "\n\n".join(parts)


def _messages_text(messages: list[DebateMessage]) -> str:
    return "\n\n".join(
        f"[Round {message.round} | {message.agent}]\n{message.content}"
        for message in messages
    )


def _compact(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    return normalized[:limit] + ("..." if len(normalized) > limit else "")


def _extract_claims(content: str) -> list[str]:
    return [
        line.strip("- *")
        for line in content.splitlines()
        if any(keyword in line for keyword in ("创新", "假设", "方向", "建议", "科学问题"))
    ][:4]


def _extract_concerns(content: str) -> list[str]:
    return [
        line.strip("- *")
        for line in content.splitlines()
        if any(keyword in line for keyword in ("风险", "质疑", "不足", "失败", "限制"))
    ][:4]
