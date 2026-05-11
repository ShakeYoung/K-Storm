# V1.6：讨论模式分层 —— 从"全量"到"即席"的可编排讨论体系

## 文档目的

本文定义 K-Storm 下一迭代（V1.6）的核心能力：

> 根据议题粒度、深度需求和算力预算，选择不同的讨论模式，并让不同模式之间通过记忆系统形成知识连续性。

本迭代不改变 V1.5 路线图中的证据绑定、候选排序、Critique 制度化等目标，而是在 V1.5 的结构化基础上增加**讨论维度**的选择灵活性。V1.5 与 V1.6 可并行推进。

---

## 一、从用户使用中发现的问题

当前系统只有一种模式：全 Agent、全轮次、全流程。用户遇到的痛点：

1. **大议题耗时太长**。全部 4 个 Agent 走满 3 轮，加上 Intake、Moderator、IR、Output，一次 run 十几分钟，只想验证一个小方向时成本过高。
2. **粒度没有匹配选项**。不是每个问题都需要 4 个视角同时讨论——有些只需要问 Reviewer "这个方案有什么漏洞"，或只让 Mechanism 和 Feasibility 对谈。
3. **没有历史记忆的利用**。之前大讨论已经形成的结论，在小问题时应该能直接引用，而不是每次都从零开始。
4. **"讨论"和"问答"混在一起**。快速验证类和深度探索类共用同一流程，模糊了工具的定位。

核心矛盾：**议题的复杂度和投入的算力之间没有对应关系**。

---

## 二、设计原则

1. **算力成本显式化**。让用户在选择模式时能感知到时间/代币的差异，而不是隐藏在不同按钮背后。
2. **模式之间的结论可迁移**。快速讨论的结论可以升级为全量讨论的上下文，全量讨论的结论可以被快速讨论引用。
3. **Agent 编排可组合**。不固定讨论组一定是 4 个 Agent，允许用户按需选择参与讨论的 Agent 子集。
4. **单次讨论的定位前置**。在创建时就明确"这是深度探索还是快速验证"，而不是运行中临时切换。
5. **兼容现有设计**。不推翻 C-led 三栏布局，在 Input Dock 中增加模式选择层，在 Intelligence Rail 中增加记忆侧写。

---

## 三、讨论模式定义

### 模式总览

| 模式 | 中文名 | 参与 Agent | 轮次 | 记忆参与 | 典型耗时 | 算力成本 |
|---|---|---|---|---|---|---|
| **Full Deliberation** | 全量审议 | 全部 (Intake + 4 Agents + Moderator + IR + Output) | 2~5 轮 | 可选择性注入 | 长 (5~20min) | 高 |
| **Focused Panel** | 专题研讨 | 可编排子集 (2~3 个 Agent) | 1~2 轮 | 自动注入相关记忆 | 中 (2~6min) | 中 |
| **Quick Probe** | 快速探查 | 1 个 Agent (用户指定问题方向) | 单轮 | 自动注入 + 记忆检索作为回答基础 | 短 (30s~2min) | 低 |
| **Memory Query** | 记忆查询 | 0 个 Agent (仅检索) | 0 | 直接检索历史结论 | 即时 (<10s) | 零 |

#### 1. Full Deliberation（已有模式的正式命名）

**定位**：当前系统的完整讨论流程，正式赋予名字，保持行为不变。

**流程**：Intake → Briefing → 4 Agent 讨论 (N 轮) → Moderator → Structured IR → Final Report

**适用场景**：
- 开题方向探索
- 方法论设计
- 多方案比较评估
- 需要多视角交叉验证的复杂问题

**配置项**：
- 参与 Agent：固定 4 个，不可缩减
- 轮次：2~5
- 是否并行首轮
- 是否包含 Red-Team Critique 阶段（V1.5 引入）

**UI 标记**：在 Input Dock 中显示为"深度模式"，带有 🔵 或类似标识，预估时间显式展示。

---

