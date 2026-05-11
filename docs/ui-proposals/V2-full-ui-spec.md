# K-Storm V2 UI 重构规格

**方向**：C 风格（深色研究控制台）+ 左侧导航 + 页面化视图 + V1.6 讨论模式  
**版本**：V2  
**日期**：2026-05-08

---

## 1. 设计目标

1. **解决臃肿**：当前所有内容挤在一个双栏页面里纵向滚动 → 拆为独立页面，左侧导航切换
2. **承接 V1.6**：讨论模式选择器（Full / Focused / Quick / Memory）嵌入新建流程
3. **强化 C 风格**：深色实验台视觉 + Agent 身份色系统
4. **保持可落地**：不改业务逻辑，先改组件结构和样式

---

## 2. 页面架构

### 2.1 总体布局

```
┌─ Top Bar ──────────────────────────────────────────────────────────┐
│ [K] K-Storm · Research Console        [RUNNING]  [模型设置]        │
├──────────┬─────────────────────────────────────────┬────────────────┤
│          │                                         │                │
│ 左侧导航  │  主舞台（根据导航切换页面）              │  情报侧栏       │
│          │                                         │  （紧凑型）     │
│ ● 总览   │  ┌──────────────────────────────────┐  │                │
│   新建   │  │                                  │  │  ─ 快速操作    │
│   讨论台 │  │  当前页面的核心内容               │  │    新建讨论     │
│   报告   │  │                                  │  │    切换 Run     │
│   历史   │  │                                  │  │  ─ 讨论模式     │
│          │  │                                  │  │    当前模式     │
│          │  │                                  │  │  ─ 模型分配     │
│          │  └──────────────────────────────────┘  │  ─ 导出         │
│          │                                         │                │
├──────────┴─────────────────────────────────────────┴────────────────┤
│ 底部状态栏（可选）                                                   │
│ Run ID · Mode · Rounds · Created                                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 左侧导航

固定宽度 220px，深色底，5 个导航项 + 分隔线。

| 导航项 | 图标 | 对应页面 | 说明 |
|--------|------|---------|------|
| 总览 | Dashboard | OverviewPage | 最近运行概览、项目统计、快速入口 |
| 新建讨论 | Plus | CreatePage | 模板输入 + 模式选择 + 开始讨论 |
| 讨论台 | Debate | DebatePage | 当前运行的多 Agent 讨论舞台 |
| 报告 | Report | ReportPage | 结构化 IR + 最终报告阅读 |
| 历史 | History | HistoryPage | 所有历史 run 列表、管理 |

**交互**：
- 点击切换页面，当前页高亮
- 导航项右侧显示 badge（如讨论台显示当前 run 状态）
- 底部固定：用户信息 / 快捷键提示

### 2.3 页面说明

#### 总览页

用户进入系统后的默认页面。不作为讨论的直接入口，而是作为状态仪表盘。

内容：
- **项目卡片**：当前研究领域、上次 run 时间、run 次数
- **最近讨论**：最近 gat3~5 条 run 摘要
- **快速入口**：新建讨论、继续上次讨论
- **记忆摘要**：最近高频关键词 / 结论

#### 新建讨论页

V1.6 四种模式的入口页。取代当前 TemplatePanel 的"表单即入口"模式。

内容：
- **研究输入区**：(3 个折叠 section：核心输入、补充条件、文档与参数)
- **讨论模式选择器**：(V1.6 核心 UI)

```
┌─ 讨论模式 ───────────────────────────────┐
│                                           │
│  ● 全量审议 Full Deliberation            │
│    全部 Agent · 2~5 轮 · 深度探索         │
│    预估 5~20 分钟 | ~100K tokens          │
│                                           │
│  ○ 专题研讨 Focused Panel                │
│    选定 2~3 个 Agent · 1~2 轮 · 定向讨论 │
│    预估 2~6 分钟 | ~hr30K tokens          │
│    └─ Panel 模板: [实验可行性审查  ▾]     │
│    └─ 参与 Agent:                         │
│       ☑ Feasibility   ☑ Reviewer         │
│       ☐ Novelty       ☐ Mechanism        │
│                                           │
│  ○ 快速探查 Quick Probe                  │
│    单 Agent · 单轮 · 快速验证             │
│    预估 30s~2 分钟 | ~5K tokens           │
│    └─ 目标 Agent: [Reviewer       ▾]     │
│    └─ 问题: ___________________________  │
│                                           │
│  ○ 记忆查询 Memory Query                 │
│    不调模型 · 检索历史结论 · 即时         │
│    └─ 查询: ___________________________  │
│       [查询]                              │
└───────────────────────────────────────────┘
```

交互：
- 切换模式：参数区联动、预估时间/token 变化
- Full 模式：显示轮次、并行首轮开关
- Focused 模式：显示 Panel 模板下拉 + Agent 复选框
- Quick Probe 模式：显示 Agent 单选 + 问题输入框
- Memory Query 模式：显示查询输入框，按钮改为 [查询]

底部固定：**开始分析按钮**（Memory Query 模式显示 [查询]）

#### 讨论台页

**核心视觉焦点**。取代当前 DebateView 的"卡片列表之一"地位，成为独立页面。

内容（按模式不同）：

| 模式 | 讨论台展示 |
|------|-----------|
| Full | Round Tabs + 4 Agent Columns（当前设计） + Briefing 摘要 |
| Focused | 2~3 列 Agent + 结论卡片 + 精简 IR 摘要 |
| Quick | 单 Agent 回答卡片 + 上下文来源标注 + [扩展讨论] 按钮 |
| Memory | 检索结果列表 + 来源标记 + [基于此讨论] 按钮 |

**全量模式的讨论舞台**：

```
┌─ 讨论台 ───────────────────────────────────────┐
│ 第 1 轮 [●]  第 2 轮 [○]  第 3 轮 [○]         │
│                                                  │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│ │🟢 Nvlt │ │🟣 Mech │ │🟡 Feas │ │🔴 Rvwr │   │
│ │        │ │        │ │        │ │        │   │
│ │ 创新   │ │ 机制   │ │ 可行   │ │ 质疑   │   │
│ │ 方向   │ │ 链条   │ │ 性评   │ │ 与      │   │
│ │ ...    │ │ ...    │ │ 估     │ │ 风险    │   │
│ │        │ │        │ │ ...    │ │ ...     │   │
│ │        │ │        │ │        │ │        │   │
│ │[复制]  │ │[复制]  │ │[复制]  │ │[复制]  │   │
│ └────────┘ └────────┘ └────────┘ └────────┘   │
│                                                  │
│ Moderator 总结 (可选折叠)                        │
└──────────────────────────────────────────────────┘
```

#### 报告页

取代当前 ReportView，独立页面化。

内容：
- **结构化 IR**：collapsible sections
- **最终报告**：Markdown 渲染
- **操作栏**：复制、下载 Markdown、下载 JSON、下载 Bundle

#### 历史页

取代当前 HistoryView，独立页面化，可以有更好的列表展示和搜索。

内容：
- **筛选栏**：按模式、状态、日期范围
- **历史列表**：每条显示 field、mode、status、时间、操作按钮
- **批量操作**：删除、导出

### 2.4 情报侧栏（右侧）

收缩为紧凑的辅助信息区，约 260px。

固定内容：
- **当前 Run 状态**：Run ID、模式、进度
- **快速操作**：新建讨论、停止当前 run
- **模型分配**：当前 run 的 agent 模型配置
- **导出快捷方式**
- **记忆侧写**（V1.6 新增）：最近讨论摘要

情报侧栏不随页面切换而消失，始终存在。

---

## 3. 配色 Token

```css
:root {
  /* Background hierarchy */
  --bg-app: #0F1722;
  --bg-topbar: #121C29;
  --bg-nav: #0D1520;
  --bg-panel: #121C2A;
  --bg-panel-2: #162233;
  --bg-elevated: #182536;
  --bg-input: #0F1825;

  /* Border hierarchy */
  --border-primary: #253247;
  --border-secondary: #2A3C54;
  --border-strong: #30445E;
  --border-accent: #39C6B4;

  /* Text hierarchy */
  --text-primary: #EAF2FA;
  --text-secondary: #B7C6D6;
  --text-tertiary: #7F93AB;
  --text-disabled: #5F738A;
  --text-on-accent: #0E1723;

  /* Brand / State */
  --accent-primary: #39C6B4;
  --accent-soft: rgba(57, 198, 180, 0.16);
  --accent-strong: #7CE4D bare;

  --accent-warning: #F2B84B;
  --accent-warning-soft: rgba(242, 184, 75, 0.16);
  --accent-danger: #EC6A97;
  --accent-danger-soft: rgba(236, 106, 151, 0.16);
  --accent-info: #6F7CFF;
  --accent-info-soft: rgba(111, 124, 255, 0.16);

  /* Agent identity colors */
  --agent-novelty: #39C6B4;
  --agent-mechanism: #6F7CFF;
  --agent-feasibility: #F2B84B;
  --agent-reviewer: #EC6A97;

  /* Mode badges */
  --mode-full: #39C6B4;
  --mode-focused: #6F7CFF;
  --mode-quick: #F2B84B;
  --mode-memory: #8CD17D;

  /* Semantic states */
  --state-running: #39C6B4;
  --state-completed: #8CD17D;
  --state-failed: #EC6A97;
  --state-idle: #7F93AB;

  /* Radii */
  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 18px;
  --radius-xl: 22 похаpx;

  /* Spacing */
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  /* Typography */
  --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
  --text-hero: 30px;
  --text-h0: 26px;
  --text-h1: 22px;
  --text-h2: 18px;
  --text-h3: 15px;
  --text-body: 14px;
  --text-caption: 12px;
}
```

---

## 4. 组件树

```
App
├── TopBar
│   ├── Brand
│   ├── RunStatusPill
│   └── QuickActions
├── AppBody
│   ├── LeftNav
│   │   ├── NavItem (总览)
│   │   ├── NavItem (新建讨论)
│   │   ├── NavItem (讨论台)
│   │   ├── NavItem (报告)
│   │   └── NavItem (历史)
│   ├── MainStage
│   │   ├── OverviewPage
│   │   │   ├── ProjectCard
│   │   │   ├── RecentRunsList
│   │   │   └── MemorySummary
│   │   ├── CreatePage
│   │   │   ├── InputSections
│   │   │   │   ├── CoreInputSection
│   │   │   │   ├── SupplementarySection
│   │   │   │   └── DocumentSection
│   │   │   ├── ModeSelector
│   │   │   │   ├── ModeOption (Full)
│   │   │   │   ├── ModeOption (Focused)
│   │   │   │   ├── ModeOption (Quick)
│   │   │   │   └── ModeOption (Memory)
│   │   │   ├── ModeParams (动态)
│   │   │   └── StartButton
│   │   ├── DebatePage
│   │   │   ├── RoundSelector
│   │   │   ├── AgentColumn × 4
│   │   │   └── ModeratorSummary
│   │   ├── ReportPage
│   │   │   ├── StructuredIR
│   │   │   ├── FinalReport
│   │   │   └── ExportActions
│   │   └── HistoryPage
│   │       ├── FilterBar
│   │       └── HistoryList
│   └── IntelRail
│       ├── RunStatusCard
│       ├── QuickActionsCard
│       ├── ModelSnapshotCard
│       ├── ExportCard
│       └── MemoryPanel (V1.6)
├── SettingsModal
└── ErrorBanner
```

---

## 5. 对应现有 React 组件的改造映射

| 当前组件 | 改造为 | 变化说明 |
|---------|--------|---------|
| `App` | `App` | 新增 `LeftNav` + 页面路由（`activePage` state），`workspace` 改为三段布局 |
| `TemplatePanel` | `CreatePage` | 移到独立页面，新增 `ModeSelector` 和 `ModeParams` |
| `RunOverview` | 分布到 `DebatePage` + `TopBar` | Overview 指标卡片移到讨论台页面上方，Run ID 进 IntelRail |
| `DebateView` | `DebatePage` | 独立页面化，保持 Agent 卡片逻辑，增加模式差异渲染 |
| `ReportView` | `ReportPage` | 独立页面化，布局重构 |
| `HistoryView` | `HistoryPage` | 独立页面化，增加模式筛选和更好的列表 |
| `ProgressTimeline` | 保留复用 | 放到 `DebatePage` 和 `TopBar` |
| `Metric` | 保留复用 | 配色升级 |
| `CopyButton` | 保留复用 | 样式适配深色 |
| `SettingsModal` | 保留 | 样式深色化 |
| `BriefBlock` | 保留复用 | 放到 `OverviewPage` |
| `CollapsibleMarkdown` | 保留复用 | 用于 Report |
| *new* 无 | `LeftNav` | 新增组件 |
| *new* 无 | `ModeSelector` | 新增组件，V1.6 核心 UI |
| *new* 无 | `IntelRail` | 新增组件，右侧情报栏 |
| *new* 无 | `MemoryPanel` | 新增组件，V1.6 记忆侧写 |
| *new* 无 | `OverviewPage` | 新增页面 |
| *new* 无 | `CreatePage` | 新增页面 |

---

## 6. 页面状态流转

```
进入 K-Storm
    │
    ▼
