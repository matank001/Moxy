# OblivionSec Upgrade Design

**Date:** 2026-05-04  
**Status:** Approved  
**Approach:** Option B — Provider Abstraction + Modular Tools

---

## Overview

Upgrade Moxy (now **OblivionSec**) from an OpenAI/Ollama-only DAST proxy tool into a full-featured security platform with:

1. Full rebranding from Moxy → OblivionSec
2. Multi-provider AI (Anthropic + OpenAI + Ollama) with native tool use
3. Four new security tools callable by the AI agent (PoC gen, active scan, static analysis, network mapping)
4. Frontend model/provider selector in Agent tab + new Scanner tab + right-click context menu on requests

---

## Section 1: Rebranding (Moxy → OblivionSec)

Every occurrence of "Moxy" / "moxy" is renamed to "OblivionSec" / "oblivionsec".

| Location | Current | New |
|---|---|---|
| Database filename | `projects_data/moxy.db` | `projects_data/oblivionsec.db` |
| Python entry point | `moxy = "main:main"` in `pyproject.toml` | `oblivionsec = "main:main"` |
| npm script | `npm run moxy` | `npm run oblivionsec` |
| UI header text | `moxy` | `OblivionSec` |
| Page `<title>` | Moxy | OblivionSec |
| README title/body | Moxy | OblivionSec |
| Docker labels/comments | Moxy | OblivionSec |
| `db.py` hardcoded path | `projects_data/moxy.db` | `projects_data/oblivionsec.db` |

**Migration:** On startup, `db.py` checks for `projects_data/moxy.db`; if found and `oblivionsec.db` does not exist, it renames the file automatically to preserve existing data.

---

## Section 2: Provider Abstraction Layer

### New directory: `backend/src/providers/`

```
backend/src/providers/
├── __init__.py
├── base.py          # Abstract base class
├── anthropic.py     # Anthropic SDK integration
├── openai.py        # OpenAI SDK (wraps existing logic)
└── ollama.py        # Ollama via OpenAI-compatible endpoint
```

### `base.py` interface

```python
class BaseProvider(ABC):
    def chat(self, messages: list, tools: list, model: str) -> tuple[str, list]:
        # Returns (response_text, tool_calls[])

    def list_models(self) -> list[str]:
        # Returns available model IDs for selector

    def supports_tool_use(self) -> bool:
        # Anthropic: True, OpenAI: True, Ollama: False
```

### Provider details

**Anthropic (`anthropic.py`):**
- Uses `anthropic` Python SDK
- Default model: `claude-sonnet-4-6`
- Available models: `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`
- Native tool use via `tools=` parameter
- Prompt caching on system message (`cache_control: {"type": "ephemeral"}`)

**OpenAI (`openai.py`):**
- Wraps existing `openai` SDK usage from `agent.py`
- Tool use via `functions`/`tools` parameter (already working)
- Model list fetched from OpenAI API

**Ollama (`ollama.py`):**
- Uses OpenAI-compatible endpoint (`/v1/chat/completions`)
- `supports_tool_use()` returns `False`
- Agent falls back to text-only mode, asks AI to describe actions in structured text
- Model list fetched from Ollama `/api/tags`

### New API endpoint

`GET /api/agent/models?provider=anthropic|openai|ollama`  
Returns `{ models: ["claude-sonnet-4-6", ...] }` for the provider selector dropdown.

### Database changes

`agent_chats` table: add columns `provider` (text, default `openai`) and `model` (text, default `gpt-4o-mini`).

---

## Section 3: Security Tools as AI-Callable Tools

### New directory: `backend/src/tools/`

```
backend/src/tools/
├── __init__.py
├── poc_generator.py      # Generate exploit PoCs
├── active_scanner.py     # Dynamic fuzzing/scanning
├── static_analyzer.py    # JS/HTML/header static analysis
└── network_analyzer.py   # Host/connection mapping
```

### Tool definitions

#### `generate_poc`
- **Input:** `request_id: int`, `vuln_type: str` (xss | sqli | ssrf | lfi | rce | idor)
- **Output:** `{ poc_payload: str, curl_command: str, description: str, severity: str }`
- **Behavior:** Fetches the raw request from DB, passes it with the vuln_type to the AI provider to generate a contextual PoC. Result saved to `findings` table.