#### 2. Focused Panel（新增）

**定位**：抽取 2~3 个与当前问题最相关的 Agent，进行定向讨论。不经过 Intake 和 Full Briefing（复用已有 Briefing 或精简版），不经过 Moderator（缩短对话链），直接产出针对性结论。

**流程**：（复用已有 Briefing 摘要）→ 选定 Agent 讨论 (1~2 轮) → 精简 IR → 结论卡片

**适用场景**：
- "我想验证这个方向实验上是否可行" → Feasibility + Reviewer
- "帮我深挖这个机制的因果链" → Mechanism + Novelty
- "评估这两个方案的创新性和可行性" → Novelty + Feasibility + Reviewer

**关键设计**：
- **Agent 选择器**：用户从 4 个 Agent 中勾选 2~3 个，每个 agent 可以独立分配模型（沿用现有机制）
- **跳过 Intake**：复用 run 级别的 Briefing（如果有），或由入口 Agent 做一趟精简摘要（非完整 Briefing）
- **跳过 Moderator**：Agent 发言直接进入精简 IR
- **精简 IR 适配**：根据参与 Agent 的数量和议题缩小，IR 模板自动缩减范围
- **与 Full 模式的关系**：Focused Panel 的结论可以"升级"——一键追加更多 Agent 或轮次，扩展为 Full Deliberation

**预置 Panel 模板**（用户可直接选，也可自定义）：

| Panel 名称 | Agent 组合 | 定位 |
|---|---|---|
| 实验可行性审查 | Feasibility + Reviewer | 评估方案的可执行性和风险 |
| 创新方向挖掘 | Novelty + Mechanism | 探索差异化方向和机制假设 |
| 方案压力测试 | Novelty + Feasibility + Reviewer | 完整三视角交叉评审 |
| 盲点扫描 | Mechanism + Reviewer | 检查逻辑漏洞和遗漏维度 |
| 自定义 | 用户自选 2~3 个 | 自由组合 |

---

#### 3. Quick Probe（新增）

**定位**：针对单问题、单 Agent 的快速问答。选择与问题最相关的 Agent（或默认 Reviewer），给出上下文后直接回答。不经过 Multi-Agent 讨论链。

**流程**：选中一个 Agent → 自动注入上下文（Briefing 摘要 + 相关记忆）→ 单次生成 → 答案卡片

**适用场景**：
- "Reviewer，这个方案最大的漏洞是什么？"
- "Feasibility，这个实验方案大概需要多久？"
- "Novelty，这个方向跟已有工作比真的有创新吗？"
- 快速验证一个假设的合理性

**关键设计**：
- **Agent 单选**：用户明确指定由哪个 Agent 回答
- **上下文装配**：自动携带当前 run 的 Briefing + 记忆中最相关的 2~3 条结论，让 Agent 不是凭空回答
- **不进入讨论链**：单次生成即结束，不触发 Moderator 或 IR
- **可转为讨论**：答案卡片上提供"扩展讨论"按钮，一键追加其他 Agent 扩充为 Focused Panel

---

#### 4. Memory Query（新增）

**定位**：不调任何 Agent，直接从历史结论中检索答案。本质上是 K-Storm 的记忆检索系统的最小化落地接口。

**流程**：用户输入问题 → 检索历史 run 的结构化结论（候选方向、关键 claim、批判点）→ 匹配结果排序展示

**适用场景**：
- "之前讨论过 XX 方向吗？结论是什么？"
- "关于这个方法上次的 feasibility 评估结果是什么？"
- "Reviewer 批判过哪些方案的可行性？"

**关键设计**：
- **不产生新 token 成本**
- **检索范围**：当前项目的所有历史 run 的 StructuredIRV2 中的 candidate_directions、key_claims、critique_points
- **排序依据**：语义相似度 + 时间衰减
- **展示形式**：结果卡片列表，每条标出来源 run_id、创建时间、相关 Agent
- **从结果发起新讨论**：每条检索结果后可选"基于此发起讨论"，将历史结论自动注入新 run 的上下文

