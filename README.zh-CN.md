# K-Storm（KS）

K-Storm 是一个本地运行的科研选题多 Agent 头脑风暴工具。它把用户填写的科研背景模板和上传文档转成高密度 briefing，再让多个 Agent 进行可控的多轮讨论，最后生成可复制的 Markdown 选题报告。

**当前版本：V1.6** — 支持四种讨论模式、记忆查询、以及重新设计的实验台 UI。

项目架构图见 [docs/ARCHITECTURE.zh-CN.md](docs/ARCHITECTURE.zh-CN.md)。

## 讨论模式（V1.6）

| 模式 | Agent 数 | 轮次 | 适用场景 |
|:--|:--|:--|:--|
| **完整讨论** | 4 + Moderator | 1–5 | 全面头脑风暴，生成完整 IR 和报告 |
| **聚焦小节** | 自选 2–3 | 1–2 | 针对特定问题的深度讨论 |
| **快速探测** | 1 | 1 | 对单个问题做快速可行性判断 |
| **记忆查询** | 自选 | 1–5 | 基于历史讨论的上下文启动新讨论 |

### 记忆查询

选择一条已完成的历史讨论，读取其记忆上下文（已知事实、未知问题、约束条件、机会点），选择 Agent 和轮次，输入新问题后启动新讨论。新讨论会继承源 Run 的 briefing 和 IR 作为记忆注入，结果与源 Run 通过 `source_run_id` 关联。

## 当前能力

- 科研头脑风暴模板填写
- 入口 Agent 全文消化模板和上传文档，生成高密度 briefing
- 上传文本类 design / experiment-data 文档，并为每份文档添加注释
- 可配置讨论轮次（1-5 轮）：
  - Novelty Agent：创新性
  - Mechanism Agent：机制深挖
  - Feasibility Agent：实验可行性
  - Reviewer Agent：审稿/评审质疑
- 第 1 轮可选并行独立发言
- Moderator 汇总第 1 轮冲突点、遗漏点和第 2 轮问题清单
- 第 2 轮开始按固定顺序串行反驳/修正
- 每个讨论 Agent 在完整发言末尾追加“给结构化 IR 的要点摘要”
- 结构化 IR：只消费各 Agent 摘要后的重点内容，汇总共识、分歧、候选方向、证据链、风险和替代路线
- 出口 Agent 基于压缩后的结构化 IR 生成最终 Markdown 报告
- 结构化 IR 和最终报告拆分为两个独立展示区域，各自固定高度、内部滚动、可复制
- 最终报告阶段使用“入口 briefing 摘要 + 结构化 IR + 讨论摘要”，降低长上下文导致的超时概率
- SQLite 本地历史记录
- Markdown 渲染：支持标题、列表、表格、引用、分隔线、代码块等常用格式
- 区域复制：入口 briefing、每个 Agent 发言、结构化 IR、最终报告均可单独复制
- Web 页面模型设置：
  - 按 `CODING PLAN`、`API` 分组显示供应商
  - 添加/删除供应商
  - 填写 API Key、Base URL、API 类型
  - 手动添加模型
  - 从供应商 `/models` 接口读取模型候选；用户选择后再加入已添加模型
  - Coding Plan 类供应商使用固定模型预设，避免通用 `/models` 不可用导致误判
  - 将任意模型分配到入口、讨论组、Moderator、结构化 IR、出口等 Agent 位置
  - Agent 模型位置显示中文名和英文名，便于和失败环节匹配
  - 可根据已添加模型自动生成推荐 Agent 配置，用户可一键应用后继续手动调整
- 运行时进度展示：
  - 默认收起，仅展示当前阶段
  - 可展开查看完整时间线
  - 显示预计完成时间、最终完成时间和失败模块
  - 支持“停止分析”，主动将运行标记为 `CANCELED`
  - 失败或停止后的历史记录支持打开并从失败位置继续分析
- V1.6 实验台 UI：
  - 三栏布局：深色左导航（220px）、主舞台、右侧情报栏（280px）
  - 六个页面：总览、新建讨论、讨论台、报告、外部论据、历史
  - Agent 卡片按角色显示不同颜色顶边框
  - 按轮次 Tab 切换查看讨论内容
  - 历史记录支持搜索和状态筛选
  - 导出统一 MD/PDF 选择器，支持 Markdown、PDF（打印）、JSON Bundle、外部论据导出
  - COMPLETED 状态的记录支持确认后跳转新建页预填模板，修改后重新分析
