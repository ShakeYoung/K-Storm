from __future__ import annotations

import asyncio
import re

from app.model_providers.base import ModelProvider


class MockModelProvider(ModelProvider):
    """Deterministic provider for local MVP testing without external API keys."""

    def generate(
        self,
        *,
        agent_key: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        on_retry=None,
    ) -> str:
        asyncio.sleep(0.6)
        field = _extract(user_prompt, "研究领域") or "当前研究领域"
        target = _extract(user_prompt, "目标产出") or "开题报告/组会讨论"
        platforms = _extract(user_prompt, "可用技术平台") or "现有实验平台"
        constraints = _extract(user_prompt, "资源限制") or "周期、样本和经费约束"
        preferred = _extract(user_prompt, "偏好方向") or "机制与应用兼顾"

        if agent_key == "intake":
            return (
                f'建议将"{field}"的背景压缩为一个可验证问题：基于已有基础，优先寻找'
                f'能用{platforms}在{constraints}内验证的关键变量，并把目标产出对齐到{target}。'
            )
        if agent_key == "novelty":
            probe = _extract(user_prompt, "用户问题")
            probe_line = f'\n\n**用户提问**：{probe}' if probe else ""
            return (
                f'**新方向**：围绕"{field}"建立一个从既有基础出发的差异化问题，优先选择'
                f'"{preferred}"相关切入点。{probe_line}\n\n'
                f'**创新点**：把已有数据/模型与{platforms}组合，形成可被验证的选题，而不是泛泛扩展。\n\n'
                '**为什么值得做**：如果能证明关键变量与表型之间存在可重复关联，后续可以自然延伸为开题论证或组会讨论主线。\n\n'
                f'**可能被质疑**：目前最大风险是创新边界不够清楚，需要用对照方案证明它不是已有工作的简单重复。\n\n'
                '### 给结构化 IR 的要点摘要\n'
                '- 关键主张：应建立差异化问题并组合已有数据与实验平台\n'
                '- 支撑依据：已有基础与平台资源可组合\n'
                '- 风险或反驳点：创新边界不够清楚\n'
                '- 建议进入 IR 的下一步动作：明确差异化切入点\n\n'
                '### 外部引用\n'
                f'[paper] {field}领域近五年创新方向综述 | Zhang et al. | https://example.com/review-{field[:3]} | 2024 | 创新方向选择有文献基础\n'
                f'[blog] {platforms}实验平台最佳实践 | Lab Protocols | https://example.com/protocols | 2023 | 平台可行性有实践指南'
            )
        if agent_key == "mechanism":
            probe = _extract(user_prompt, "用户问题")
            probe_line = f'\n\n**用户提问**：{probe}' if probe else ""
            return (
                '**机制假设**：建议把问题拆成\u201c触发因素 → 中介机制 → 可测表型 → 干预验证\u201d四段链条。'
                f'{probe_line}\n\n'
                f'**关键变量**：优先选择能被{platforms}直接测量或扰动的变量，避免依赖暂时不可获得的技术。\n\n'
                '**因果验证**：至少设置一个 gain/loss-of-function 或分层队列验证，让相关性结果进入因果解释。\n\n'
                '**需要收敛**：不要同时追太多通路，先选 1 条主链条和 1 条备选链条。\n\n'
                '### 给结构化 IR 的要点摘要\n'
                '- 关键主张：四段因果链条框架\n'
                '- 支撑依据：平台可直接测量关键变量\n'
                '- 风险或反驳点：通路过多需收敛\n'
                '- 建议进入 IR 的下一步动作：确定主链条和备选链条\n\n'
                '### 外部引用\n'
                f'[paper] Causal inference in {field}: a systematic review | Li et al. | https://example.com/causal-{field[:3]} | 2023 | 因果验证方案有系统综述支撑'
            )
        if agent_key == "feasibility":
            probe = _extract(user_prompt, "用户问题")
            probe_line = f'\n\n**用户提问**：{probe}' if probe else ""
            return (
                f'**可执行版本**：在{constraints}下，建议先做 2-4 周小规模验证，再决定是否扩大样本或上动物/临床队列。'
                f'{probe_line}\n\n'
                f'**资源匹配**：优先使用{platforms}，把新增平台需求降到最低。\n\n'
                '**周期风险**：高通量或动物实验适合作为第二阶段，第一阶段应以已有样本、公共数据或细胞模型验证为主。\n\n'
                '**降险方案**：每个选题都应设计一个低成本替代 readout，保证核心假设可以快速被证伪。\n\n'
                '### 给结构化 IR 的要点摘要\n'
                '- 关键主张：先小规模验证再扩大\n'
                '- 支撑依据：现有平台资源可直接使用\n'
                '- 风险或反驳点：周期可能超预期\n'
                '- 建议进入 IR 的下一步动作：定义 2-4 周验证计划\n\n'
                '### 外部引用\n'
                f'[paper] Rapid validation strategies in experimental {field} | Wang et al. | https://example.com/rapid-validation | 2024 | 快速验证策略有方法论文\n'
                f'[dataset] {platforms}公共数据集 | Open Data Portal | https://example.com/dataset-{field[:3]} | 2023 | 公共数据可直接获取'
            )
        if agent_key == "reviewer":
            probe = _extract(user_prompt, "用户问题")
            probe_line = f'\n\n**用户提问**：{probe}' if probe else ""
            return (
                '**主要质疑**：选题需要更明确地回答\u201c相比现有研究多知道了什么\u201d。如果只描述现象，评审会认为科学问题偏弱。'
                f'{probe_line}\n\n'
                '**证据链断点**：从已有基础到最终产出之间还缺一个关键验证实验，尤其是机制干预或独立样本验证。\n\n'
                f'**论证风险**：目标产出是{target}，因此需要提前定义最低可讨论单元和失败后的备选叙事。\n\n'
                '**建议修正**：把 Top 方向按创新性、可行性、证据链完整度打分，优先推进综合分最高且 4 周内可产生结果的方向。\n\n'
                '### 给结构化 IR 的要点摘要\n'
                '- 关键主张：选题需回答增量贡献问题\n'
                '- 支撑依据：证据链存在断点\n'
                '- 风险或反驳点：目标产出需定义最低可讨论单元\n'
                '- 建议进入 IR 的下一步动作：对 Top 方向综合打分\n\n'
                '### 外部引用\n'
                f'[paper] Common pitfalls in {field} research proposals | Chen et al. | https://example.com/pitfalls-{field[:3]} | 2022 | 评审常见质疑点有文献归纳\n'
                f'[blog] How to write a strong {target} | Academic Writing Blog | https://example.com/writing-guide | 2024 | 论证写作有结构化指南'
            )
        if agent_key == "group_summarizer":
            return (
                '讨论组共识是：先把宽泛背景压缩成 3 个可验证方向，每个方向必须同时具备差异化科学问题、'
                '可落地实验路线和明确失败替代方案。分歧主要在创新优先还是可行性优先；建议采用\u201c两阶段策略\u201d：'
                '第一阶段快速验证，第二阶段再扩大为机制或转化研究。'
            )
        if agent_key == "output":
            return _mock_report(field, target, platforms, constraints, preferred)

        return "已完成本轮分析。"


