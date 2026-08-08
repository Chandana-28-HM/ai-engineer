# AI Engineer

An autonomous software-engineering assistant. Chat with an LLM, attach a repository
(by zip upload or `git clone`) that gets indexed into a vector database for semantic
code search, and hand complex goals to a LangGraph multi-agent team that plans, codes,
reviews, debugs, and documents — then writes a final report.

Built with a **FastAPI + PostgreSQL + Qdrant** backend and a **Next.js** dark-themed UI.

---

## Features

| Feature | Description |
|---|---|
| **Chat** | Streaming chat (`SSE`) with the configured LLM provider |
| **Code tasks** | `Code / Explain / Fix / Search repo` modes with tailored system prompts |
| **Repository awareness** | Upload a `.zip` or `git clone` a repo; browse structure, see language stats |
| **Semantic code search** | Code is chunked and embedded into **Qdrant**; ask questions and get ranked source snippets with citations |
| **Autonomous agent** | Single-agent mode with file + shell tools inside an isolated workspace |
| **Multi-agent team** | LangGraph state machine: **Planner → Coder → Reviewer → Debugger → Documenter**, looping until the reviewer approves |
| **Project / conversation history** | Conversations, messages and agent runs persisted in PostgreSQL |

---

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy 2 (async), asyncpg, Pydantic v2, LangChain, LangGraph, Qdrant
- **LLM providers:** Gemini (default), DeepSeek, OpenRouter, Ollama (local)
- **Embeddings:** Gemini embeddings, or a dependency-free local hashed n-gram fallback
- **Database:** PostgreSQL 18
- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, react-markdown + Prism

---

## Prerequisites

- Python 3.12+ (tested on 3.13)
- Node.js 20+ (tested on 24)
- PostgreSQL running locally (18+)
- Git
- (Optional) A [Gemini API key](https://aistudio.google.com/app/apikey) — needed for real LLM answers and Gemini embeddings. Without a key the app still runs: chat returns a provider error gracefully, repo search falls back to the local embedder.

---

## Setup

### 1. Create the database

```sql
CREATE USER ai_engineer WITH PASSWORD 'ai_engineer_dev';
CREATE DATABASE ai_engineer OWNER ai_engineer;
```

> The tables are created automatically on backend startup (`init_db`).

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt

# add your Gemini key (optional but recommended)
# edit .env → GEMINI_API_KEY=your_key

uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

- Interactive API docs: <http://127.0.0.1:8001/docs>
- Health check: <http://127.0.0.1:8001/api/health>

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. The frontend talks to the backend at `http://127.0.0.1:8001`
(default; override with the `NEXT_PUBLIC_API_URL` env var).

---

## How to use it

1. **Create a project** (sidebar → *New Project*).
2. **New Chat** — ask anything, or pick a task chip: `Code`, `Explain`, `Fix`, `Search repo`.
3. **Attach a repository** (header → *Repo*):
   - upload a `.zip`, or paste a git URL and *Clone*;
   - press *Index* to embed the code into Qdrant;
   - *Structure* shows a summary, language stats and file tree;
   - then use `Search repo` in chat, or the in-panel search box, to get ranked source results.
4. **Run the agent team** (header → *Agent*, or toggle *Agent mode* in the input box):
   - type a goal like *"Add a REST API endpoint with tests"*;
   - watch the pipeline: Planner → Coder → Reviewer → Debugger → Documenter with live tool logs;
   - a final report is written to `AGENT_REPORT.md` in the repo workspace when one is attached.

---

## Project structure

```
ai-engineer/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, router wiring, init_db
│   │   ├── config.py               # pydantic-settings (env config)
│   │   ├── database.py             # async engine / session
│   │   ├── models/models.py        # Project, Conversation, Message, Repository, CodeChunk, AgentRun, AgentStep
│   │   ├── schemas/                # Pydantic request/response models
│   │   ├── routers/                # projects, conversations, chat, repos, agent
│   │   └── services/
│   │       ├── chat_service.py     # intent detection + SSE streaming chat + RAG
│   │       ├── repo_service.py     # zip/git import, chunking, indexing, structure, search
│   │       ├── vector_store.py     # Qdrant (lazy singleton, local disk)
│   │       ├── llm/                # factory, embeddings (gemini/local), prompts
│   │       └── agent/              # tools, LangGraph graph, run persistence
│   ├── scripts/test_agent_offline.py
│   ├── requirements.txt
│   └── .env                        # provider + DB config
├── frontend/
│   ├── app/                        # layout, globals.css, page.tsx (thin composition)
│   ├── components/                 # Sidebar, Header, ChatArea, MessageBubble, InputBox, Markdown, RepoPanel, AgentPanel
│   ├── hooks/                      # useWorkspace, useChat, useAgentRun
│   └── lib/                        # api client (SSE), types
├── docs/                           # architecture + requirements
└── README.md
```

---

## Configuration

All backend settings live in `backend/app/config.py` and can be overridden via `backend/.env`:

| Env var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://ai_engineer:ai_engineer_dev@localhost:5432/ai_engineer` | Postgres DSN |
| `LLM_PROVIDER` | `gemini` | `gemini` \| `deepseek` \| `openrouter` \| `ollama` |
| `LLM_MODEL` | `gemini-2.5-flash` | Default chat model |
| `GEMINI_API_KEY` | *(empty)* | Required for real Gemini calls |
| `EMBEDDING_PROVIDER` | `gemini` | `gemini` \| `local` |
| `AGENT_MAX_ITERATIONS` | `12` | Agent tool-call limit |
| `AGENT_MAX_REVIEW_LOOPS` | `2` | Reviewer → debugger loop limit |

> Port note: the backend is served on **8001** because port 8000 is occupied by another local app.

---

## Scripts / tests

```bash
# Offline smoke test for the single + multi-agent graphs (no API key needed)
python backend/scripts/test_agent_offline.py

# Frontend type-check + production build
cd frontend && npm run build
```

---

## Roadmap

- [x] **Phase 1 — MVP chat:** streaming LLM chat, code tasks, projects/conversations
- [x] **Phase 2 — Repository awareness:** repo upload/clone, indexing, semantic search, RAG context
- [x] **Phase 3 — Autonomous agent:** single agent with file & shell tools in an isolated workspace
- [x] **Phase 4 — Multi-agent system:** LangGraph planner/coder/reviewer/debugger/documenter loop
- [ ] **Phase 5 — Future additions:** authentication, deployment, code-editor UI, test runner integration

See [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) for a detailed requirement-to-implementation
map, and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how it all fits together.

---

## License

[MIT](LICENSE)