---

## 四、记忆系统的设计与角色

### 4.1 记忆解决的问题

四种模式的核心差异不只是 Agent 数量和轮次，关键在于**记忆如何参与**：

- Full Deliberation：用户**可选择**注入相关记忆作为额外上下文
- Focused Panel：**自动注入**与当前议题最相关的历史结论
- Quick Probe：**必须注入**，因为单 Agent 没有讨论链互相补充，记忆是回答质量的基本保障
- Memory Query：**仅检索**，不生成

### 4.2 记忆的存储结构

现有 `StructuredIRV2` 已经包含了 `candidate_directions`、`key_claims`、`evidence_refs`、`critique_points`。记忆系统在此基础上增加：

```python
class MemoryEntry(BaseModel):
    """记忆条目：从一次 run 的结构化结论中提取的可检索知识单元"""
    entry_id: str
    run_id: str
    source_type: str = "candidate_direction" | "key_claim" | "critique_point" | "evidence_ref"
    source_id: str            # 指向 StructuredIRV2 中的具体条目 ID
    content: str              # 可检索的文本内容
    field: str                # 所属研究领域
    tags: list[str]           # 自动抽取的关键词标签
    confidence: float         # 来源 run 的置信度（预留）
    created_at: str
```

**存储位置**：SQLite 新增 `memory_entries` 表，与 `runs` 表一对多。

### 4.3 记忆的写入时机

每次 run 完成且 `StructuredIRV2` 生成后，自动将 `candidate_directions`、`key_claims`、`critique_points` 中的内容拆解为 `MemoryEntry` 写入记忆库。

### 4.4 记忆的检索与注入

检索：
- 使用轻量 TF-IDF 或嵌入检索（V1.6 建议先走 TF-IDF，不引入外部向量数据库）
- 检索范围：当前项目的所有 MemoryEntry
- Top-K：快速模式取 3~5 条，全量模式取 5~8 条

注入：
- 检索到的记忆条目格式化为一小段上下文，注入到对应 Agent 的系统提示词的 Memory Context 段中
- 格式示例：

```
## 记忆上下文（来自历史讨论）

以下是从历史讨论中检索到的相关结论，供参考：

[1] 候选方向"XX 基因在 YY 通路中的作用"（来源：run_ks_abc123，2026-05-08）
    - 核心主张：该方向可能解释耐药机制
    - Feasibility Agent 评估：动物模型周期约 3 个月，可行
    - Reviewer 质疑：需要先确认临床样本中的表达差异

[2] 关键 claim："YY 通路与免疫检查点抑制剂的协同效应已有初步证据"
    - 来源：run_ks_def456，Mechanism Agent 发言
    - 证据：文献 PMID: 12345678
```

---

## 五、Agent 编排系统的改动

### 5.1 当前编排结构

```
Intake → [Novelty, Mechanism, Feasibility, Reviewer] × N rounds → Moderator → IR → Output
```

### 5.2 V1.6 编排结构

```
                            ┌─ Full Deliberation ───────────────────────────┐
                            │  Intake → [All 4] × N → Moderator → IR → Out │
                            └──────────────────────────────────────────────┘

                            ┌─ Focused Panel ───────────────────────────────┐
        议题 → 模式选择器 ──→│  (Briefing) → [Selected 2~3] × 1~2 → LiteIR │
                            └──────────────────────────────────────────────┘

                            ┌─ Quick Probe ───┐
                            │  Context + 1 Agent → Answer │
                            └──────────────────┘

                            ┌─ Memory Query ──┐
                            │  Query → 检索结果 │
                            └──────────────────┘
```

### 5.3 后端改动要点

1. **新增 `DiscussionMode` 枚举**：
   ```python
   class DiscussionMode(StrEnum):
       FULL_DELIBERATION = "full_deliberation"
       FOCUSED_PANEL = "focused_panel"
       QUICK_PROBE = "quick_probe"
       MEMORY_QUERY = "memory_query"
   ```