def _extract(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}[：:](.+)", text)
    if not match:
        return ""
    return match.group(1).strip()


def _mock_report(
    field: str,
    target: str,
    platforms: str,
    constraints: str,
    preferred: str,
) -> str:
    return f"""# K-Storm 科研选题报告

## 1. 用户输入摘要

- 研究领域：{field}
- 可用技术平台：{platforms}
- 资源限制：{constraints}
- 目标产出：{target}
- 偏好方向：{preferred}

## 2. 核心科学问题提炼

如何基于现有实验基础，在资源可控的前提下，提出一个兼具创新性、机制解释力和短期验证路径的科研选题？

## 3. 推荐选题 Top 3

### Top 1：基于已有模型的关键调控轴验证

- 科学问题：现有结果中最稳定的表型是否由一个可干预的关键调控轴驱动？
- 创新点：从已有基础出发形成明确机制链条，避免重新铺开大而散的问题。
- 可行性：高，优先使用现有样本和{platforms}。
- 实验路线：整理已有数据 → 筛选候选变量 → 小规模验证 → 干预实验 → 独立样本复核。
- 关键验证实验：候选变量扰动后检测核心表型是否反向改变。
- 风险点：候选变量与表型只有相关性，干预效果弱。
- 替代方案：改用上游触发因素或下游 readout 作为主线。
- 适合产出类型：{target}

### Top 2：资源约束下的分层队列/样本验证

- 科学问题：不同样本分层中是否存在可重复的差异模式，并能解释疾病或材料性能差异？
- 创新点：把已有观察转成可解释分层，提高后续开题和组会叙事的确定性。
- 可行性：中高，取决于样本量和统计功效。
- 实验路线：定义分层标准 → 小样本验证 → 建立评分指标 → 扩展样本 → 关联功能表型。
- 关键验证实验：独立批次样本复现关键差异。
- 风险点：样本异质性过强或效应量不足。
- 替代方案：先用公共数据或历史样本做预验证。
- 适合产出类型：预实验、开题报告、组会讨论材料。

### Top 3：交叉技术平台驱动的方法/应用延伸

- 科学问题：能否用{platforms}形成一个比单一 readout 更稳健的评价或预测框架？
- 创新点：强调技术组合和可迁移分析框架，适合形成方法或转化应用方向。
- 可行性：中等，需要控制技术复杂度。
- 实验路线：选择最小技术组合 → 建立评价指标 → 验证预测能力 → 机制解释补强。
- 关键验证实验：指标能否预测或解释独立实验结果。
- 风险点：方法复杂但生物/工程解释不足。
- 替代方案：缩小到一个明确应用场景，减少平台数量。
- 适合产出类型：方法开发、转化应用、专利前验证。

## 4. 综合优先级排序

1. 关键调控轴验证：创新性 4/5，可行性 5/5，风险 2/5。
2. 分层队列/样本验证：创新性 3/5，可行性 4/5，风险 3/5。
3. 交叉技术平台延伸：创新性 4/5，可行性 3/5，风险 4/5。

## 5. 下一步 2-4 周行动计划

1. 明确已有数据中最稳定的 2-3 个候选变量或表型。
2. 为 Top 1 设计一个最小验证实验，优先使用现有样本和平台。
3. 同步准备 Top 2 的样本分层表，判断是否具备统计验证条件。
4. 在第 4 周做一次 go/no-go 评估，决定是否扩大为机制研究或转向备选方向。

## 6. 可直接用于开题/组会的表达版本

本课题拟基于前期研究基础，围绕{field}中的关键未解问题，构建\u201c现象观察-机制假设-实验干预-独立验证\u201d的研究链条。研究将优先利用现有{platforms}和样本资源，在{constraints}约束下开展可快速证伪的预实验，筛选最具创新性与可行性的研究方向，为后续{target}奠定明确的科学问题、技术路线和风险替代方案。
"""
