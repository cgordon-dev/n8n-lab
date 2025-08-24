# PRD — MVP “Template → n8n” Agent

## 1) Vision
Enable a non‑expert to describe an automation in plain English and get a **ready‑to‑review** workflow created in a local n8n instance by reusing a curated template corpus.

## 2) Users
- **Builder (you/power user):** validates the agent locally and curates templates.
- **Analyst/PM:** describes desired automation in one sentence and receives a draft workflow to review in n8n.

## 3) Assumptions
- Self‑hosted n8n is available locally via Docker and exposes its REST API with an API key.
- Templates exist as valid n8n workflow JSON files (import/export compatible).
- Local‑only development; no cloud dependencies required in V1.

## 4) Success Metrics
- **P0:** ≥ 80% of test prompts import a sensible workflow on the first try.
- **P0:** Median time from `/chat` request to workflow visible in n8n editor ≤ 5 seconds on a typical laptop.
- **P0:** 100% of auth failures return a clear, actionable error (no silent failures).

## 5) Scope

### In‑Scope (V1)
- `/chat` endpoint: free‑text → best template → import (optional activate)
- `/dryrun` endpoint: free‑text → top‑3 candidates (no import)
- Local Docker Compose for three services (n8n, Templates Service, Agent API)

### Out‑of‑Scope (V1)
- Credential/OAuth flows and secret injection
- New graph synthesis
- n8n Chat Trigger UX (planned V2)

## 6) Functional Requirements
- **F1** `/chat` accepts `{ message: string, activate?: boolean }` and returns `{ workflowId, editorUrl }` on success.
- **F2** The Agent calls Templates Service `/search` and `/workflow/<id>` to select and fetch a template JSON.
- **F3** The Agent creates the workflow via n8n REST API using `X-N8N-API-KEY`.
- **F4** If `activate=true`, the Agent attempts to activate the workflow; on failure, returns inactive with reason.
- **F5** `/dryrun` returns top‑3 candidates: `[ { id, name, score } ]`.
- **F6** Structured errors for: missing API key, no matches, n8n API unavailable.

## 7) Non‑Functional Requirements
- **N1** One‑command startup: `docker compose up` to run all services.
- **N2** Deterministic, explainable ranking (keywords + simple heuristics).
- **N3** Logs and metrics: request ids, timing for search/import, n8n API response codes.

## 8) User Flow (Happy Path)
1. User POSTs `/chat` with a natural‑language request.
2. Agent parses intent, queries Templates `/search`, chooses top candidate.
3. Agent fetches JSON (`/workflow/<id>`), creates workflow via n8n REST API.
4. Agent returns `{ workflowId, editorUrl }` (and `active: true/false`).

## 9) Milestones
- **M1** Compose up: n8n reachable; API key configured; health endpoints OK.
- **M2** Templates Service indexes repo and serves `/search` + `/workflow/<id>`.
- **M3** Agent imports “webhook echo” template and returns a valid editor URL.
- **M4** Add `/dryrun` and basic ranking weights.
- **M5** Add retry/backoff and structured error responses; write TROUBLESHOOTING.

## 10) Acceptance Criteria
- Running `docker compose up` starts `n8n`, `templates`, and `agent` successfully.
- A request like “Slack alert on new Gmail” yields a created workflow visible in n8n (inactive by default).
- Without `N8N_API_KEY`, `/chat` returns 401/403 with a clear message; with a valid key, imports succeed.

## 11) Risks & Mitigations
- **API Path Differences** (`/api/v1` vs `/rest`): probe both and allow override via env.
- **Template Drift/Quality**: import inactive by default; surface TODOs for credentials and manual checks.
- **Ranking Misses**: provide `/dryrun` preview and allow manual template selection.

## 12) V2 Considerations
- n8n Chat Trigger + Respond to Chat (Response Mode: Using Response Nodes)
- Minimal parameter prompts (e.g., `sheetId`, webhook URL) with validation
- On‑the‑fly workflow synthesis when no template is sufficiently close