2. **扩展 `RunCreate` schema**：
   ```python
   class RunCreate(BaseModel):
       template_input: TemplateInput
       mode: DiscussionMode = DiscussionMode.FULL_DELIBERATION
       # Full 模式参数
       rounds: int = 3
       parallel_first_round: bool = False
       # Focused 模式参数
       selected_agents: list[str] = Field(default_factory=list)  # agent keys
       panel_rounds: int = 1
       # Quick Probe 参数
       probe_agent: str = ""  # 目标 agent key
       probe_question: str = ""
       # Memory Query 参数
       memory_query: str = ""
       # 通用
       model_settings: AgentModelSettings | None = None
       documents: list[UploadedDocument] = Field(default_factory=list)
       inject_memory: bool = False  # 是否注入历史记忆
   ```

3. **扩展 `RunRecord`**：增加 `mode` 字段，用于历史记录中区分运行类型。

4. **Orchestrator 新增模式分支**：
   - `execute_run()` 根据 `mode` 路由到不同执行路径
   - `execute_focused_panel()`：并行或串行运行选定的 Agent 子集
   - `execute_quick_probe()`：单 Agent 单次生成
   - `execute_memory_query()`：仅检索已有记忆

5. **新增 `memory_store` 模块**：
   - `storage/memory.py`：MemoryEntry 的 CRUD 与检索
   - 写入时机：run 完成后，从 `StructuredIRV2` 拆解写入
   - 检索方式：TF-IDF + 词频匹配（V1.6 先用轻量方案）

6. **已有 Prompt 的适配**：
   - Full Deliberation：系统提示词末尾增加可选的 Memory Context 段（由 `inject_memory` 控制）
   - Focused Panel/Quick Probe：Agent 提示词中内置 Memory Context 段（始终注入）

---

## 六、UI 改动方案

基于 C-led 三栏布局（Input Dock + Observatory Stage + Intelligence Rail）进行扩展。

### 6.1 Input Dock：模式选择器

在现有模板表单与"开始分析"按钮之间，插入**模式选择区域**：

```
┌─────────────────────────────────┐
│  Input Dock                      │
│                                  │
│  [Core Input Section]            │
│  [Constraints Section]           │
│  [Documents & Params Section]    │
│                                  │
│  ── 讨论模式 ────────────────── │
│  │ ○ Full Deliberation (深度)   │
│  │ ● Focused Panel (专题)       │ ← 选中态
│  │ ○ Quick Probe (快速)         │
│  │ ○ Memory Query (查询)        │
│  │                              │
│  │   └─ Panel 模板: (下拉)      │ ← Focused 模式时显示
│  │      实验可行性审查            │
│  │      创新方向挖掘              │
│  │      方案压力测试              │
│  │      盲点扫描                  │
│  │      自定义...                 │
│  │                              │
│  │   └─ 参与 Agent: ☑ Novelty   │
│  │                 ☑ Feasibility │
│  │                 ☑ Reviewer    │
│  │                              │
│  │  预估: 3~6 分钟 | ~10K tokens│
│  │                              │
│  │  [开始分析]                   │
└─────────────────────────────────┘
```

交互行为：
- 切换模式时，下方参数区域动态变化
  - Full：显示轮次、并行首轮开关
  - Focused：显示 Panel 模板下拉、Agent 多选（2~3 个）、轮次（1~2）
  - Quick Probe：显示 Agent 单选框、问题输入框
  - Memory Query：显示检索式输入框，不显示"开始分析"按钮（改为"查询"）
- 预估时间和代币消耗随模式动态更新
- 模式切换不丢失已填写的模板内容

### 6.2 Observatory Stage：分模式展示

不同模式的运行结果在主舞台差异化展示：

