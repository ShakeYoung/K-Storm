# K-Storm 项目架构图

K-Storm 是一个本地运行的科研选题多 Agent 头脑风暴系统。当前版本为 V1.6，采用轻量 Web 架构：FastAPI 提供后端 API，React + Vite 作为主前端，SQLite 用于本地历史记录。

## 1. 总体架构

```mermaid
flowchart TB
  User["用户 / 科研人员"]

  subgraph Browser["浏览器 Web UI"]
    StaticUI["FastAPI 静态 UI（旧版）<br/>backend/app/static/index.html"]
    ReactUI["React + Vite 主前端（V1.6）<br/>frontend/src/main.jsx"]
    ModelSettings["模型设置<br/>供应商 / 模型 / Agent 位置"]
    ModeSelector["讨论模式选择<br/>完整 / 聚焦 / 快速 / 记忆"]
    TemplateForm["头脑风暴模板<br/>文档上传 / 注释 / 讨论轮次"]
    RunView["讨论台<br/>停止分析 / 继续分析 / 分轮讨论"]
    DocumentView["报告页<br/>报告面板 / Markdown 渲染 / PDF 导出"]
    ReferencesView["外部论据页<br/>按类型分组 / Markdown 渲染 / 导出"]
    HistoryView["历史记录<br/>搜索 / 状态筛选 / 继续分析 / 删除"]
    MemoryQuery["记忆查询<br/>基于历史 Run 启动新讨论"]
  end

  subgraph Backend["FastAPI Backend"]
    API["API Layer<br/>backend/app/main.py"]
    Orchestrator["Agent Orchestrator<br/>backend/app/orchestrator/runner.py"]
    AgentRegistry["Agent Registry<br/>backend/app/agents/registry.py"]
    Schemas["Pydantic Schemas<br/>backend/app/schemas/models.py"]
    ProviderRouter["Agent Model Router<br/>backend/app/model_providers/router.py"]
    ProviderClients["Model Provider Clients<br/>OpenAI Compatible / Responses / Anthropic / Mock"]
    Storage["Storage Service<br/>backend/app/storage/db.py"]
  end

  subgraph LocalData["本地数据"]
    SQLite["SQLite<br/>data/ks.sqlite3"]
    LocalStorage["Browser localStorage<br/>模型设置与 API Key"]
  end

  subgraph ExternalModels["外部或本地模型服务"]
    DeepSeek["DeepSeek / DashScope / OpenRouter 等"]
    Ollama["Ollama Local"]
    Mock["Local Mock Provider"]
  end

  User --> ReactUI
  User --> StaticUI
  ReactUI --> ModeSelector
  ReactUI --> TemplateForm
  ReactUI --> ModelSettings
  ReactUI --> RunView
  ReactUI --> DocumentView
  ReactUI --> ReferencesView
  ReactUI --> HistoryView
  ReactUI --> MemoryQuery
  StaticUI --> TemplateForm
  StaticUI --> ModelSettings
  StaticUI --> RunView
  StaticUI --> DocumentView
  StaticUI --> HistoryView

  ModelSettings --> LocalStorage
  TemplateForm --> API
  RunView --> API
  DocumentView --> API
  HistoryView --> API

  API --> Schemas
  API --> Orchestrator
  API --> Storage
  Orchestrator --> AgentRegistry
  Orchestrator --> ProviderRouter
  ProviderRouter --> ProviderClients
  ProviderClients --> DeepSeek
  ProviderClients --> Ollama
  ProviderClients --> Mock
  Storage --> SQLite
```

## 2. 运行流程