- 外部论据系统：
  - 各 Agent 按角色要求引用外部论文、博客、数据集
  - 二级提取：优先解析 Agent 输出的显式引用小节，未找到则正则全文 fallback
  - 独立的外部论据页面，按类型分组展示，支持 markdown 渲染和 MD/PDF 导出
  - 记忆查询模式自动合并源 Run 的已有论据
- 结构化 IR 对用户隐藏（中间产物），仅在打包导出中包含
- 从总览/历史打开正在运行的讨论时，自动恢复 polling 并保持停止按钮可用

## 技术栈

- 前端：React + Vite
- 后端：FastAPI
- 数据库：SQLite
- Agent 编排：自研状态机
- 模型接入：
  - 默认本地 mock provider，无 API Key 也能跑完整流程
  - 支持 OpenAI Compatible、OpenAI Responses、Anthropic Messages

## 快速启动

### 1. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

默认使用 mock provider，无需任何 API Key。如需配置外部模型：

```bash
cp ../.env.example ../.env
# 编辑 .env 填入 API Key
```

也可以在浏览器“模型设置”中直接配置，无需编辑 .env。

### 2. 启动 React 前端（推荐）

Vite 前端包含完整的 V1.6 功能：

```bash
cd frontend
npm install
npm run dev
```

打开：

```text
http://localhost:5173
```

### 3. 后端静态 UI

后端同时提供一版免构建的 Web UI：

```text
http://127.0.0.1:8000
```

这是早期版本，不包含 V1.6 讨论模式和新的实验台 UI，适合没有 npm 的环境快速试用。

## 模型设置说明

点击页面右上角“模型设置”。

### 供应商分组

设置页参考常见模型客户端的结构，默认分为：

- `CODING PLAN`：例如 Kimi Coding Plan、百炼 Coding Plan、火山引擎 Coding Plan。
- `API`：例如 DeepSeek、DashScope、OpenAI、OpenRouter、Ollama、MiniMax、SiliconFlow。

### 添加供应商

可填写：

- 名称：例如 DeepSeek
- API Key：供应商提供的 key
- Base URL：例如 `https://api.deepseek.com/v1`
- 证书校验：默认严格校验；如果公司代理或自签名证书导致 TLS 失败，可临时打开“允许不安全证书”
- API 类型：
  - `OpenAI Compatible`
  - `Anthropic Messages`
  - `OpenAI Responses`

API Key 默认只保存在本机浏览器 localStorage 中，不会写入 SQLite 历史记录。

每次运行会在 SQLite 中保存一份脱敏后的 `model_settings` 快照，用于后续定位失败时的 Agent 模型位置。该快照会保留供应商、模型列表和 Agent 分配关系，但会清空 API Key。

其中 `OpenAI Compatible`、`Anthropic Messages`、`OpenAI Responses` 已有后端请求适配。

“允许不安全证书”只建议在本地开发、公司代理或可信内网环境中使用；公网 API 正常情况下不应打开。

### 添加模型

可以手动添加：

- 显示名称：例如 `DeepSeek V4 Flash`
- 模型 ID：例如 `deepseek-v4-flash`

也可以点击“读取模型”。普通 API 供应商后端会请求：

```text
{Base URL}/models
```

并把返回结果展示为候选模型。用户可以搜索候选模型，点击候选项或输入模型 ID 后再添加到当前供应商，避免一次性加入过多模型。

`Kimi Coding Plan`、`百炼 Coding Plan`、`火山引擎 Coding Plan` 这类套餐入口不一定提供通用 `/models` 列表接口，KS 会按官方文档维护一组可选模型预设，避免“Base URL 正确但模型列表为空”的误判。

### 当前默认供应商地址

- Kimi Coding Plan：`https://api.kimi.com/coding/v1`，模型 `kimi-for-coding`
- 百炼 Coding Plan：`https://coding.dashscope.aliyuncs.com/v1`
- 火山引擎 Coding Plan：`https://ark.cn-beijing.volces.com/api/coding/v3`
- DeepSeek：`https://api.deepseek.com/v1`
- DashScope（百炼按量 API）：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- OpenAI：`https://api.openai.com/v1`
- OpenRouter：`https://openrouter.ai/api/v1`
- Ollama：`http://127.0.0.1:11434/v1`
- MiniMax：`https://api.minimax.io/v1`
- SiliconFlow：`https://api.siliconflow.cn/v1`

注意：部分 Coding Plan 文档明确限制使用场景，接入前请确认你的 Key、Base URL、模型 ID 和供应商条款匹配。

### 分配模型到 Agent

支持为以下位置分别选择模型：

