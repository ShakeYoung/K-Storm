# K-Storm

A local multi-agent research topic brainstorming tool. It turns your research background template and uploaded documents into a structured briefing, runs a controlled multi-agent discussion, and produces a Markdown topic selection report.

**Current version: V1.6** — includes four discussion modes, memory-based queries, and a redesigned research console UI.

中文说明见 [README.zh-CN.md](README.zh-CN.md).
架构文档见 [docs/ARCHITECTURE.zh-CN.md](docs/ARCHITECTURE.zh-CN.md).

## Features

### Discussion Modes (V1.6)

| Mode | Agents | Rounds | Use Case |
|:--|:--|:--|:--|
| **Full Deliberation** | 4 + Moderator | 1–5 | Comprehensive brainstorming with full IR and report |
| **Focused Panel** | Select 2–3 | 1–2 | Targeted deep-dive on specific questions |
| **Quick Probe** | 1 | 1 | Fast sanity check on a single question |
| **Memory Query** | Select agents | 1–5 | New discussion based on a historical run's context |

### Core Capabilities

- **Structured template input** — research field, background, existing basis, constraints, goals
- **Document upload** with type tagging (design / experiment-data) and per-document notes
- **Intake Agent** digests the full input into a dense briefing
- **4 discussion agents**: Novelty, Mechanism, Feasibility, Reviewer
- **Moderator** summarizes first-round conflicts and omissions
- **Structured IR** (Intermediate Representation) with candidate directions, evidence refs, and critique points
- **Final Markdown report** for thesis proposal or group meeting discussion
- **External references extraction** — agents cite papers, blogs, datasets; two-tier extraction (explicit section → regex fallback); dedicated references page with grouped display and export
- **Run management**: stop, resume from failure, rerun from scratch
- **History**: search, filter by status, open past runs, delete
- **Export**: unified MD/PDF selector on all download buttons, JSON bundle, external references export
- **Model settings**: per-agent model assignment, supports OpenAI-compatible, Anthropic, and local mock provider

### UI

- Three-column research console: dark left navigation, main stage, right intelligence rail
- Page-based navigation: Overview, New Discussion, Debate Floor, Report, References, History
- Round-by-round agent cards with identity-colored borders and markdown rendering
- Structured IR hidden from user view (included in export bundle only)

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for the Vite frontend)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The backend also serves a standalone UI at <http://localhost:8000>.

> The Vite frontend (port 5173) is the primary UI with full V1.6 features. The backend static UI (port 8000) is a legacy version.

### Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

The default `KS_MODEL_PROVIDER=mock` works without any API key. To use OpenAI:

```bash
KS_MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4.1-mini
```

API keys can also be configured in the browser-based model settings without touching `.env`.

## Tech Stack

| Layer | Technology |
|:--|:--|
| Frontend | React + Vite |
| Backend | FastAPI |
| Storage | SQLite |
| Agent orchestration | Local state machine |
| Model providers | Mock (default), OpenAI-compatible, Anthropic |

## API Overview

```text
POST   /api/runs                          Create a new run
GET    /api/runs/{run_id}                  Get run status and data
POST   /api/runs/{run_id}/resume          Resume a failed/canceled run
POST   /api/runs/{run_id}/cancel          Cancel a running run
POST   /api/runs/{run_id}/references      Extract or update external references
GET    /api/history                        List past runs
POST   /api/history/delete                 Delete selected runs
```

## Project Structure

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
    main.jsx             React application (single file)
    styles/
      app.css            Stylesheet
docs/
  ARCHITECTURE.zh-CN.md  Architecture documentation
  K-STORM-ROADMAP.zh-CN.md  Evolution roadmap
  V1_6-DISCUSSION-MODES.zh-CN.md  V1.6 discussion modes spec
```

## License

MIT. See [LICENSE](LICENSE).