```mermaid
sequenceDiagram
  autonumber
  participant U as 用户
  participant UI as Web UI
  participant API as FastAPI /api/runs
  participant DB as SQLite
  participant OR as Orchestrator
  participant IN as Intake Agent
  participant DA as Discussion Agents
  participant MOD as Moderator
  participant IR as Structured IR Agent
  participant OUT as Output Agent
  participant LLM as Model Provider

  U->>UI: 填写模板、上传文档、设置轮次和模型
  UI->>API: POST /api/runs
  API->>DB: 创建 RunRecord，状态 CREATED
  API->>OR: 后台启动执行
  UI->>API: 轮询 GET /api/runs/{run_id}

  OR->>DB: TEMPLATE_VALIDATED
  OR->>IN: 入口模型读取模板和上传文档全文
  IN->>LLM: generate(intake)
  LLM-->>IN: 高密度 briefing
  OR->>DB: 保存 structured_brief

  OR->>DB: 信息传送到讨论组

  alt 第 1 轮并行独立发言
    par Novelty Agent
      DA->>LLM: generate(novelty)
    and Mechanism Agent
      DA->>LLM: generate(mechanism)
    and Feasibility Agent
      DA->>LLM: generate(feasibility)
    and Reviewer Agent
      DA->>LLM: generate(reviewer)
    end
  else 串行第 1 轮
    DA->>LLM: Novelty -> Mechanism -> Feasibility -> Reviewer
  end

  OR->>MOD: 汇总第 1 轮冲突点和遗漏点
  MOD->>LLM: generate(moderator)
  OR->>DB: 保存 Moderator 消息和 IR 摘要

  loop 第 2 轮到第 N 轮
    OR->>DA: 按固定顺序串行反驳/修正
    DA->>LLM: generate(agent)
    OR->>DB: 逐条保存完整发言和 ir_summary
  end

  OR->>IR: 使用各 Agent ir_summary 生成结构化 IR
  IR->>LLM: generate(group_summarizer)
  OR->>DB: 保存 group_summary

  OR->>OUT: 使用 briefing 摘要 + 压缩 IR + 讨论摘要生成最终 Markdown 报告
  OUT->>LLM: generate(output)
  OR->>DB: 保存 final_report，状态 COMPLETED
  UI->>API: 获取完成状态
  API-->>UI: 进度、讨论、IR、报告
```

停止/继续流程：

```mermaid
sequenceDiagram
  autonumber
  participant U as 用户
  participant UI as Web UI
  participant API as FastAPI
  participant OR as Orchestrator
  participant DB as SQLite
  participant LLM as Model Provider

  U->>UI: 点击停止分析
  UI->>API: POST /api/runs/{run_id}/cancel
  API->>DB: 状态更新为 CANCELED，当前 timeline 步骤标记 canceled
  Note over OR,LLM: 已发出的阻塞式 HTTP 请求无法硬中断
  LLM-->>OR: 若稍后返回
  OR->>DB: 检测 CANCELED，丢弃结果，不推进后续 Agent

  U->>UI: 打开失败/停止历史记录
  UI->>API: GET /api/runs/{run_id}
  UI-->>U: 展示失败环节，用户可重选模型
  U->>UI: 点击继续分析
  UI->>API: POST /api/runs/{run_id}/resume
  API->>OR: 从未完成或失败节点继续
  OR->>DB: 复用已完成 briefing、已有发言、已有 IR
```

## 3. 后端模块图

```mermaid
flowchart LR
  Main["main.py<br/>API 路由"]
  Schemas["schemas/models.py<br/>RunCreate / RunRecord / TimelineStep"]
  Runner["orchestrator/runner.py<br/>状态机与 Agent 编排"]
  Registry["agents/registry.py<br/>Agent 角色与系统提示词"]
  Factory["model_providers/factory.py<br/>Provider 创建"]
  Router["model_providers/router.py<br/>按 Agent 分配模型"]
  Compatible["model_providers/compatible.py<br/>OpenAI Compatible / Responses / Anthropic"]
  Mock["model_providers/mock.py<br/>本地 Mock"]
  DB["storage/db.py<br/>SQLite CRUD"]

  Main --> Schemas
  Main --> Runner
  Main --> Factory
  Main --> DB
  Runner --> Registry
  Runner --> DB
  Runner --> Router
  Factory --> Router
  Factory --> Mock
  Router --> Compatible
  Router --> Mock
```

## 4. 数据流与持久化

```mermaid
flowchart TB
  Template["template_input<br/>科研背景模板"]
  Docs["documents<br/>上传文本、类型、注释"]
  ModelSnapshot["model_settings<br/>脱敏后的供应商、模型、Agent 分配快照"]
  Brief["structured_brief<br/>入口模型整合 briefing"]
  Messages["debate_messages<br/>每轮 Agent 完整发言 + ir_summary"]
  Summary["group_summary<br/>结构化 IR"]
  Report["final_report<br/>最终 Markdown 报告"]
  Refs["external_references<br/>外部引用列表"]
  Warnings["ir_warnings<br/>证据绑定校验警告"]
  Timeline["timeline<br/>预计/完成时间、当前阶段"]
  Error["error<br/>失败模块与错误信息"]
  DB["SQLite runs 表<br/>data/ks.sqlite3"]

  Template --> DB
  Docs --> DB
  ModelSnapshot --> DB
  Brief --> DB
  Messages --> DB
  Summary --> DB
  Report --> DB
  Refs --> DB
  Warnings --> DB
  Timeline --> DB
  Error --> DB
```

说明：