- 入口 Agent
- Novelty Agent
- Mechanism Agent
- Feasibility Agent
- Reviewer Agent
- Moderator
- 结构化 IR
- 出口 Agent

例如，接入 `deepseek-v4-flash` 后，可以把它放在入口 Agent，也可以放在讨论组中任意 Agent 位置。未选择模型的位置会自动使用本地 mock provider。

点击“推荐配置”后，KS 会读取已添加模型和模型 ID，按以下偏好生成一套初始配置：

- 入口 Agent：优先长上下文、稳定理解模型。
- Novelty / Feasibility：优先快速、成本适中的模型。
- Mechanism / Reviewer：优先推理稳定、批判性较强的模型。
- Moderator / 结构化 IR：优先总结、结构化能力强的模型。
- 出口 Agent：优先中文写作稳定、长输出可靠的模型。

推荐配置只是初稿，用户可以继续逐项调整，再点击“保存设置”。

## API 简表

```text
POST   /api/runs
GET    /api/runs/{run_id}
GET    /api/runs/{run_id}/messages
GET    /api/runs/{run_id}/report
POST   /api/runs/{run_id}/rerun
POST   /api/runs/{run_id}/resume
POST   /api/runs/{run_id}/cancel
POST   /api/runs/{run_id}/references
POST   /api/memory/query
GET    /api/history
GET    /api/history/location
POST   /api/history/delete
POST   /api/models/discover
```

## 运行数据

SQLite 数据库默认位于：

```text
data/ks.sqlite3
```

保存内容包括：

- 用户模板输入
- 上传文档文本、文档类型和注释
- 结构化 briefing
- 每轮 Agent 发言
- 每轮 Agent 面向结构化 IR 的要点摘要 `ir_summary`
- Moderator 汇总
- 结构化 IR
- 最终报告
- 外部引用列表 `external_references`（论文、博客、数据集等）
- 证据绑定校验警告 `ir_warnings`
- 运行状态、时间线、错误信息
- 脱敏后的模型位置快照 `model_settings`

不会保存页面模型设置里的 API Key。

## 当前工作流

```text
模板 + 上传文档
  ↓
入口 Agent 全文消化并生成 briefing
  ↓
第 1 轮可选并行独立发言
  ↓
Moderator 汇总冲突点和遗漏点
  ↓
第 2 轮起串行反驳/修正
  ↓
各 Agent 提供给 IR 的要点摘要
  ↓
结构化 IR 只读取摘要后的重点内容
  ↓
最终 Markdown 报告
```

如果第 1 轮选择并行讨论，Moderator 会读取第 1 轮讨论组 Agent 的完整发言，以便充分判断冲突和遗漏；结构化 IR 阶段则只读取各 Agent 的要点摘要。  
如果从第 1 轮开始串行讨论，每个 Agent 同样会在完整发言后附加 IR 摘要，结构化 IR 仍只消费摘要后的重点内容。

## 停止与继续分析

- `停止分析`：用户可以在运行中主动停止当前 run。当前已经发出的模型 HTTP 请求不能从 socket 层硬杀掉，但其返回结果会被丢弃，不会继续推进后续 Agent。
- `继续分析`：失败或已停止的 run 可从失败位置继续执行。继续前可以先打开“模型设置”，针对失败环节重选模型。
- `从头重跑`：保留原逻辑，基于同一模板和文档创建一条新的 run，从入口阶段重新开始。

## GitHub 上传前注意

项目已包含 `.gitignore`，默认忽略 `data/*.sqlite3`、`node_modules/`、`__pycache__/`、`.env` 等本地文件。上传前仍建议手动确认：

```bash
find . -name "ks.sqlite3" -type f
find . -name "__pycache__" -type d
find . -name "*.pyc" -type f
```

不要把真实 API Key、历史运行数据库、上传文档内容提交到 GitHub。

## 目录结构

```text
backend/
  app/
    agents/
    model_providers/
    orchestrator/
    schemas/
    static/
    storage/
frontend/
  src/
```

## 后续可扩展方向

- 证据绑定校验：验证每个候选方向是否绑定了真实、非 fallback 的 evidence_refs（已实现基础版，语义审查待实验数据）
- Critique 独立阶段：在 group_summary 后增加独立批判轮次
- 记忆检索引擎：TF-IDF / embedding 语义检索，替代当前的整 Run 加载
- 模式升级链路：Quick → Focused → Full 的上下文延续按钮
- 预置 Panel 模板：实验可行性审查、创新方向挖掘等一键模板
- SSE 实时推送讨论进度
- 文献检索 Agent
- PDF / DOCX 解析
- 组会 PPT 生成
