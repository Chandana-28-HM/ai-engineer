# Architecture

## Overview

```
┌───────────────┐    SSE / JSON     ┌──────────────────────────┐
│  Next.js UI   │ ───────────────► │        FastAPI           │
│  (React 19)   │ ◄─────────────── │        (port 8001)       │
└───────────────┘                  └───────────┬──────────────┘
                                               │
              ┌────────────────┬───────────────┼──────────────────┐
              │                │               │                  │
       ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼─────┐   ┌───────▼────────┐
       │ PostgreSQL  │  │   Qdrant    │  │  Workspace│   │  LLM providers │
       │ (metadata,  │  │ (code chunks│  │  (local   │   │ Gemini /       │
       │  messages,  │  │  embeddings)│  │  repo files)│  │ DeepSeek /     │
       │  runs)      │  │             │  │           │   │ OpenRouter /    │
       └─────────────┘  └─────────────┘  └───────────┘   │ Ollama         │
                                                         └────────────────┘
```

The frontend never talks to the database or vector store directly. Every interaction goes
through the REST/SSE API on `:8001`.

---

## Backend

### Request flow (chat)

```
POST /api/chat (or /api/code/task)
   │  body: { conversation_id?, project_id?, repo_id?, message, task_type? }
   ▼
chat_service.stream_chat()
   1. ensure_conversation()      → creates/reuses a Conversation row
   2. save_message(user)          → persists the user turn
   3. detect_intent()             → chat | generate | explain | fix | search
      ├─ "search" + attached repo → repo_service.search_repo() (RAG)
      │                              → yields `sources` + a prebuilt answer, or
      │                                switches to the CODE_SEARCH prompt
      └─ else                     → attach repo structure summary as context
   4. stream LLM tokens           → yields `token` events
   5. save_message(assistant)     → persists the reply (with sources JSON)
   6. yields `done`
```

All responses are **Server-Sent Events**. Each chunk is:

```
event: <name>
data: <json>

```

| Event | Payload | Meaning |
|---|---|---|
| `intent` | `{ intent, conversation_id }` | Detected task type; backend-created conversation id (use this for subsequent turns) |
| `sources` | `{ sources: [{file_path, line, score, snippet}] }` | RAG hits used to answer a search |
| `token` | `{ text }` | Streamed LLM token |
| `done` | `{ message_id }` | Assistant message persisted |
| `error` | `{ message }` | Streaming error (still persisted) |

### Agent run flow

```
POST /api/agent/run → run_service.create_run() → 202
   → StreamingResponse consumes asyncio.Queue fed by run_service.execute_run()
   → LangGraph graph (single agent or multi-agent) drives tools in a workspace
   → each step persisted (AgentRun / AgentStep rows) + streamed as events
```

| Event | Payload | Meaning |
|---|---|---|
| `run_start` | `{ run_id }` | Run created |
| `step` | `{ agent, title, status, plan?, files?, output?, approved?, comments? }` | Step progress/result (same step can be updated as it transitions) |
| `agent_tool` | `{ kind, command?/path? }` | Agent invoked a tool (echo for the live log) |
| `agent_token` | `{ text }` | Streamed reasoning tokens |
| `run_done` | `{ summary }` | Finished; final report text |
| `run_error` | `{ message }` | Failed / timed out (300s) |

### Data model (PostgreSQL)

| Table | Purpose |
|---|---|
| `projects` | Top-level container |
| `conversations` | Chat sessions scoped to a project |
| `messages` | User/assistant turns (`sources` column holds JSON of RAG hits) |
| `repositories` | Uploaded/cloned repos; `status` ∈ `pending \| indexing \| indexed \| failed` |
| `code_chunks` | Chunk → repo mapping (payloads live in Qdrant) |
| `agent_runs` | One per goal; stores `status`, `summary`, `error` |
| `agent_steps` | Per-agent step inside a run; stores tool results and files changed |

### RAG pipeline (`repo_service`)

1. **Import** — unzip a `.zip` or `git clone --depth 1` into `backend/storage/workspaces/{project_id}/{repo_id}`.
2. **Chunk** — walk the tree, skip binaries and `node_modules`/`.git`/venv etc., split files into ~500-token chunks (LangChain `RecursiveCharacterTextSplitter`).
3. **Embed** — Gemini embeddings, or the dependency-free `LocalEmbedder` (deterministic hashed n-grams via `zlib.crc32`).
4. **Index** — upsert into Qdrant collection `code_chunks` (dimension 768, cosine).
5. **Search** — `query_points` → ranked `(file_path, line, snippet, score)`; an optional `answer=True` step uses the LLM to synthesize an answer over the top-k snippets.

> Qdrant runs in **local-disk mode** (`backend/storage/qdrant`) and is reached through the
> `LazyVectorStore` singleton — Qdrant locks its storage folder per process, so a fresh
> client must not be created per-request.

### Agent graph (LangGraph)

- **Single agent** — one ReAct agent with the file/shell toolset and the goal as its system prompt.
- **Multi-agent** — a `StateGraph`:

```
   Planner ──► Coder ──► Reviewer ──►{ approved? }
                                      │   yes
                                      ▼
                                 Documenter
                                      │
                                      ▼
                                      │   no (and loops left)
                                      ▼
                                  Debugger ──► Coder
```

The `debugger` node analyzes reviewer comments and produces fix instructions, then the
`coder` re-implements; the loop is bounded by `agent_max_review_loops` (default 2).

**Tools** (`services/agent/tools.py`): `list_dir`, `read_file`, `create_file`, `edit_file`,
`run_command`. Paths are constrained to the repo workspace; commands are run with a timeout
and a blocklist of destructive/network commands.

### Storage layout

```
backend/storage/
├── qdrant/                 # vector DB files (local mode)
└── workspaces/
    └── {project_id}/
        └── {repo_id}/      # checked-out repo the agent edits in place
```

---

## Frontend

- **State layer** — three focused hooks instead of a monolithic page:
  - `hooks/useWorkspace.ts` — projects, conversations, repositories (fetch + CRUD)
  - `hooks/useChat.ts` — SSE chat streaming into a placeholder bubble, history loading, auto conversation creation
  - `hooks/useAgentRun.ts` — agent SSE streaming, step upsert, live tool log
- **Presentation layer** — `app/page.tsx` is a thin composition of presentational components:
  `Sidebar`, `Header`, `ChatArea`/`MessageBubble`, `InputBox`, `Markdown`, `RepoPanel`, `AgentPanel`.
- **API client** — `lib/api.ts`: typed `api<T>()` helper plus `streamSSE()` which parses
  the `event:/data:` frames from FastAPI. `API_BASE` defaults to `http://127.0.0.1:8001`
  (override with `NEXT_PUBLIC_API_URL`).
- **Rendering** — assistant replies render through `react-markdown` + `remark-gfm` with
  Prism syntax highlighting (oneDark). RAG `sources` render as clickable file chips.

---

## Configuration surfaces

| Where | What |
|---|---|
| `backend/.env` | DB DSN, LLM provider/model/keys, embedding provider, agent limits |
| `backend/app/config.py` | Every setting + its default (pydantic-settings) |
| `frontend` `NEXT_PUBLIC_API_URL` | Backend base URL for the browser |