总览页 ─────────────────────────────────────────┐
│  · 看到最近 run                                │
│  · 点击"新建讨论" → 新建页                     │
│  · 点击某条历史 → 打开对应 run（讨论台/报告页）│
└────────────────────────────────────────────────┤
                                                 │
新建页 ─────────────────────────────────────┐   │
│  · 填写模板                                │   │
│  · 选择模式                                │   │
│  · 点击"开始分析" → 自动跳转讨论台          │   │
└────────────────────────────────────────────┤   │
                                             │   │
讨论台 ─────────────────────────────────┐   │   │
│  · 实时观察 agent 讨论                 │   │   │
│  · 轮次切换                           │   │   │
│  · 完成后可跳转报告页                  │   │   │
└────────────────────────────────────────┤   │   │
                                         │   │   │
报告页 ─────────────────────────────┐   │   │   │
│  · 阅读 IR 和最终报告              │   │   │   │
│  · 导出操作                       │   │   │   │
└────────────────────────────────────┤   │   │   │
                                     │   │   │   │
历史页 ─────────────────────────┐   │   │   │   │
│  · 查看所有历史 run            │   │   │   │   │
│  · 筛选、删除、打开            │◄──┘◄──┘◄──┘   │
│  · 打开 run → 讨论台或报告页   │                 │
└────────────────────────────────┘◄────────────────┘
```

---

## 7. 情报侧栏

### 7.1 运行中状态

```
┌─ 当前 Run ─────────────┐
│ Run #ks_20260508_01    │
│ 模式：Full Deliberation│
│ 轮次：2 / 3            │
│ 进度：[▪▪▪▪▪▪▪▪━] 67% │
└────────────────────────┘

