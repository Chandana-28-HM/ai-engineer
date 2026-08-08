# Requirements → Implementation

This document maps the product requirements (phase by phase) to what was actually built,
so you can verify the AI matches your specification before pushing.

Legend: ✅ done · 🔶 partially (needs an API key / external service) · ⬜ not started

---

## Phase 1 — MVP: chat with an LLM ✅

| # | Requirement | Status | Where | How to verify |
|---|---|---|---|---|
| 1.1 | User can chat with an LLM | ✅ | `backend/app/services/chat_service.py`, `frontend/hooks/useChat.ts` | Open a chat, type a message, watch tokens stream in |
| 1.2 | Streaming responses (not a spinner + full block) | ✅ | SSE: `token` events → `streamSSE` | Watch text appear token-by-token |
| 1.3 | Common code tasks: generate / explain / fix | ✅ | `/api/code/task`, `prompts.py` (`GENERATE/EXPLAIN/FIX`) | Use the Code / Explain / Fix chips |
| 1.4 | Automatic intent detection from a plain message | ✅ | `detect_intent()` in `chat_service.py` | Type *"explain what does this do"* → intent event = `explain` |
| 1.5 | Persist projects and conversations | ✅ | `models/models.py`, `routers/projects.py`, `routers/conversations.py` | Create a project + chat; refresh the page — history remains |
| 1.6 | Chat history loaded when reopening a conversation | ✅ | `/api/conversations/{id}/messages`, `useChat.openConversation` | Open a past chat → prior messages reappear |
| 1.7 | Provider-agnostic LLM layer | 🔶 | `services/llm/factory.py` | Switch `LLM_PROVIDER` in `.env`; needs the provider's key |
| 1.8 | Works even without a paid API key (local fallback) | 🔶 | `LLM_PROVIDER=ollama`; graceful SSE `error` event | With no key, chat surfaces a clear error instead of crashing |

---

## Phase 2 — Repository awareness (RAG) ✅

| # | Requirement | Status | Where | How to verify |
|---|---|---|---|---|
| 2.1 | Attach a repository by **uploading a zip** | ✅ | `repo_service.create_repo_from_upload`, `/api/repos/upload` | Repo panel → upload a `.zip` |
| 2.2 | Attach a repository by **git clone** | ✅ | `create_repo_from_git`, `/api/repos/git` | Paste `https://github.com/…` → Clone |
| 2.3 | Store repo metadata + file inventory | ✅ | `repositories` table, `code_chunks` table | Repo shows file count + chunk count |
| 2.4 | **Index** code into a vector store | ✅ | `repo_service.index_repo` + Qdrant `code_chunks` | Press Index; status → `indexed` |
| 2.5 | Semantic **code search** with ranked results + citations | ✅ | `repo_service.search_repo`, `SearchResponse` | Ask *"where is the express server defined"* → source chips with scores |
| 2.6 | Search answers synthesized by the LLM over top-k snippets | 🔶 | `search_repo(..., answer=True)` | Same as 2.5 with a `GEMINI_API_KEY` set |
| 2.7 | Repo **structure summary** (overview, language stats, dependency files, tree) | ✅ | `get_structure`, `RepoStructure` | Repo panel → Structure |
| 2.8 | Works when the model has **no key** (local embeddings fallback) | ✅ | `LocalEmbedder` in `services/llm/embeddings.py` | Set `EMBEDDING_PROVIDER=local` or leave key empty → search still returns hits |
| 2.9 | RAG context attached to normal chat when a repo is connected | ✅ | `prompts.repo_context(...)` in `chat_service` | Attach a repo, ask a question — answers reflect the repo structure |

---

## Phase 3 — Autonomous agent ✅

| # | Requirement | Status | Where | How to verify |
|---|---|---|---|---|
| 3.1 | A single agent that can act on a goal | ✅ | `graph.make_single_agent`, `services/agent/tools.py` | Agent panel → Single agent → run a goal |
| 3.2 | File tools: list dir, read file, create file, edit file | ✅ | `services/agent/tools.py` | Goal: *"create a file utils.py with a helper"* → file appears in workspace |
| 3.3 | Shell tool with timeout + dangerous-command blocklist | ✅ | `run_command` (via `app/utils/shell.py`) | Watch tool log; `rm -rf` / network commands are refused |
| 3.4 | Agent works inside an **isolated workspace** scoped to the repo | ✅ | `tools.py` path-safety checks + `workspaces/{project}/{repo}` | Agent cannot escape its repo folder |
| 3.5 | Agent can edit an attached repository | ✅ | workspace = attached repo checkout | Attach repo, run goal, diff the files afterwards |
| 3.6 | Agent results persisted | ✅ | `agent_runs` / `agent_steps`, `routers/agent.py` | `GET /api/agent/runs?project_id=…` returns history |
| 3.7 | Offline testable without a model key | ✅ | `scripts/test_agent_offline.py` | `python backend/scripts/test_agent_offline.py` |

---

## Phase 4 — Multi-agent system ✅

| # | Requirement | Status | Where | How to verify |
|---|---|---|---|---|
| 4.1 | A **planner** that breaks a goal into tasks | ✅ | `graph.build_multi_agent` → planner node | Run a multi-agent goal; watch the Plan steps |
| 4.2 | A **coder** that implements the tasks | ✅ | coder node | Files appear in the workspace |
| 4.3 | A **reviewer** that checks the code | ✅ | reviewer node (with `comments` on failure) | See reviewer step + comments |
| 4.4 | A **debugger** that turns reviewer feedback into fixes | ✅ | debugger node | Reviewer rejects → debugger produces fix instructions → coder loops |
| 4.5 | A **documenter** that writes the final report | ✅ | documenter node → `AGENT_REPORT.md` + `summary` | Final report shown in UI + written to the repo workspace |
| 4.6 | Review→fix loop bounded so it cannot run forever | ✅ | `agent_max_review_loops` (default 2) | Run a bad-goal scenario; loop exits and reports |
| 4.7 | Live visibility into each stage | ✅ | `step` / `agent_tool` / `agent_token` SSE events | Agent panel pipeline + tool log update live |
| 4.8 | `multi` vs `single` agent switch | ✅ | `AgentRunRequest.kind`, UI toggle | Toggle in the Agent panel |

---

## Phase 5 — Future additions ⬜

- Authentication / multi-user
- Deployment (Docker, cloud hosting)
- In-browser code editor + diff preview of agent changes
- Unit-test runner integration (agent executes the project's test suite)
- Conversation-level RAG memory / long-term vector memory

---

## Acceptance summary

```text
Phase 1  MVP chat + persistence          ✅  done
Phase 2  Repository awareness + RAG      ✅  done
Phase 3  Autonomous agent                ✅  done
Phase 4  Multi-agent team                ✅  done
Phase 5  Future                           ⬜  next
```

> The only two 🔶 items (real LLM answers + Gemini embeddings) are configuration, not
> code — they become ✅ the moment a `GEMINI_API_KEY` is added to `backend/.env`.
