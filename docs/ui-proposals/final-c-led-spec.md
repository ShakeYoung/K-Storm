# K-Storm 最终推荐稿

**方向**：C 主导，吸收 A 的稳定骨架  
**建议命名**：`K-Storm Research Console`

这个版本的核心原则是：

- 用 **A 的工作流骨架** 保证清晰、可信、可持续使用
- 用 **C 的视觉语言与舞台中心** 强化多 Agent 研究实验平台的身份感
- 让用户第一眼感受到这是一个 **研究控制台**，而不是普通表单后台

---

# 1. 最终页面结构图

## 1.1 总体布局

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Global Top Bar                                                                             │
│ Brand · Run Status · Quick Actions · Model Settings                                        │
├───────────────┬───────────────────────────────────────────────────────┬──────────────────────┤
│ Input Dock    │ Observatory Stage                                    │ Intelligence Rail    │
│ 左侧输入工作台 │ 中央主舞台                                           │ 右侧情报栏            │
│               │                                                       │                      │
│ 1. 核心输入    │ A. Run Overview                                       │ a. Output Switcher   │
│ 2. 补充条件    │ B. Debate Stage                                       │ b. Model Assignment  │
│ 3. 文档与参数  │    - Round Tabs                                       │ c. Export Center     │
│ 4. Start CTA  │    - 4 Agent Columns                                  │ d. Run History Mini  │
│               │    - Active / Failed / Done states                    │ e. Metadata / IDs    │
│               │ C. Brief / Structured Summary Drawer or Subpanel      │                      │
└───────────────┴───────────────────────────────────────────────────────┴──────────────────────┘
```

## 1.2 视觉层级

```text
Level 1  中央视觉焦点：Debate Stage
Level 2  左侧输入台 + 右侧情报栏
Level 3  概览指标、导出、历史、模型分配
Level 4  次级说明文案、帮助提示、元数据
```

## 1.3 页面区块详细结构

### Top Bar
- 左：K-Storm 标识、产品副标题
- 中：当前运行状态 `READY / RUNNING / FAILED / COMPLETED`
- 右：模型设置、重新分析、全局快捷操作

### Input Dock
- 固定左栏，不跟随结果区切换而消失
- 三段式组织：
  1. 核心输入
  2. 补充条件
  3. 文档与运行参数
- 底部固定主按钮：开始分析
- 显示模板完成度环

### Observatory Stage
- 上半区：运行概览 + timeline
- 中心区：讨论舞台
- 下挂子区：结构化 briefing 或 moderator summary
- 视觉上以“Agent 信号柱”形成舞台中心

### Intelligence Rail
- 结构化输出切换
- 模型分配概览
- 导出按钮组
- 历史记录摘要
- 当前 run 元信息

---

# 2. 页面行为建议

## 2.1 初始态
- 中央显示空态，强调“从左侧填写研究输入开始”
- 右栏显示可用能力说明，不显示冗长空列表

## 2.2 运行中
- Top Bar 状态高亮
- 概览区 timeline 动态更新
- Debate Stage 默认聚焦当前轮次
- Intelligence Rail 中导出区弱化，模型分配和当前阶段高亮

## 2.3 运行完成
- Debate Stage 仍保留，但默认折叠到最近轮次
- Intelligence Rail 将“报告 / IR”切换提升优先级
- 导出区变为高亮主操作

## 2.4 运行失败
- Top Bar 与当前阶段显示失败态
- 右栏暴露 rerun / diagnose 操作
- 中央舞台保持失败前最后状态，避免信息中断

---

# 3. 配色 Token

下面这套 token 是为“深色研究控制台”准备的，重点不是赛博炫技，而是高可读、强结构、适度未来感。

## 3.1 Core Tokens

```css
:root {
  /* Background */
  --bg-app: #0F1722;
  --bg-topbar: #121C29;
  --bg-panel: #121C2A;
  --bg-panel-2: #162233;
  --bg-elevated: #182536;
  --bg-input: #0F1825;
  --bg-overlay: rgba(7, 12, 18, 0.72);

  /* Border */
  --border-primary: #253247;
  --border-secondary: #2A3C54;
  --border-strong: #30445E;
  --border-accent: #39C6B4;

  /* Text */
  --text-primary: #EAF2FA;
  --text-secondary: #B7C6D6;
  --text-tertiary: #7F93AB;
  --text-disabled: #5F738A;
  --text-on-accent: #0E1723;

  /* Brand / State */
  --accent-primary: #39C6B4;
  --accent-primary-soft: rgba(57, 198, 180, 0.16);
  --accent-primary-strong: #7CE4D6;

  --accent-warning: #F2B84B;
  --accent-warning-soft: rgba(242, 184, 75, 0.16);

  --accent-danger: #EC6A97;
  --accent-danger-soft: rgba(236, 106, 151, 0.16);

  --accent-info: #6F7CFF;
  --accent-info-soft: rgba(111, 124, 255, 0.16);

  /* Agent Identity */
  --agent-novelty: #39C6B4;
  --agent-mechanism: #6F7CFF;
  --agent-feasibility: #F2B84B;
  --agent-reviewer: #EC6A97;

  /* Semantic State */
  --state-ready: #7F93AB;
  --state-running: #39C6B4;
  --state-completed: #8CD17D;
  --state-failed: #EC6A97;

  /* Radius */
  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 18px;
  --radius-xl: 22px;

  /* Shadow */
  --shadow-panel: 0 10px 30px rgba(0, 0, 0, 0.18);
  --shadow-focus: 0 0 0 3px rgba(57, 198, 180, 0.18);
}
```

## 3.2 Typography Tokens

```css
:root {
  --font-family-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;

  --text-hero: 30px;
  --text-h1: 24px;
  --text-h2: 20px;
  --text-h3: 16px;
  --text-body: 14px;
  --text-caption: 12px;

  --weight-regular: 500;
  --weight-medium: 600;
  --weight-semibold: 700;
  --weight-bold: 760;
}
```

## 3.3 Spacing Tokens

```css
:root {
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-7: 28px;
  --space-8: 32px;
}
```

---

# 4. 组件分区说明

## 4.1 Zone A · Global Top Bar
**目标**：建立品牌、状态、全局操作中心

包含：
- Brand
- Status Pill
- Model Settings Entry
- Retry / quick actions

设计要求：
- 高度紧凑
- 状态 pill 必须一眼可见
- 不放复杂表单，只做全局控制

---

## 4.2 Zone B · Input Dock
**目标**：稳定输入台，承担高频配置工作

包含：
- Template Fields
- Completion Ring
- Document Upload
- Rounds / Parallel First Round
- Start Action

设计要求：
- 左栏固定
- 分段清晰，建议做 section cards
- CTA 固定在视野底部附近
- 输入控件深色但保持高对比

子区建议：
1. `Core Research Input`
2. `Constraints & Output Intent`
3. `Documents & Run Params`

---

## 4.3 Zone C · Run Overview
**目标**：把系统状态翻译成可快速理解的仪表信息

包含：
- Run ID
- Rounds
- Debate Message Count
- Status
- Timeline
- Briefing Summary

设计要求：
- 不追求信息多，追求信号强
- 指标卡最多 4 个
- Timeline 一定要有高亮当前阶段能力

---

## 4.4 Zone D · Debate Stage
**目标**：成为整页的主舞台

包含：
- Round Tabs
- Agent Columns
- Per-agent message body
- Copy actions
- Running / failed state hints

设计要求：
- 每个 Agent 独立身份色
- 更像“信号柱”而非普通白卡片
- 轮次切换清晰
- 默认展示当前轮次，减少滚动噪声

推荐结构：
- 每列顶部：Agent 名称 + 模型标签
- 中部：内容摘要 / 主体
- 底部：copy / state / meta

---

## 4.5 Zone E · Intelligence Rail
**目标**：承载系统级次级信息，不和主舞台争夺焦点

包含：
- Output Switcher: Report / Structured IR / History
- Model Assignment Snapshot
- Export Actions
- History Mini List
- Metadata

设计要求：
- 宽度窄于中心区
- 更像仪表栏而非主内容区
- 历史记录默认只显示摘要，完整列表用 drawer 或 modal

---

## 4.6 Zone F · Modal Layer
**目标**：容纳高复杂配置，不污染主舞台

包含：
- SettingsModal
- Large History Inspector（建议新增）
- Model Assignment Details（可选新增）

设计要求：
- 保持深色主题统一
- 强化分区层级
- 避免现在这种“内容很多但关系不够明显”的问题

---

# 5. 对应现有 React 组件的改造映射

下面按你当前 `frontend/src/main.jsx` 的组件结构来映射。

## 5.1 App
**现状职责**
- 顶层布局
- 状态管理
- 左模板 + 右结果区
- settings modal 控制

**改造方向**
- 仍然保留为顶层 orchestrator
- 将当前 `workspace` 从双栏改成三段结构：
  1. `InputDock`
  2. `MainStage`
  3. `IntelligenceRail`

**建议拆分**
- `TopBar`
- `InputDock`
- `MainStage`
- `IntelligenceRail`
- `OverlayLayer`

---

## 5.2 TemplatePanel → InputDock
**现状职责**
- 表单输入
- 文档上传
- 运行参数
- 提交

**改造后角色**
- 成为左侧固定输入台 `InputDock`
- 内部再拆成 3 个 section

**建议内部拆分**
- `InputCompletionHeader`
- `CoreInputSection`
- `SupplementarySection`
- `DocumentsAndParamsSection`
- `StartRunBar`

**样式变化**
- 从白底长表单改为深色分段卡片
- CTA 固定底部

---

## 5.3 RunOverview → OverviewDeck
**现状职责**
- 指标
- timeline
- briefing

**改造后角色**
- 保留，但提升为中央主区顶部仪表层
- 结构改为 `metric cards + timeline + briefing summary`

**建议内部拆分**
- `RunMetrics`
- `RunTimeline`
- `BriefingSnapshot`

**说明**
- `CollapsibleMarkdown` 可以继续复用，用于 briefing 摘要卡

---

## 5.4 DebateView → DebateStage
**现状职责**
- Round tabs
- message grid

**改造后角色**
- 成为页面视觉中心
- 从“普通消息卡片网格”改为“Agent identity columns”

**建议内部拆分**
- `RoundSelector`
- `AgentColumn`
- `AgentColumnHeader`
- `AgentColumnBody`
- `AgentColumnMeta`

**说明**
- 当前 `message-grid` 可以演化为 4 列固定舞台
- 每列绑定 agent identity token

---

## 5.5 ReportView → OutputPanel
**现状职责**
- group summary
- final report
- export actions

**改造后角色**
- 不再占据主区整块纵向空间
- 移入右侧 `IntelligenceRail` 的输出切换模块，或抽屉式展开

**建议变化**
- 默认只显示输出摘要和操作按钮
- 点击后展开 report viewer

**建议内部拆分**
- `OutputSwitcher`
- `StructuredIRPreview`
- `FinalReportPreview`
- `ExportActions`

---

## 5.6 HistoryView → HistoryMini + HistoryDrawer
**现状职责**
- 完整历史记录列表
- 删除、打开、导出

**改造后角色**
- 页面内默认只保留 `HistoryMini`
- 完整列表进入 `HistoryDrawer` 或 modal

**原因**
- 现在历史记录直接占一大块主页面高度，打断主舞台
- 它更适合作为二级信息

**建议拆分**
- `HistoryMini`
- `HistoryDrawer`
- `HistoryActions`

---

## 5.7 SettingsModal
**现状职责**
- 供应商管理
- 模型发现
- 模型分配

**改造后角色**
- 保留 modal 形式不变
- 但视觉风格要完全纳入深色控制台系统

**建议变化**
- 左：provider list
- 中：provider config
- 右：model discovery / assignment helper

如果你暂时不想重构逻辑，可以先只改样式与层级。

---

## 5.8 ProgressTimeline / Metric / BriefBlock / CopyButton
这些都属于 **低成本高收益复用件**。

### 保留并升级
- `ProgressTimeline` → 改为更像状态仪表线
- `Metric` → 改为深色指标卡
- `BriefBlock` → 改为 briefing capsule
- `CopyButton` → 保持复用

它们不用推倒重来，重点是换容器语义和样式。

---

# 6. CSS 层面的重构优先级

## 第一阶段：只改骨架和主题
- 全局深色主题 token
- `workspace` 改三栏
- `panel` 改为深色层级面板
- `template-pane / results-pane` 重组

## 第二阶段：把 DebateView 舞台化
- 建立 agent identity 色
- 固定列布局
- 调整 round tabs
- 优化 markdown 内容滚动区域

## 第三阶段：把 Report / History 从主区降级到右栏
- Output switcher
- History mini + drawer
- Export center

## 第四阶段：统一 modal / overlay 体系
- SettingsModal 深色化
- 历史详情抽屉
- 可选的 briefing 展开层

---

# 7. 你现在这套代码最适合的落地方式

我建议不要一上来重写所有组件，而是按下面顺序推进：

1. **先改布局骨架**
   - `App` 从双栏改三栏
2. **再改视觉 token**
   - 统一深色控制台主题
3. **优先重做 DebateView**
   - 因为这是最能立住产品身份的部分
4. **再压缩 ReportView / HistoryView 到右栏**
5. **最后重整 SettingsModal**

这样收益最大，风险也更可控。

---

# 8. 最终一句判断

如果要一句话概括这个终稿方向：

> 它应该看起来像一个可以长期使用的研究控制台，而中央那块多 Agent debate 舞台，必须让人一眼记住这是 K-Storm。
