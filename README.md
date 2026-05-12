<div align="center">

<img src="assets/k-storm-icon.svg" width="180" alt="K-Storm logo">

# K-Storm

**Local multi-agent research topic brainstorming**

Turn your research template + uploaded documents → structured briefing → controlled multi-agent discussion → Markdown topic selection report.

[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://github.com/ShakeYoung/K-Storm/blob/main/LICENSE)
[![Version](https://img.shields.io/badge/version-v1.6-green.svg?style=flat-square)](https://github.com/ShakeYoung/K-Storm)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

[English](./README.md) | [中文文档](./README.zh-CN.md)

</div>

---

## ⚡ Overview

K-Storm is a **fully local** research topic brainstorming MVP. Multiple AI agents (Novelty, Mechanism, Feasibility, Reviewer) hold a structured, multi-round discussion on your research question, then produce a ready-to-use Markdown report for thesis proposals or group meetings.

**Zero cloud dependency** — works out of the box with the built-in mock provider. Plug in any OpenAI-compatible or Anthropic API to unlock real agent reasoning.

## 🪄 Discussion Modes (V1.6)

| Mode | Agents | Rounds | Best For |
|:--|:--|:--|:--|
| **Full Deliberation** | 4 + Moderator | 1–5 | Comprehensive brainstorming → full IR + report |
| **Focused Panel** | Select 2–3 | 1–2 | Targeted deep-dive on specific questions |
| **Quick Probe** | 1 | 1 | Fast sanity check on one question |
| **Memory Query** | Select agents | 1–5 | Continue from a historical run's context |

## ✨ Core Capabilities

- 📋 **Structured template input** — research field, background, existing basis, constraints, goals
- 📎 **Document upload** with type tagging and per-document notes
- 🧠 **Intake Agent** digests everything into a dense briefing
- 🤖 **4 discussion agents** — Novelty · Mechanism · Feasibility · Reviewer
- 🎯 **Moderator** summarizes conflicts, omissions, and next-round questions
- 📊 **Structured IR** — candidate directions, evidence chains, critique points
- 📝 **Final Markdown report** — thesis-ready, with per-section copy buttons
- 📚 **External references** — agents cite papers/blogs/datasets; two-tier extraction; dedicated references page
- 🔄 **Run management** — stop, resume from failure, rerun from scratch
- 🗂️ **History** — search, filter, open past runs, delete
- 📤 **Export** — MD/PDF, JSON bundle, references export
- ⚙️ **Per-agent model assignment** — mix mock + OpenAI + Anthropic per agent slot

## 🏗️ Architecture

```text
Template + uploaded documents
  ↓
Intake Agent → dense briefing
  ↓
Round 1 (optional parallel)
  ↓
Moderator → conflict/omission summary
  ↓
Round 2+ (serial)
  ↓
Per-agent IR summary snippets
  ↓
Structured IR (compressed)
  ↓
Output Agent → final Markdown report
```

<details>
<summary><b>Project Structure</b></summary>

```text
backend/
  app/
    agents/              Agent definitions and registry
    model_providers/     Mock, OpenAI, Anthropic providers
    orchestrator/        Run execution state machine
    schemas/             Pydantic models
    storage/             SQLite database layer
    static/              Legacy standalone UI
    main.py              FastAPI app entry point
frontend/
  src/
    main.jsx             React application
    styles/
      app.css            Stylesheet
docs/
  ARCHITECTURE.zh-CN.md  Architecture documentation
  K-STORM-ROADMAP.zh-CN.md  Evolution roadmap
```

</details>

## 🚀 Quick Start

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+ (for the Vite frontend)

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Default uses **mock provider** — no API key needed.

### 2. Frontend (recommended)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** for the full V1.6 experience.

> The backend also serves a standalone UI at **http://localhost:8000** (legacy, no V1.6 features).

### 3. Configure Models (optional)

Browser-based model settings support:

| Provider Type | Examples |
|:--|:--|
| OpenAI Compatible | DeepSeek, DashScope, OpenRouter, Ollama, SiliconFlow |
| OpenAI Responses | OpenAI |
| Anthropic Messages | Claude |
| Coding Plan | Kimi, 百炼, 火山引擎 |

API keys stay in your browser's `localStorage` — never written to disk or SQLite.

<details>
<summary><b>Environment Variables (alternative)</b></summary>

```bash
cp .env.example .env
```

```bash
KS_MODEL_PROVIDER=mock        # default, no key needed
# KS_MODEL_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key
# OPENAI_MODEL=gpt-4.1-mini
```

</details>

## 🔧 Tech Stack

| Layer | Technology |
|:--|:--|
| Frontend | React 19 + Vite |
| Backend | FastAPI |
| Storage | SQLite (WAL) |
| Agent orchestration | Custom state machine |
| Model providers | Mock · OpenAI-compatible · Anthropic |

## 📡 API Overview

```text
POST   /api/runs                          Create a new run
GET    /api/runs/{run_id}                  Get run status and data
POST   /api/runs/{run_id}/resume          Resume a failed/canceled run
POST   /api/runs/{run_id}/cancel          Cancel a running run
POST   /api/runs/{run_id}/references      Extract or update external references
GET    /api/history                        List past runs
POST   /api/history/delete                 Delete selected runs
```

## 📜 License

[MIT](LICENSE) © 2026 apech