┌─ 快速操作 ─────────────┐
│ [+ 新建讨论]            │
│ [⏹ 停止当前]            │
└────────────────────────┘

┌─ 模型分配 ─────────────┐
│ Intake    GLM-5.1     │
│ Novelty   DeepSeek    │
│ Mechanism Qwen Max    │
│ Feasblty  Qwen Plus   │
│ Reviewer  DeepSeek    │
└────────────────────────┘
```

### 7.2 记忆侧写（V1.6 新增）

```
┌─ 记忆 ─────────────────┐
│ 📋 最近讨论             │
│  · XX 耐药机制 (1天前) │
│  · YY 通路交叉验证     │
│  · ZZ 可行性评估       │
│                         │
│ 🔍 [搜索记忆...]        │
│ （快速检索历史结论）     │
└────────────────────────┘
```

---

## 8. 改造成本评估

| 改动类别 | 工作量 | 风险 |
|---------|--------|------|
| 页面路由系统 | 中等 | 低：不要求真实 router，state 切换即可 |
| 左侧导航 | 低 | 低 |
| 页面拆分（5 个 page） | 中等 | 低：组件逻辑不动，只是换容器 |
| 情报侧栏 | 低 | 低：内容本身已存在，改排布 |
| 模式选择器 | 中等 | 中：需要联动参数 + 后端 schema 适配 |
| 深色主题 token | 低 | 低 |
| 记忆侧写 | 待 V1.5 IR 结构确定 | 中：依赖 V1.5 |

---

## 9. 实现顺序建议

### Phase 1 · 骨架重铸
1. `App` 改为 TopBar + LeftNav + MainStage + IntelRail
2. 5 个 page 占位
3. 深色 token 应用

### Phase 2 · 页面迁移
4. `TemplatePanel` → `CreatePage`
5. `DebateView` → `DebatePage`
6. `ReportView` → `ReportPage`
7. `HistoryView` → `HistoryPage`
8. `OverviewPage` 新建

### Phase 3 · V1.6 融合
9. `ModeSelector` + `ModeParams`
10. 后端 schema 适配
11. 模式差异化渲染

### Phase 4 · 收尾
12. 情报侧栏完善
13. 记忆侧写（等 V1.5 IR 稳定）
14. 交互细节打磨

---

## 10. 一句话总结

**从"一页到底"变为"导航驱动 + 页面聚焦"，从"只有全量讨论"变为"四种可编排模式"。C 风格深色控制台贯穿始终，左侧导航承载结构，中央舞台承载内容，右侧情报栏承载系统信息。**