| 模式 | 主舞台展示 |
|---|---|
| Full Deliberation | 现有设计不变：Round Tabs + 4 Agent Columns + Briefing/IR/Report |
| Focused Panel | 精简版：2~3 列 Agent（按勾选数量），结论卡片区，无 Moderator 步骤 |
| Quick Probe | 单 Agent 回答卡片，上下文来源标注，[扩展讨论] 按钮 |
| Memory Query | 检索结果列表，每条带来源标记，[基于此讨论] 按钮 |

### 6.3 Intelligence Rail：记忆侧写

新增**记忆摘要面板**，位置在 Intelligence Rail 中：

```
┌─ 记忆 ─────────────────────┐
│ 📋 最近讨论                 │
│  · XX 耐药机制 (昨天)      │
│  · YY 通路 (3天前)         │
│  · ZZ 模型可行性 (5天前)   │
│                             │
│ 🔍 搜索记忆...              │
│ (输入快速检索历史结论)      │
└────────────────────────────┘
```

- 显示最近的 3~5 条历史 run 摘要
- 提供搜索入口（等同于 Memory Query 模式）
- 快速跳转到历史 run 详情

### 6.4 创建流程示意

```
用户进入界面

[Full 模式，默认]
填写模板 → 调整轮次 → [开始分析] → 全量讨论

[Focused 模式]
填写模板 → 选择 Panel 模板或自定义 Agent → [开始分析] → 专题研讨

[Quick Probe 模式]
填写问题 → 选择 Agent → [提问] → 单次回答
         ↓ (可选)
      注入当前 Briefing 上下文

[Memory Query 模式]
输入查询 → [检索] → 结果列表 → 点击结果跳转详情
                           ↓ (可选)
                        基于此发起讨论 (转换为 Full/Focused)
```

---

## 七、升级路径：从快速到深度的闭环

四种模式不是孤立的，而是形成一条**讨论深度光谱**，用户可以在不同深度之间跃迁：

```
Memory Query ──→ Quick Probe ──→ Focused Panel ──→ Full Deliberation
 (发现已有结论)   (验证一个点)     (几个视角对谈)     (完整审议)
```

**升级操作**：
- Memory Query 结果 → "基于此展开讨论" → 转入 Quick Probe 或 Focused Panel
- Quick Probe 答复 → "扩展讨论" → 自动增加 Agent 扩充为 Focused Panel
- Focused Panel 结论 → "深度审议" → 补充 Agent 并增加轮次扩展为 Full Deliberation
- 所有升级操作**保留已有上下文**，不会丢失已产生的结论

这是一个**正向升级链**，用户从最轻量的入口发现问题，逐步加深，直到需要全量审议时再投入全部算力。

反向也存在：
- Full Deliberation 的结论被记忆系统吸收 → 下次同类问题直接走 Memory Query 或 Quick Probe

---

## 八、与 V1.5 的关系

V1.5（证据绑定、候选排序、Critique 制度化）与 V1.6（讨论模式分层）是**正交但互惠**的两个维度：

| 维度 | V1.5 | V1.6 |
|---|---|---|
| **核心问题** | 讨论产物的质量 | 讨论投入的成本 |
| **改动焦点** | IR 结构、证据链 | 编排逻辑、模式路由 |
| **改动范围** | 后端 IR 生成 + Report | 后端 Orchestrator + Frontend 创建流程 |
| **依赖关系** | V1.6 的 Focused/Quick 模式受益于 V1.5 的证据绑定和结构化 IR | V1.5 的结构化 IR 是记忆系统的基础输入 |
| **可并行度** | 可独立推进 | 可独立推进，但共享同一代码库 |

**建议执行顺序**：两个版本的弱依赖部分并行开发，强依赖部分按需协调。

- 可并行：V1.5 的 IR 结构 + V1.6 的模式路由（先行定义但暂不接入记忆）
- 需协调：V1.6 的记忆系统依赖 V1.5 的 `StructuredIRV2` 结构
- 推荐：先定义模式路由和 UI，等 V1.5 的 IR 结构稳定后再对接记忆写入