- `structured_brief.intake_synthesis` 保存入口模型对模板和上传文档的高密度整合。
- `debate_messages` 保存每个 Agent 的原始 Markdown 发言，并保存面向结构化 IR 的 `ir_summary`。
- `group_summary` 当前语义为结构化 IR，而不是普通聊天式总结。结构化 IR 是中间产物，不对用户直接展示，仅在打包导出中包含。
- `final_report` 由出口 Agent 生成。为降低超时概率，出口阶段不再接收完整讨论全文，而是使用 briefing 摘要、压缩后的结构化 IR 和讨论摘要。
- `external_references` 从各 Agent 的讨论发言中提取的外部论据（论文、博客、数据集等），支持显式小节提取和正则全文 fallback。记忆查询模式自动合并源 Run 的已有引用。
- `ir_warnings` 记录结构化 IR 证据绑定校验的告警信息（如悬空引用、空绑定、仅泛化引用等）。
- `timeline` 保存每个阶段的状态、预计完成时间、最终完成时间和失败信息。
- `model_settings` 保存运行时模型位置快照，但 API Key 会被清空，不写入 SQLite。

## 5. Agent 编排结构

```mermaid
flowchart TB
  Intake["入口 Agent<br/>全文消化模板与上传文档<br/>生成高密度 briefing"]

  subgraph Round1["第 1 轮：可选并行独立发言"]
    Novelty1["Novelty Agent<br/>创新性方向"]
    Mechanism1["Mechanism Agent<br/>机制链条"]
    Feasibility1["Feasibility Agent<br/>资源与实验可行性"]
    Reviewer1["Reviewer Agent<br/>审稿/组会质疑"]
  end

  Moderator["Moderator<br/>汇总冲突点、遗漏点、第 2 轮问题清单"]

  subgraph LaterRounds["第 2 轮到第 N 轮：串行反驳/修正"]
    NoveltyN["Novelty Agent"]
    MechanismN["Mechanism Agent"]
    FeasibilityN["Feasibility Agent"]
    ReviewerN["Reviewer Agent"]
  end

  IRFeedback["每个 Agent 的 IR 摘要<br/>关键主张 / 依据 / 风险 / 下一步"]
  IR["结构化 IR<br/>只读取摘要后的重点内容<br/>共识、分歧、候选方向、证据链、风险、替代路线"]
  Output["出口 Agent<br/>最终 Markdown 报告"]

  Intake --> Round1
  Novelty1 --> Moderator
  Mechanism1 --> Moderator
  Feasibility1 --> Moderator
  Reviewer1 --> Moderator
  Moderator --> NoveltyN --> MechanismN --> FeasibilityN --> ReviewerN
  Novelty1 --> IRFeedback
  Mechanism1 --> IRFeedback
  Feasibility1 --> IRFeedback
  Reviewer1 --> IRFeedback
  Moderator --> IRFeedback
  ReviewerN --> IRFeedback --> IR --> Output
```

说明：

- 第 1 轮并行时，Moderator 读取第 1 轮讨论组 Agent 的完整发言，以便充分识别冲突和遗漏。
- 结构化 IR 不再读取所有完整发言，而是读取各 Agent 在发言末尾提供的 `给结构化 IR 的要点摘要`。
- 串行模式从第 1 轮开始同样要求每个 Agent 产出 IR 摘要，因此后续 IR 阶段不会随轮次线性吞下完整大段文本。

当前 Agent 位置可在 Web UI 中分别绑定不同模型：

- 入口 Agent：推荐长上下文模型，用于消化完整模板和上传文档。
- Novelty Agent：推荐速度较快、发散能力强的模型。
- Mechanism Agent：推荐推理稳定、机制链条表达强的模型。
- Feasibility Agent：推荐成本适中、执行细节可靠的模型。
- Reviewer Agent：推荐批判性和长文本能力强的模型。
- Moderator：推荐总结和对比能力较强的模型。
- 结构化 IR：推荐结构化输出稳定的模型。
- 出口 Agent：推荐中文写作稳定、长输出可靠的模型。

## 6. 模型设置与调用

