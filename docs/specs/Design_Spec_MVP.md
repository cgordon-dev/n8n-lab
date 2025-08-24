# Design Spec — MVP: “Template → n8n” Agent (Local Docker)

## 1) Goal & Non‑Goals
**Goal (V1):** From a plain‑English request, pick the **best matching workflow template** from the local template corpus (your `n8n-workflows` repo), import it into a **self‑hosted n8n** via REST API, and optionally activate it. V1 **does not** synthesize brand‑new graphs; it performs **retrieve → confirm → import**.

**Non‑Goals (V1):**
- Credential/OAuth wiring
- Multi‑turn chat inside n8n
- Cloud deployment or n8n Cloud free tier (no public API)
- Arbitrary new workflow synthesis

---

## 2) Architecture (Local Containers)

### Services (3 containers)
1. **n8n** — Official image; REST API enabled; API key auth.
2. **Templates Service** — Tiny HTTP service that indexes your repo and exposes:
   - `GET /search?q=…` → returns top templates (id, name, path, simple metadata)
   - `GET /workflow/<id>` → returns raw workflow JSON
3. **Agent API** — LangGraph + FastAPI:
   - Endpoint `/chat` → NL prompt → pick template → import into n8n (optional activate)
   - Endpoint `/dryrun` → NL prompt → show top candidates without import

### Data Flow
User → **Agent `/chat`** → **Templates `/search`** → **Templates `/workflow/<id>`** → **n8n API create (+activate)** → Response `{ workflowId, editorUrl }`.

---

## 3) Minimal Containerization Plan

- **n8n**: official Docker image; expose `:5678`; mount a persistent volume; set `N8N_ENCRYPTION_KEY`. Create API key in the UI.
- **Templates Service**: Python (FastAPI/Flask). Mount your repo read‑only; build a quick on‑start index (filename, inferred integrations, node count).
- **Agent API**: Python (LangGraph + FastAPI). Environment: `N8N_API_URL`, `N8N_API_KEY`, `TEMPLATES_URL`.

---

## 4) Contracts & Behaviors

### Agent → Templates Service
- `GET /search?q=<text>` → `[{ id, name, path, score }]`
- `GET /workflow/<id>` → `workflow.json`

### Agent → n8n API
- Auth: header `X-N8N-API-KEY: <key>`
- Create workflow: `POST /.../workflows` (instance may use `/api/v1` or `/rest`); optional activation step after create.

### Happy Path
Input: “Set up a Webhook that posts JSON to Slack.”  
Agent detects integrations (`Webhook`, `Slack`), calls `/search`, selects top template, fetches JSON, creates workflow via n8n API, returns `{ workflowId, editorUrl }`.

### Errors & Recovery
- Missing/invalid API key → return actionable 401 error.
- Low confidence match → return top‑3 candidates and ask user to pick (or use `/dryrun` first).
- Templates requiring credentials → import **inactive**; return TODOs in the response.

---

## 5) Ranking (Simple, Robust)
- Extract terms from prompt: integrations, trigger type, operations (“append”, “notify”, “classify”).
- Score templates by:
  - Integration overlap (exact hits)
  - Trigger match (Webhook/Schedule/Chat)
  - Node count proximity (avoid huge graphs for simple asks)
- Optional: small text‑embedding similarity over template names/descriptions.

---

## 6) Security (Local‑Only, V1)
- Keep `N8N_API_KEY` in `.env` (never commit).
- No user secrets handled by the Agent; workflows that need credentials import **inactive** and are activated manually after creds are added in n8n.

---

## 7) Test Plan / Acceptance (Tech)

**Import smoke test**
- Prompt: “Create a webhook echo.”
- Result: a webhook‑based template imports, runs in n8n, and is visible in the editor.

**Ranking sanity**
- “Gmail → Slack alert” vs “Slack alert from Gmail” both select the same top template.

**Failure modes**
- No match → top‑3 list returned
- API down → retries with backoff, then structured error
- 401/403 → explicit message to set `N8N_API_KEY`

---

## 8) Risks & Mitigations
- **n8n API path drift** (`/api/v1` vs `/rest`) → probe both; configurable base path.
- **Template quality variance** → default to import **inactive** and surface a checklist (“Add Slack credential”, etc.).
- **Ranking quality** → keep a manual allowlist for “gold” templates until retrieval is tuned.

---

## 9) Implementation Outline (for Claude Code)

**Templates Service**
- Walk `workflows/` at boot; build in‑memory index (filename, inferred integrations by scanning node `type`s, node count).
- `/search`: keyword match + heuristic score → top N
- `/workflow/<id>`: stream file

**Agent API**
- LangGraph state: `{ query, candidates[], selected{id,name,path}, templateJson, created{ id, url }, error }`
- Steps: parse → search → select → fetch → create → (activate?) → respond
- n8n client: tries `/api/v1/workflows` then `/rest/workflows`; sets `X-N8N-API-KEY`

**Dev Ergonomics**
- Single `docker compose up` for all services
- `.env` for keys and service URLs
- README with curlable examples for `/dryrun` and `/chat`

---

## 10) V2 Notes (Not in MVP)
- n8n Chat UX (Chat Trigger + Respond to Chat with “Using Response Nodes”)
- Minimal parameterization prompts (ask for `sheetId`, webhook URL, etc.)
- New workflow synthesis when no template is close enough