---

## 九、排除项（本版本不涉及）

1. **不引入外部向量数据库**。记忆检索先用 TF-IDF，后续 V2/V3 再升级。
2. **不改变 Full Deliberation 的底层逻辑**。该模式的执行流程与现有系统完全一致，只做重命名和 mode 标记。
3. **不引入 Agent 数量动态扩展**。Focused Panel 的 Agent 上限为 3 个，不开放 4 个以上。
4. **不取代用户手动调整 prompt 的能力**。高级用户仍可通过模板编辑影响 Agent 行为。
5. **不做跨 session 的记忆持久化**。记忆库在 V1.6 中基于 SQLite，不清除不跨用户。

---

## 十、V1.6 完成判据

1. 用户在创建页面可以选择 4 种讨论模式，切换时参数区联动变化
2. Full Deliberation 运行完整流程，与当前行为一致
3. Focused Panel 按选定 Agent 子集运行 1~2 轮，产出精简 IR
4. Quick Probe 针对单 Agent 单问题生成回答，带上下文注入
5. Memory Query 检索历史 run 的结构化结论并展示结果列表
6. 每次 Full/Focused/Quick 运行完成后，自动将结构化结论写入记忆库
7. 记忆检索在所有模式中正确注入（Full 可选，其他默认开启）
8. 支持 "升级" 操作：Memory Query → Focused，Quick Probe → Focused，Focused → Full
9. 历史列表中标记每次 run 的讨论模式

---

## 十一、推荐执行顺序

### Phase 1：模式层定义（后端先行）

1. 定义 `DiscussionMode` 枚举和扩展后的 `RunCreate` schema
2. 扩展 `RunRecord` 增加 `mode`、`selected_agents`、`probe_question` 等字段
3. 实现 `execute_focused_panel()` 和 `execute_quick_probe()` 编排函数
4. 实现 `execute_memory_query()` 检索函数（先写纯文本检索，不依赖 IR 结构）
5. Orchestrator 中 `start_run()` 根据 `mode` 路由到不同执行路径

### Phase 2：UI 模式选择器（前端 + 后端联调）

6. Input Dock 中增加模式选择区（Radio Group + 动态参数表单）
7. Observatory Stage 根据模式差异化渲染结果
8. 后端 API 适配新的 RunCreate 字段
9. Focused Panel 的 Panel 模板预置（5 个模板，prompt 层面完成）

### Phase 3：记忆系统（依赖 V1.5 StructuredIRV2）

10. 实现 MemoryEntry schema 和 SQLite 表
11. 实现写入：run 完成后从 StructuredIRV2 提取记忆条目
12. 实现检索：TF-IDF + 词频匹配
13. 实现注入：在 Agent 提示词中插入 Memory Context 段

### Phase 4：升级链路与收尾

14. 实现 4 种升级操作（Memory→Quick→Focused→Full）
15. Intelligence Rail 新增记忆侧写面板
16. 历史记录页面标记讨论模式
17. 边界测试（极短输入、空记忆、模式中途切换等）

---

## 十二、开放问题

1. **记忆检索的精度下限**：TF-IDF 在短文本（单条 claim）上的检索效果如何？是否需要走一步 embedding 路线？
2. **Focused Panel 的 Panel 模板**：5 个预置模板是否够用？是否允许用户保存自定义 Panel 模板？
3. **Quick Probe 的上下文装配策略**：当有多段历史记忆 + Briefing 时，上下文裁剪策略是什么？固定 token 预算还是动态？
4. **记忆的过期与检索范围**：是否按时间衰减？——不同领域的记忆是否应隔离？当前按项目/领域的方案是否足够？
5. **Full Deliberation 中记忆注入是默认开还是默认关**：默认开可能引入噪声，默认关则用户感知不到记忆的存在。

这些开放问题需要在开发过程中通过用户反馈逐步收敛，不建议在规划阶段全部下定论。