```mermaid
flowchart LR
  SettingsUI["模型设置 UI"]
  Providers["providers[]<br/>名称 / API Key / Base URL / API 类型 / 模型列表"]
  Assignments["assignments{}<br/>agent_key -> provider:model"]
  Recommender["推荐配置<br/>读取已添加模型 ID 并生成 Agent 分配初稿"]
  LocalStorage["浏览器 localStorage"]
  RunPayload["POST /api/runs<br/>model_settings"]
  Snapshot["SQLite 脱敏快照<br/>api_key 清空"]
  Router["AgentModelRouter"]
  Client["Provider Client"]
  API["供应商 API"]
  Fallback["Local Mock Fallback"]

  SettingsUI --> Providers
  SettingsUI --> Assignments
  SettingsUI --> Recommender --> Assignments
  Providers --> LocalStorage
  Assignments --> LocalStorage
  LocalStorage --> RunPayload
  RunPayload --> Snapshot
  RunPayload --> Router
  Router -->|已分配模型| Client
  Router -->|未分配模型| Fallback
  Client --> API
```

当前支持的 API 类型：

- `OpenAI Compatible`
- `OpenAI Responses`
- `Anthropic Messages`
- `Local Mock`

模型设置中的 API Key 只保存在浏览器 `localStorage`。运行创建时，后端会把模型设置脱敏后写入 SQLite：保留供应商、模型列表和 Agent 分配关系，清空 API Key，便于后续分析失败模块。

## 7. 前端呈现结构（V1.6）

```mermaid
flowchart TB
  LeftNav["左侧导航（220px）<br/>深色 #1f2a33"]
  MainStage["主舞台"]
  IntelRail["右侧情报栏（280px）<br/>运行状态 / 模型 / 导出"]

  subgraph Pages["六个页面"]
    Overview["总览"]
    Create["新建讨论<br/>模式选择 + 模板填写"]
    Debate["讨论台<br/>运行概览 / 时间线 / 讨论"]
    Report["报告<br/>最终报告"]
    References["外部论据<br/>按类型分组 / 渲染 / 导出"]
    History["历史<br/>搜索 / 筛选 / 操作"]
  end

  LeftNav --> Pages
  Pages --> MainStage
  Pages --> IntelRail
```

V1.6 UI 特性：

- 三栏布局：深色左导航 220px + 主舞台弹性宽度 + 右侧情报栏 280px
- 六个页面通过左侧导航切换，无路由，CSS class 控制
- 讨论模式选择器：四种模式的参数区动态联动
- Agent 卡片按角色显示不同颜色顶边框，内容 markdown 渲染
- 按轮次 Tab 切换查看讨论内容
- 结构化 IR 对用户隐藏（中间产物），仅在打包导出中包含
- 外部论据页：按类型分组、markdown 渲染、MD/PDF 导出
- 历史记录支持搜索和状态筛选
- 导出统一 MD/PDF 选择器（DownloadMenu 组件），覆盖报告、打包、论据导出
- 从总览/历史打开正在运行的讨论时，自动恢复 polling，保持停止按钮可用
- COMPLETED 记录确认后跳转新建页预填模板
- 记忆查询面板：选择历史 Run → 读取记忆 → 配置参数 → 启动新讨论
- 响应式断点：≤1280px 隐藏右栏，≤900px 隐藏左导航

Markdown 渲染器支持：标题、有序/无序列表、粗体、行内代码、引用块、分隔线、表格、fenced code block。

## 8. 当前目录结构

```text
K-Storm/
  backend/
    app/
      agents/
        registry.py
      model_providers/
        base.py
        compatible.py
        factory.py
        mock.py
        openai_provider.py
        router.py
      orchestrator/
        runner.py
      schemas/
        models.py
      static/
        index.html
      storage/
        db.py
      main.py
    requirements.txt

  frontend/
    src/
      main.jsx
      styles/app.css
    package.json
    vite.config.js

  data/
    ks.sqlite3

  README.md
  README.zh-CN.md
```

## 9. 项目状态与后续方向

### V1.6 已完成

- 四种讨论模式（完整/聚焦/快速/记忆）
- 记忆查询：基于历史 Run 上下文启动新讨论
- 三栏实验台 UI（深色左导航 + 主舞台 + 情报栏）
- 六个页面：总览、新建讨论、讨论台、报告、外部论据、历史
- 停止/继续/从头重跑
- 统一 MD/PDF 导出选择器（DownloadMenu 组件）
- 外部论据系统：Agent 角色化引用要求、二级提取、分组展示、MD/PDF 导出
- 证据绑定校验（基础版：悬空引用、空绑定、仅泛化引用检测）
- 结构化 IR 对用户隐藏，仅在打包导出中包含
- 从总览/历史打开运行中的讨论时自动恢复 polling
- COMPLETED 记录确认后预填模板重跑

### 待开发

- 证据语义审查 Agent（待实验数据后评估）
- Critique 独立阶段
- 记忆检索引擎（TF-IDF / embedding）
- 模式升级链路（Quick → Focused → Full）
- 预置 Panel 模板
- SSE 实时推送
