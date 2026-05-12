<div align="center">

<img src="assets/k-storm-icon.svg" width="180" alt="K-Storm logo">

# K-Storm

**本地多 Agent 科研选题头脑风暴**

把你的科研模板 + 上传文档 → 结构化 briefing → 可控多轮 Agent 讨论 → Markdown 选题报告

[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://github.com/ShakeYoung/K-Storm/blob/main/LICENSE)
[![Version](https://img.shields.io/badge/version-v1.6-green.svg?style=flat-square)](https://github.com/ShakeYoung/K-Storm)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

[中文文档](./README.zh-CN.md) | [English](./README.md)

</div>

---

## ⚡ 项目概述

K-Storm 是一个**完全本地运行**的科研选题多 Agent 头脑风暴工具。多个 AI Agent（Novelty、Mechanism、Feasibility、Reviewer）围绕你的研究问题进行结构化多轮讨论，最终生成可直接用于开题报告或组会讨论的 Markdown 报告。

**零云端依赖** — 内置 mock provider 开箱即用，接入任意 OpenAI 兼容或 Anthropic API 即可解锁真实 Agent 推理。

## 🪄 讨论模式（V1.6）

| 模式 | Agent 数 | 轮次 | 适用场景 |
|:--|:--|:--|:--|
| **完整讨论** | 4 + Moderator | 1–5 | 全面头脑风暴，生成完整 IR 和报告 |
| **聚焦小节** | 自选 2–3 | 1–2 | 针对特定问题的深度讨论 |
| **快速探测** | 1 | 1 | 对单个问题做快速可行性判断 |
| **记忆查询** | 自选 | 1–5 | 基于历史讨论的上下文启动新讨论 |

<details>
<summary><b>🧠 记忆查询说明</b></summary>

选择一条已完成的历史讨论，读取其记忆上下文（已知事实、未知问题、约束条件、机会点），选择 Agent 和轮次，输入新问题后启动新讨论。新讨论会继承源 Run 的 briefing 和 IR 作为记忆注入，结果与源 Run 通过 `source_run_id` 关联。

</details>

## ✨ 核心能力

- 📋 **结构化模板填写** — 研究方向、背景、已有基础、约束条件、研究目标
- 📎 **文档上传** — 支持 design / experiment-data 类型标注和逐文档注释
- 🧠 **入口 Agent** — 全文消化模板和文档，生成高密度 briefing
- 🤖 **4 个讨论 Agent** — Novelty（创新性）· Mechanism（机制深挖）· Feasibility（可行性）· Reviewer（审稿质疑）
- 🎯 **Moderator** — 汇总冲突点、遗漏点，生成下一轮问题清单
- 📊 **结构化 IR** — 候选方向、证据链、批判点、风险与替代路线
- 📝 **最终 Markdown 报告** — 开题/组会可用，支持逐区域复制
- 📚 **外部论据** — Agent 引用论文/博客/数据集；二级提取 + 独立论据页面 + 分组导出
- 🔄 **运行管理** — 停止分析、从失败位置继续、从头重跑
- 🗂️ **历史记录** — 搜索、状态筛选、打开历史讨论、删除
- 📤 **多格式导出** — MD/PDF、JSON Bundle、外部论据导出
- ⚙️ **按 Agent 分配模型** — mock / OpenAI / Anthropic 混配

## 🏗️ 系统架构

```mermaid
flowchart TB
  User["用户 / 科研人员"]

  subgraph Browser["浏览器 Web UI"]
    ReactUI["React + Vite 主前端（V1.6）"]
    ModelSettings["模型设置"]
    ModeSelector["讨论模式选择"]
    TemplateForm["头脑风暴模板"]
    RunView["讨论台"]
    DocumentView["报告页"]
    HistoryView["历史记录"]
  end

  subgraph Backend["FastAPI Backend"]
    API["API Layer"]
    Orchestrator["Agent Orchestrator"]
    AgentRegistry["Agent Registry"]
    ProviderRouter["Agent Model Router"]
    ProviderClients["Model Providers\nOpenAI / Anthropic / Mock"]
    Storage["SQLite Storage"]
  end

  subgraph Models["外部模型服务"]
    DeepSeek["DeepSeek / DashScope / OpenRouter"]
    Ollama["Ollama Local"]
    Mock["Local Mock"]
  end

  User --> ReactUI
  ReactUI --> API
  API --> Orchestrator
  Orchestrator --> AgentRegistry
  Orchestrator --> ProviderRouter
  ProviderRouter --> ProviderClients
  ProviderClients --> DeepSeek
  ProviderClients --> Ollama
  ProviderClients --> Mock
  API --> Storage
```

完整架构文档见 [docs/ARCHITECTURE.zh-CN.md](docs/ARCHITECTURE.zh-CN.md)，包含运行流程时序图、后端模块图、数据流图和 Agent 编排结构。

<details>
<summary><b>🔄 运行流程</b></summary>

```text
模板 + 上传文档
  ↓
入口 Agent → 高密度 briefing
  ↓
第 1 轮（可选并行）
  ↓
Moderator → 冲突/遗漏汇总 + 下一轮问题清单
  ↓
第 2 轮起串行反驳/修正
  ↓
各 Agent → IR 要点摘要（压缩）
  ↓
结构化 IR → 候选方向 + 证据链 + 风险
  ↓
出口 Agent → 最终 Markdown 报告
```

</details>

<details>
<summary><b>📁 项目结构</b></summary>

```text
backend/
  app/
    agents/              Agent 定义与注册
    model_providers/     Mock / OpenAI / Anthropic 供应商
    orchestrator/        运行执行状态机
    schemas/             Pydantic 模型
    storage/             SQLite 数据层
    static/              早期独立 UI
    main.py              FastAPI 入口
frontend/
  src/
    main.jsx             React 应用
    styles/
      app.css            样式表
docs/
  ARCHITECTURE.zh-CN.md       架构文档
  K-STORM-ROADMAP.zh-CN.md    演进路线图
```

</details>

## 🚀 快速启动

### 环境要求

- **Python** 3.10+
- **Node.js** 18+（用于 Vite 前端）

### 1. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

默认使用 **mock provider**，无需任何 API Key。

### 2. 启动 React 前端（推荐）

Vite 前端包含完整的 V1.6 功能：

```bash
cd frontend
npm install
npm run dev
```

打开 <http://localhost:5173>。

> 后端同时提供一版免构建 UI：<http://127.0.0.1:8000>（早期版本，不含 V1.6 新功能，适合没有 npm 的环境快速试用）。

### 3. 配置模型（可选）

浏览器模型设置支持以下供应商：

| 供应商类型 | 示例 |
|:--|:--|
| OpenAI Compatible | DeepSeek、DashScope、OpenRouter、Ollama、SiliconFlow |
| OpenAI Responses | OpenAI |
| Anthropic Messages | Claude |
| Coding Plan | Kimi、百炼、火山引擎 |

API Key 仅保存在浏览器 `localStorage` 中，不会写入磁盘或 SQLite。

<details>
<summary><b>⚙️ 环境变量配置（备选方案）</b></summary>

```bash
cp .env.example .env
```

```bash
KS_MODEL_PROVIDER=mock        # 默认，无需 Key
# KS_MODEL_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key
# OPENAI_MODEL=gpt-4.1-mini
```

也可以在浏览器"模型设置"中直接配置，无需编辑 .env。

</details>

<details>
<summary><b>🔗 默认供应商地址</b></summary>

| 供应商 | Base URL |
|:--|:--|
| Kimi Coding Plan | `https://api.kimi.com/coding/v1` |
| 百炼 Coding Plan | `https://coding.dashscope.aliyuncs.com/v1` |
| 火山引擎 Coding Plan | `https://ark.cn-beijing.volces.com/api/coding/v3` |
| DeepSeek | `https://api.deepseek.com/v1` |
| DashScope | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| OpenAI | `https://api.openai.com/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| Ollama | `http://127.0.0.1:11434/v1` |
| MiniMax | `https://api.minimax.io/v1` |
| SiliconFlow | `https://api.siliconflow.cn/v1` |

</details>

## 🔧 技术栈

| 层级 | 技术 |
|:--|:--|
| 前端 | React 19 + Vite |
| 后端 | FastAPI |
| 数据库 | SQLite（WAL 模式） |
| Agent 编排 | 自研状态机 |
| 模型接入 | Mock（默认）· OpenAI Compatible · Anthropic |

## 📡 API 简表

```text
POST   /api/runs                          创建新运行
GET    /api/runs/{run_id}                  获取运行状态和数据
GET    /api/runs/{run_id}/messages         获取讨论消息
GET    /api/runs/{run_id}/report           获取最终报告
POST   /api/runs/{run_id}/rerun            从头重跑
POST   /api/runs/{run_id}/resume           从失败位置继续
POST   /api/runs/{run_id}/cancel           停止运行
POST   /api/runs/{run_id}/references       提取或更新外部论据
POST   /api/memory/query                   记忆查询
GET    /api/history                        历史记录列表
POST   /api/history/delete                 删除历史记录
POST   /api/models/discover                从供应商发现模型
```

## 📜 许可证

[MIT](LICENSE) © 2026 apech