#### `active_scan`
- **Input:** `request_id: int`, `parameter: str`, `payloads: list[str]`, `threads: int` (default 1)
- **Output:** `{ findings: [{ payload: str, response_diff: str, severity: str, status_code: int }] }`
- **Behavior:** Sends parameter-mutated copies of the request via `http_sender.py`. Compares response status, length, and body for anomalies. Bounded to target host already in the project.

#### `static_analyze`
- **Input:** `request_id: int` or `url: str`, `scope: str` (js | headers | body | all)
- **Output:** `{ findings: [{ type: str, location: str, value: str, severity: str }] }`
- **Patterns detected:**
  - Hardcoded secrets (API keys, tokens, passwords in JS/body)
  - Dangerous JS sinks (`eval`, `document.write`, `innerHTML`, `location.href`)
  - Missing security headers (`Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`)
  - Exposed sensitive paths (`.env`, `.git`, `wp-config`, `phpinfo`)
  - JWT tokens in response bodies/headers

#### `network_map`
- **Input:** `project_id: int`, `filters: dict` (optional host/method/status filters)
- **Output:** `{ hosts: [str], connections: [{ from, to, count }], timeline: [{ timestamp, host, method, status }] }`
- **Behavior:** Queries the project requests DB, aggregates unique hosts and their relationships (redirects, API calls), and returns structured data for visualization.

### New DB table: `findings`

```sql
CREATE TABLE findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER,
    tool TEXT,           -- generate_poc | active_scan | static_analyze | network_map
    vuln_type TEXT,
    severity TEXT,       -- critical | high | medium | low | info
    title TEXT,
    description TEXT,
    evidence TEXT,       -- raw payload/value that triggered finding
    remediation TEXT,
    timestamp TEXT,
    FOREIGN KEY (request_id) REFERENCES requests(id)
);
```

---

## Section 4: Frontend UI Changes

### Agent Tab — Provider/Model selector

Added at the top of the Agent tab:

```
┌──────────────────────────────────────────────────────┐
│ Provider: [Anthropic ▾]   Model: [claude-sonnet-4-6 ▾] │
├──────────────────────────────────────────────────────┤
│ Chat messages...                                     │
│                                                      │
│  ┌─ Tool: generate_poc ───────────────────────────┐  │
│  │ ✓ XSS PoC generated for param "q"             │  │
│  │ [Show details ▾]                               │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
├──────────────────────────────────────────────────────┤
│ [message input]                           [Send]     │
└──────────────────────────────────────────────────────┘
```

- Provider dropdown: `Anthropic | OpenAI | Ollama`
- Model dropdown: populated from `/api/agent/models?provider=<selected>`
- Both saved per-chat (stored in DB, restored on chat load)
- Tool call results rendered inline, collapsible
- Severity badges: colored pills for `Critical` / `High` / `Medium` / `Low` / `Info`
- Ollama: tool-calling UI hidden (text-only mode indicator shown)

### New Tab: Scanner

Position: between Resender and Agent tabs.

Aggregated findings view for the current project:

- Table columns: Severity | Type | Host | Parameter | Description | Request | Timestamp
- Filter by severity, type, host
- Click row → opens request in Resender or HttpViewer
- Findings sourced from `findings` DB table, polled via `/api/projects/<id>/findings`

### Home Tab — Right-click context menu on requests

Right-click any request in the request list to get:

- **Analyze with AI** — opens Agent tab, pre-fills "Analyze this request: #<id>"
- **Generate PoC** — opens Agent tab, pre-fills "Generate a PoC for request #<id>"  
- **Active Scan** — opens Agent tab, pre-fills "Run an active scan on request #<id>"

---

## Architecture Diagram

```
Frontend (React)
  ├── AgentTab (provider/model selector + chat)
  ├── ScannerTab (findings aggregation)
  └── HomeTab (right-click context menu)
        │
        ▼
Backend (Flask)
  ├── api/agent.py (orchestration — updated)
  ├── api/findings.py (new — CRUD for findings)
  ├── providers/
  │   ├── anthropic.py
  │   ├── openai.py
  │   └── ollama.py
  └── tools/
      ├── poc_generator.py
      ├── active_scanner.py
      ├── static_analyzer.py
      └── network_analyzer.py
        │
        ▼
SQLite (per-project DB)
  ├── requests
  ├── findings (new)
  ├── agent_chats (+ provider, model columns)
  └── agent_messages
```

---

## Out of Scope

- Browser automation tool: unchanged
- MITMproxy addon: unchanged
- Authentication/multi-user: not in this iteration
- Remote/cloud scanning: not in this iteration
