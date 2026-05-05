# OblivionSec Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebrand Moxy → OblivionSec, add multi-provider AI (Anthropic/OpenAI/Ollama) with tool use, add four security tools (PoC gen, active scan, static analysis, network map), and add Scanner tab + provider selector to the frontend.

**Architecture:** Provider abstraction layer (`backend/src/providers/`) wraps all three AI providers behind a unified `chat(system, messages, tools, model)` interface. Security tools live in `backend/src/tools/` and are registered as callable tools in the agent loop. The agent loop in `api/agent.py` stays provider-agnostic by using OpenAI-compatible normalized message format, which each provider converts internally.

**Tech Stack:** Python/Flask backend, `anthropic` SDK (new), `openai` SDK (existing), React/TypeScript frontend, shadcn/ui, SQLite per-project databases.

---

## File Map

### New files
- `backend/src/providers/__init__.py`
- `backend/src/providers/base.py` — abstract provider interface
- `backend/src/providers/anthropic_provider.py` — Anthropic SDK wrapper
- `backend/src/providers/openai_provider.py` — OpenAI SDK wrapper
- `backend/src/providers/ollama_provider.py` — Ollama via OpenAI-compat endpoint
- `backend/src/tools/__init__.py`
- `backend/src/tools/poc_generator.py` — generate exploit PoCs via AI
- `backend/src/tools/active_scanner.py` — dynamic parameter fuzzing
- `backend/src/tools/static_analyzer.py` — regex-based JS/header/body analysis
- `backend/src/tools/network_analyzer.py` — host/timeline mapping from requests DB
- `backend/src/api/findings.py` — REST CRUD for findings table
- `frontend/src/components/tabs/ScannerTab.tsx` — findings table UI

### Modified files
- `backend/pyproject.toml` — add `anthropic` dep, rename entry point
- `backend/src/db.py` — rename DB path, add findings table + migration, add findings/chat functions
- `backend/src/api/__init__.py` — register findings blueprint
- `backend/src/api/agent.py` — use provider abstraction, add security tools, add /models endpoint
- `backend/main.py` — register findings blueprint, update startup prints
- `frontend/package.json` — rename `moxy` script
- `frontend/index.html` — rename title/meta
- `frontend/src/components/AppTabs.tsx` — rename logo, add Scanner tab, add agent navigation callback
- `frontend/src/components/tabs/AgentTab.tsx` — add provider/model selector
- `frontend/src/lib/api.ts` — add models, findings, update chatWithAgent
- `frontend/src/components/RequestList.tsx` — add right-click context menu
- `README.md` — rename all Moxy references

---

## Task 1: Rebrand Moxy → OblivionSec

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/src/db.py:16`
- Modify: `frontend/package.json`
- Modify: `frontend/index.html`
- Modify: `frontend/src/components/AppTabs.tsx:47`
- Modify: `README.md`

- [ ] **Step 1.1: Rename pyproject.toml entry point**

Edit `backend/pyproject.toml`:
```toml
[project]
name = "oblivionsec"
version = "1.0.2"
description = "OblivionSec - Next-Gen DAST Tool"
requires-python = ">=3.11"
dependencies = [
    "flask>=3.0.0",
    "flask-cors>=4.0.0",
    "mitmproxy",
    "browser-use",
    "openai-agents",
    "anthropic>=0.40.0"
]

[project.scripts]
oblivionsec = "main:main"

[tool.uv]
package = true

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]
include = ["main.py"]
```

- [ ] **Step 1.2: Rename DB path and add migration in db.py**

In `backend/src/db.py`, replace lines 16 and the `list_available_databases` exclusion and add migration:

Old (line 16):
```python
MAIN_DATABASE_PATH = os.path.join(PROJECTS_DB_DIR, 'moxy.db')
```

New:
```python
MAIN_DATABASE_PATH = os.path.join(PROJECTS_DB_DIR, 'oblivionsec.db')


def _migrate_moxy_db():
    """Rename moxy.db to oblivionsec.db on first run if it exists."""
    old_path = os.path.join(PROJECTS_DB_DIR, 'moxy.db')
    if os.path.exists(old_path) and not os.path.exists(MAIN_DATABASE_PATH):
        os.rename(old_path, MAIN_DATABASE_PATH)
        print("📦 Migrated moxy.db → oblivionsec.db")


_migrate_moxy_db()
```

Also update `list_available_databases` to exclude `oblivionsec.db` instead of `moxy.db`:

Old (line 57):
```python
        if filename.endswith('.db') and filename != 'moxy.db':
```

New:
```python
        if filename.endswith('.db') and filename != 'oblivionsec.db':
```

- [ ] **Step 1.3: Rename npm script in package.json**

In `frontend/package.json`, replace:
```json
    "moxy": "vite",
```
With:
```json
    "oblivionsec": "vite",
```

- [ ] **Step 1.4: Rename page title in index.html**

Replace all occurrences of `Moxy` in `frontend/index.html`:
```html
    <title>OblivionSec</title>
    <meta name="description" content="OblivionSec" />
    <meta name="author" content="OblivionSec" />
    <meta property="og:title" content="OblivionSec" />
    <meta property="og:description" content="OblivionSec - Next-Gen DAST Tool" />
    <meta name="twitter:site" content="@OblivionSec" />
```

- [ ] **Step 1.5: Rename logo text in AppTabs.tsx**

In `frontend/src/components/AppTabs.tsx`, line 47, replace:
```tsx
            <span className="font-logo text-2xl font-bold text-primary tracking-tight">
              moxy
            </span>
```
With:
```tsx
            <span className="font-logo text-2xl font-bold text-primary tracking-tight">
              OblivionSec
            </span>
```

- [ ] **Step 1.6: Update README.md**

Replace all instances of `Moxy` / `moxy` in README.md with `OblivionSec` / `oblivionsec`. Key replacements:
- `# Moxy` → `# OblivionSec`
- `Moxy (Next-Gen Man in the middle proxy)` → `OblivionSec (Next-Gen Man in the Middle Proxy)`
- `npm run moxy` → `npm run oblivionsec`
- `uv run moxy` → `uv run oblivionsec`
- `moxy.db` → `oblivionsec.db`

- [ ] **Step 1.7: Commit**

```bash
git add backend/pyproject.toml backend/src/db.py frontend/package.json frontend/index.html frontend/src/components/AppTabs.tsx README.md
git commit -m "rebrand: rename Moxy to OblivionSec across all files"
```

---

## Task 2: DB Schema — findings table + agent_chats columns

**Files:**
- Modify: `backend/src/db.py`

- [ ] **Step 2.1: Add findings table to `init_project_db`**

In `backend/src/db.py`, inside the `init_project_db` function, after the `agent_messages` table creation (around line 296), add:

```python
        # Create findings table for security scan results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                tool TEXT NOT NULL,
                vuln_type TEXT,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                evidence TEXT,
                remediation TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES requests(id)
            )
        ''')
```

- [ ] **Step 2.2: Add provider/model columns to agent_chats**

Inside `init_project_db`, replace the `agent_chats` CREATE TABLE statement with:

```python
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                provider TEXT DEFAULT 'openai',
                model TEXT DEFAULT 'gpt-4o-mini',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        # Migration: add columns if they don't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE agent_chats ADD COLUMN provider TEXT DEFAULT 'openai'")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE agent_chats ADD COLUMN model TEXT DEFAULT 'gpt-4o-mini'")
        except Exception:
            pass
```

- [ ] **Step 2.3: Add DB functions for findings**

At the end of `backend/src/db.py`, add:

```python
# ===== Findings Operations (Project Database) =====

def add_finding(project_id, request_id, tool, vuln_type, severity, title, description, evidence, remediation):
    """Save a security finding to the project database"""
    project = get_project_by_id(project_id)
    if not project:
        return None

    db_path = get_project_db_path(project['name'])
    now = datetime.utcnow().isoformat()

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO findings (request_id, tool, vuln_type, severity, title, description, evidence, remediation, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (request_id, tool, vuln_type, severity, title, description, evidence, remediation, now))
        return cursor.lastrowid


def get_findings(project_id, severity=None, tool=None):
    """Get security findings for a project with optional filters"""
    project = get_project_by_id(project_id)
    if not project:
        return []

    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return []

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        query = '''
            SELECT f.*, r.url, r.method
            FROM findings f
            LEFT JOIN requests r ON f.request_id = r.id
            WHERE 1=1
        '''
        params = []
        if severity:
            query += ' AND f.severity = ?'
            params.append(severity)
        if tool:
            query += ' AND f.tool = ?'
            params.append(tool)
        query += ' ORDER BY f.timestamp DESC'
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def delete_finding(project_id, finding_id):
    """Delete a finding"""
    project = get_project_by_id(project_id)
    if not project:
        return False

    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return False

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM findings WHERE id = ?', (finding_id,))
        return cursor.rowcount > 0
```

- [ ] **Step 2.4: Update `create_agent_chat` to accept provider/model**

Replace the existing `create_agent_chat` function in `db.py`:

```python
def create_agent_chat(project_id, title=None, provider='openai', model='gpt-4o-mini'):
    """Create a new agent chat"""
    project = get_project_by_id(project_id)
    if not project:
        raise ValueError("Project not found")

    db_path = get_project_db_path(project['name'])
    now = datetime.utcnow().isoformat()

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO agent_chats (title, provider, model, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (title or "New Chat", provider, model, now, now))
        return cursor.lastrowid
```

- [ ] **Step 2.5: Commit**

```bash
git add backend/src/db.py
git commit -m "feat(db): add findings table, provider/model columns to agent_chats"
```

---

## Task 3: Provider abstraction — base + Anthropic

**Files:**
- Create: `backend/src/providers/__init__.py`
- Create: `backend/src/providers/base.py`
- Create: `backend/src/providers/anthropic_provider.py`

- [ ] **Step 3.1: Create providers package**

Create `backend/src/providers/__init__.py`:
```python
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider

_PROVIDERS = {
    'anthropic': AnthropicProvider,
    'openai': OpenAIProvider,
    'ollama': OllamaProvider,
}


def get_provider(name: str):
    """Return an instantiated provider by name. Raises ValueError for unknown names."""
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider: {name}. Choose from: {list(_PROVIDERS)}")
    return cls()
```

- [ ] **Step 3.2: Create base provider**

Create `backend/src/providers/base.py`:
```python
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Abstract AI provider. All providers use OpenAI-compatible message format as the
    normalized interchange format. Each provider converts internally as needed."""

    @abstractmethod
    def chat(self, system: str, messages: list[dict], tools: list[dict], model: str) -> tuple[str, list[dict]]:
        """Send a chat request.

        Args:
            system: System prompt string.
            messages: Conversation history in OpenAI format:
                - {"role": "user", "content": str}
                - {"role": "assistant", "content": str, "tool_calls": [...]}
                - {"role": "tool", "tool_call_id": str, "content": str}
            tools: Tool definitions in OpenAI function-calling format:
                [{"type": "function", "function": {"name": str, "description": str, "parameters": {...}}}]
            model: Model ID string.

        Returns:
            (response_text, tool_calls) where tool_calls is a list of:
                {"id": str, "name": str, "input": dict}
        """

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return available model ID strings for the frontend selector."""

    @abstractmethod
    def supports_tool_use(self) -> bool:
        """Whether this provider supports structured tool calling."""
```

- [ ] **Step 3.3: Create Anthropic provider**

Create `backend/src/providers/anthropic_provider.py`:
```python
import json
import os
import anthropic
from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    MODELS = ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"]

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def chat(self, system: str, messages: list[dict], tools: list[dict], model: str) -> tuple[str, list[dict]]:
        anthropic_tools = [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"],
            }
            for t in tools
        ]

        anthropic_messages = self._convert_messages(messages)

        kwargs = {
            "model": model,
            "max_tokens": 8096,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": anthropic_messages,
        }
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = self.client.messages.create(**kwargs)

        text = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "input": block.input})

        return text, tool_calls

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """Convert OpenAI-format messages to Anthropic format."""
        result = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg["role"]

            if role == "user":
                result.append({"role": "user", "content": msg["content"]})
                i += 1

            elif role == "assistant":
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for tc in msg.get("tool_calls", []):
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"],
                    })
                if not content:
                    content = [{"type": "text", "text": ""}]
                result.append({"role": "assistant", "content": content})
                i += 1

            elif role == "tool":
                # Collect consecutive tool results into one user message
                tool_results = []
                while i < len(messages) and messages[i]["role"] == "tool":
                    tm = messages[i]
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tm["tool_call_id"],
                        "content": tm["content"],
                    })
                    i += 1
                result.append({"role": "user", "content": tool_results})

            else:
                i += 1

        return result

    def list_models(self) -> list[str]:
        return self.MODELS

    def supports_tool_use(self) -> bool:
        return True
```

- [ ] **Step 3.4: Commit**

```bash
git add backend/src/providers/
git commit -m "feat(providers): add provider abstraction base and Anthropic provider"
```

---

## Task 4: OpenAI and Ollama providers

**Files:**
- Create: `backend/src/providers/openai_provider.py`
- Create: `backend/src/providers/ollama_provider.py`

- [ ] **Step 4.1: Create OpenAI provider**

Create `backend/src/providers/openai_provider.py`:
```python
import json
import os
from openai import OpenAI
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self):
        self.client = OpenAI()

    def chat(self, system: str, messages: list[dict], tools: list[dict], model: str) -> tuple[str, list[dict]]:
        openai_messages = [{"role": "system", "content": system}] + messages

        kwargs = {
            "model": model,
            "messages": openai_messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        text = msg.content or ""
        tool_calls = []

        for tc in (msg.tool_calls or []):
            tool_calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "input": json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments,
            })

        return text, tool_calls

    def list_models(self) -> list[str]:
        try:
            models = self.client.models.list()
            return sorted([m.id for m in models.data if "gpt" in m.id])
        except Exception:
            return ["gpt-4o", "gpt-4o-mini"]

    def supports_tool_use(self) -> bool:
        return True
```

- [ ] **Step 4.2: Create Ollama provider**

Create `backend/src/providers/ollama_provider.py`:
```python
import os
import logging
from openai import OpenAI
from .base import BaseProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    def __init__(self):
        base_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1/")
        self.client = OpenAI(base_url=base_url, api_key="ollama")
        self._base_url = base_url

    def chat(self, system: str, messages: list[dict], tools: list[dict], model: str) -> tuple[str, list[dict]]:
        openai_messages = [{"role": "system", "content": system}] + [
            {k: v for k, v in m.items() if k in ("role", "content")}
            for m in messages
            if m["role"] in ("user", "assistant")
        ]

        response = self.client.chat.completions.create(
            model=model,
            messages=openai_messages,
        )
        return response.choices[0].message.content or "", []

    def list_models(self) -> list[str]:
        try:
            import requests as http_req
            ollama_base = self._base_url.rstrip("/").removesuffix("/v1")
            resp = http_req.get(f"{ollama_base}/api/tags", timeout=5)
            if resp.ok:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception as exc:
            logger.debug("Could not fetch Ollama models: %s", exc)
        return []

    def supports_tool_use(self) -> bool:
        return False
```

- [ ] **Step 4.3: Commit**

```bash
git add backend/src/providers/openai_provider.py backend/src/providers/ollama_provider.py
git commit -m "feat(providers): add OpenAI and Ollama providers"
```

---

## Task 5: Security tools

**Files:**
- Create: `backend/src/tools/__init__.py`
- Create: `backend/src/tools/poc_generator.py`
- Create: `backend/src/tools/active_scanner.py`
- Create: `backend/src/tools/static_analyzer.py`
- Create: `backend/src/tools/network_analyzer.py`

- [ ] **Step 5.1: Create tools package**

Create `backend/src/tools/__init__.py`:
```python
from .poc_generator import get_poc_generator_tool_def, generate_poc
from .active_scanner import get_active_scanner_tool_def, active_scan
from .static_analyzer import get_static_analyzer_tool_def, static_analyze
from .network_analyzer import get_network_map_tool_def, network_map

__all__ = [
    "get_poc_generator_tool_def", "generate_poc",
    "get_active_scanner_tool_def", "active_scan",
    "get_static_analyzer_tool_def", "static_analyze",
    "get_network_map_tool_def", "network_map",
]
```

- [ ] **Step 5.2: Create poc_generator.py**

Create `backend/src/tools/poc_generator.py`:
```python
"""AI-powered proof-of-concept exploit generator."""
import json
import re
import logging

logger = logging.getLogger(__name__)


def get_poc_generator_tool_def() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "generate_poc",
            "description": (
                "Generate a proof-of-concept (PoC) exploit for a captured HTTP request. "
                "Supports XSS, SQL injection, SSRF, LFI, RCE, and IDOR vulnerabilities. "
                "Use when asked to create an exploit or test a specific vulnerability type. "
                "Saves the finding to the database."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "integer",
                        "description": "ID of the captured HTTP request to exploit"
                    },
                    "vuln_type": {
                        "type": "string",
                        "enum": ["xss", "sqli", "ssrf", "lfi", "rce", "idor"],
                        "description": "Vulnerability type to generate PoC for"
                    }
                },
                "required": ["request_id", "vuln_type"]
            }
        }
    }


def generate_poc(request_id: int, vuln_type: str, provider, model: str) -> dict:
    """Generate exploit PoC using the active AI provider with request context."""
    from .. import db, state

    project_id = state.get_current_project()
    if not project_id:
        return {"error": "No current project selected"}

    request = db.get_project_request(project_id, request_id)
    if not request:
        return {"error": f"Request {request_id} not found"}

    raw_request = request.get("raw_request", "")

    prompt = f"""You are a security researcher generating a proof-of-concept exploit for authorized penetration testing.

Generate a {vuln_type.upper()} exploit PoC for this HTTP request:

{raw_request}

Respond with a JSON object containing exactly these keys:
- "poc_payload": the specific payload string to inject
- "injection_point": where to inject it (parameter name, header, body field)
- "curl_command": complete curl command demonstrating the exploit
- "success_indicator": what a successful exploitation looks like in the response
- "description": brief explanation of the vulnerability
- "severity": one of "critical", "high", "medium", "low"

Return only the JSON object, no other text."""

    try:
        text, _ = provider.chat(
            system="You are a security researcher generating proof-of-concept exploits for authorized penetration testing. Respond only with valid JSON.",
            messages=[{"role": "user", "content": prompt}],
            tools=[],
            model=model,
        )

        result = {"description": text, "severity": "high", "poc_payload": "", "curl_command": "", "injection_point": ""}
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        db.add_finding(
            project_id, request_id, "generate_poc", vuln_type,
            result.get("severity", "high"),
            f"{vuln_type.upper()} PoC — request #{request_id}",
            result.get("description", text),
            result.get("poc_payload", ""),
            "Validate and sanitize all user-controlled input; apply output encoding."
        )

        return result

    except Exception as exc:
        logger.error("PoC generation failed: %s", exc, exc_info=True)
        return {"error": str(exc)}
```

- [ ] **Step 5.3: Create active_scanner.py**

Create `backend/src/tools/active_scanner.py`:
```python
"""Dynamic parameter fuzzer — sends payload-mutated requests and detects anomalies."""
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

MAX_PAYLOADS = 20  # safety cap per scan run


def get_active_scanner_tool_def() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "active_scan",
            "description": (
                "Dynamically fuzz an HTTP request parameter with a list of payloads and detect "
                "response anomalies (status changes, length differences, error keywords). "
                "Bounded to the target host already in the project database. "
                "Saves findings. Use for injection testing, parameter tampering."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "integer", "description": "ID of the captured request to fuzz"},
                    "parameter": {"type": "string", "description": "Query string or body parameter name to mutate"},
                    "payloads": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of payload strings to inject (max 20 used)"
                    },
                    "threads": {"type": "integer", "description": "Concurrency (default 1; currently sequential)", "default": 1}
                },
                "required": ["request_id", "parameter", "payloads"]
            }
        }
    }


def active_scan(request_id: int, parameter: str, payloads: list, threads: int = 1) -> dict:
    """Fuzz a request parameter and return anomaly findings."""
    from .. import db, state, http_sender

    project_id = state.get_current_project()
    if not project_id:
        return {"error": "No current project selected"}

    request = db.get_project_request(project_id, request_id)
    if not request:
        return {"error": f"Request {request_id} not found"}

    raw_request = request.get("raw_request", "")
    url = request.get("url", "")

    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = str(parsed.port or (443 if parsed.scheme == "https" else 80))
    use_https = parsed.scheme == "https"

    baseline = http_sender.send_raw_http_request(raw_request, host, port, use_https)
    baseline_status = baseline.get("status_code", 0)
    baseline_len = len(baseline.get("raw_response", ""))

    findings = []
    tested = payloads[:MAX_PAYLOADS]

    for payload in tested:
        mutated = re.sub(
            rf'({re.escape(parameter)}=)[^&\s\r\n]*',
            rf'\g<1>{payload}',
            raw_request
        )
        if mutated == raw_request:
            mutated = raw_request + f"\n{parameter}={payload}"

        result = http_sender.send_raw_http_request(mutated, host, port, use_https)
        resp_status = result.get("status_code", 0)
        resp_body = result.get("raw_response", "")
        resp_len = len(resp_body)

        status_changed = resp_status != baseline_status
        big_len_diff = abs(resp_len - baseline_len) > 200
        error_keywords = any(k in resp_body.lower() for k in ["error", "exception", "sql", "warning", "fatal", "traceback"])

        if status_changed or big_len_diff or error_keywords:
            severity = "high" if error_keywords else "medium"
            diff_summary = f"status {baseline_status}→{resp_status}, len_diff={resp_len - baseline_len}"
            finding = {
                "payload": payload,
                "response_diff": diff_summary,
                "severity": severity,
                "status_code": resp_status,
            }
            findings.append(finding)

            db.add_finding(
                project_id, request_id, "active_scan", "parameter_tampering",
                severity,
                f"Anomaly on param '{parameter}' — request #{request_id}",
                diff_summary,
                payload,
                "Validate, sanitize, and encode all user-controlled input."
            )

    return {
        "parameter": parameter,
        "payloads_tested": len(tested),
        "findings_count": len(findings),
        "findings": findings,
    }
```

- [ ] **Step 5.4: Create static_analyzer.py**

Create `backend/src/tools/static_analyzer.py`:
```python
"""Regex-based static analysis of request/response content."""
import re
import logging

logger = logging.getLogger(__name__)

# (name, regex_pattern, severity)
SECRET_PATTERNS = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}", "critical"),
    ("private_key_header", r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "critical"),
    ("api_key_generic", r"(?i)(?:api[_\-]?key|apikey)\s*[=:]\s*['\"]?([a-zA-Z0-9_\-]{20,})", "high"),
    ("jwt_token", r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", "medium"),
    ("password_in_param", r"(?i)(?:password|passwd|pwd)\s*[=:]\s*['\"]?([^'\"\s&]{4,})", "high"),
    ("bearer_token", r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})", "high"),
    ("google_api_key", r"AIza[0-9A-Za-z\-_]{35}", "high"),
    ("slack_token", r"xox[baprs]-[0-9A-Za-z\-]{10,}", "high"),
]

JS_SINK_PATTERNS = [
    ("js_eval", r"\beval\s*\(", "high"),
    ("js_inner_html", r"\.innerHTML\s*=", "high"),
    ("js_document_write", r"document\.write\s*\(", "high"),
    ("js_outer_html", r"\.outerHTML\s*=", "high"),
    ("js_set_attribute", r"\.setAttribute\s*\(\s*['\"]on", "medium"),
    ("js_location_assign", r"(?:location\.href|location\.assign|location\.replace)\s*=", "medium"),
    ("js_document_domain", r"document\.domain\s*=", "high"),
]

SENSITIVE_PATH_PATTERNS = [
    ("exposed_dotenv", r"\.env(?:\b|$)", "high"),
    ("exposed_git", r"\.git(?:/|$)", "high"),
    ("phpinfo", r"phpinfo\(\)", "medium"),
    ("wp_config", r"wp-config\.php", "high"),
    ("server_status", r"/server-status(?:\b|$)", "medium"),
]

SECURITY_HEADERS = [
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "strict-transport-security",
    "x-xss-protection",
    "referrer-policy",
    "permissions-policy",
]

ALL_PATTERNS = SECRET_PATTERNS + JS_SINK_PATTERNS + SENSITIVE_PATH_PATTERNS


def get_static_analyzer_tool_def() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "static_analyze",
            "description": (
                "Analyze a captured HTTP request/response for secrets, dangerous JS sinks, "
                "missing security headers, and exposed sensitive paths. "
                "Saves all findings. Use when asked to analyze a request for vulnerabilities."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "integer", "description": "ID of the captured request to analyze"},
                    "scope": {
                        "type": "string",
                        "enum": ["js", "headers", "body", "all"],
                        "description": "What to analyze: js=JS sinks only, headers=security headers, body=secrets in body, all=everything",
                        "default": "all"
                    }
                },
                "required": ["request_id"]
            }
        }
    }


def static_analyze(request_id: int, scope: str = "all") -> dict:
    """Run static analysis on a captured request/response."""
    from .. import db, state

    project_id = state.get_current_project()
    if not project_id:
        return {"error": "No current project selected"}

    request = db.get_project_request(project_id, request_id)
    if not request:
        return {"error": f"Request {request_id} not found"}

    raw_request = request.get("raw_request", "") or ""
    raw_response = request.get("raw_response", "") or ""
    url = request.get("url", "")

    content = {
        "js": raw_response,
        "body": raw_response,
        "headers": raw_response,
        "all": raw_request + "\n" + raw_response,
    }.get(scope, raw_request + "\n" + raw_response)

    findings = []

    # Pattern-based analysis
    patterns_to_run = ALL_PATTERNS
    if scope == "js":
        patterns_to_run = JS_SINK_PATTERNS
    elif scope == "headers":
        patterns_to_run = []  # only header check below
    elif scope == "body":
        patterns_to_run = SECRET_PATTERNS + SENSITIVE_PATH_PATTERNS

    for name, pattern, severity in patterns_to_run:
        for match in re.finditer(pattern, content):
            value = match.group()[:120]
            findings.append({"type": name, "location": url, "value": value, "severity": severity})
            db.add_finding(
                project_id, request_id, "static_analyze", name,
                severity, f"Static: {name}", f"Matched pattern in {scope} scope",
                value, "Remove or redact sensitive data; apply secure coding practices."
            )

    # Missing security headers check (response only)
    if scope in ("headers", "all"):
        response_lower = raw_response.lower()
        for header in SECURITY_HEADERS:
            if header not in response_lower:
                findings.append({
                    "type": "missing_security_header",
                    "location": url,
                    "value": header,
                    "severity": "medium"
                })
                db.add_finding(
                    project_id, request_id, "static_analyze", "missing_security_header",
                    "medium", f"Missing header: {header}",
                    "Security header absent from HTTP response",
                    header, f"Add '{header}' to all HTTP responses."
                )

    return {"findings": findings, "total": len(findings), "scope": scope}
```

- [ ] **Step 5.5: Create network_analyzer.py**

Create `backend/src/tools/network_analyzer.py`:
```python
"""Host and connection mapper from captured traffic."""
import sqlite3
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def get_network_map_tool_def() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "network_map",
            "description": (
                "Map all unique hosts, HTTP method distributions, status code distributions, "
                "and request timeline from captured traffic in the current project. "
                "Useful for attack surface mapping and understanding application topology."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID to analyze (uses current project if omitted)"
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional filters: {host: str, method: str, status_code: int}",
                        "properties": {
                            "host": {"type": "string"},
                            "method": {"type": "string"},
                            "status_code": {"type": "integer"}
                        }
                    }
                },
                "required": []
            }
        }
    }


def network_map(project_id: int = None, filters: dict = None) -> dict:
    """Aggregate host/connection/timeline data from the project requests database."""
    from .. import db, state

    pid = project_id or state.get_current_project()
    if not pid:
        return {"error": "No current project selected"}

    project = db.get_project_by_id(pid)
    if not project:
        return {"error": f"Project {pid} not found"}

    db_path = db.get_project_db_path(project["name"])

    import os
    if not os.path.exists(db_path):
        return {"hosts": [], "connections": [], "timeline": [], "method_counts": {}, "status_counts": {}}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT url, method, status_code, timestamp FROM requests WHERE 1=1"
    params = []
    filters = filters or {}

    if filters.get("method"):
        query += " AND method = ?"
        params.append(filters["method"])
    if filters.get("status_code"):
        query += " AND status_code = ?"
        params.append(filters["status_code"])

    query += " ORDER BY timestamp ASC LIMIT 2000"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    hosts = {}
    method_counts = {}
    status_counts = {}
    timeline = []

    for row in rows:
        url = row.get("url", "")
        parsed = urlparse(url)
        host = parsed.netloc or parsed.hostname or ""
        if not host:
            continue

        host_filter = filters.get("host", "")
        if host_filter and host_filter not in host:
            continue

        hosts[host] = hosts.get(host, 0) + 1
        method = row.get("method", "?")
        method_counts[method] = method_counts.get(method, 0) + 1
        status = str(row.get("status_code", "?"))
        status_counts[status] = status_counts.get(status, 0) + 1

        timeline.append({
            "timestamp": row.get("timestamp"),
            "host": host,
            "method": method,
            "status": row.get("status_code"),
        })

    sorted_hosts = [{"host": h, "request_count": c} for h, c in sorted(hosts.items(), key=lambda x: -x[1])]

    return {
        "hosts": sorted_hosts,
        "total_requests": len(rows),
        "method_counts": method_counts,
        "status_counts": status_counts,
        "timeline": timeline[:500],
    }
```

- [ ] **Step 5.6: Commit**

```bash
git add backend/src/tools/
git commit -m "feat(tools): add PoC generator, active scanner, static analyzer, network mapper"
```

---

## Task 6: Update agent.py — provider abstraction + security tools + /models endpoint

**Files:**
- Modify: `backend/src/api/agent.py` (full rewrite of core logic)

- [ ] **Step 6.1: Rewrite agent.py**

Replace the entire content of `backend/src/api/agent.py` with:

```python
"""
API endpoints for agent functionality with multi-provider support.
Supported providers: anthropic, openai, ollama
"""
import json
import logging
import os

from flask import Blueprint, request, jsonify
from .. import db, state
from ..providers import get_provider
from ..api.tools import (
    get_query_database_tool, get_send_request_tool, get_browse_tool,
    query_database, send_request, browse,
)
from ..tools import (
    get_poc_generator_tool_def, generate_poc,
    get_active_scanner_tool_def, active_scan,
    get_static_analyzer_tool_def, static_analyze,
    get_network_map_tool_def, network_map,
)

logger = logging.getLogger(__name__)

agent_bp = Blueprint('agent', __name__)

SYSTEM_MESSAGE = """You are OblivionSec — an advanced DAST (Dynamic Application Security Testing) AI assistant for authorized security professionals.

You have access to seven tools:

1. QUERY DATABASE — SQL SELECT queries against captured HTTP requests.
   Table: requests (id, method, url, status_code, timestamp, raw_request, raw_response, duration_ms, flow_id)

2. SEND REQUEST — Send/resend/modify raw HTTP requests to any host.

3. BROWSE — Control an automated browser to navigate sites and capture traffic.

4. GENERATE POC — Generate proof-of-concept exploits (XSS, SQLi, SSRF, LFI, RCE, IDOR) from a captured request.

5. ACTIVE SCAN — Fuzz request parameters with payloads and detect anomalies (status changes, error messages, length diffs).

6. STATIC ANALYZE — Regex analysis of request/response for secrets, dangerous JS sinks, missing security headers.

7. NETWORK MAP — Map unique hosts, method/status distributions, and request timeline from captured traffic.

After tool calls, analyze results and provide clear security-focused summaries. All testing must be on authorized targets only."""


def _get_all_tools() -> list:
    return [
        get_query_database_tool(),
        get_send_request_tool(),
        get_browse_tool(),
        get_poc_generator_tool_def(),
        get_active_scanner_tool_def(),
        get_static_analyzer_tool_def(),
        get_network_map_tool_def(),
    ]


def _dispatch_tool(tool_name: str, tool_args: dict, provider, model: str) -> dict:
    """Execute a tool by name and return its output dict."""
    if tool_name == "query_database":
        return query_database(tool_args.get("sql_query", ""))
    if tool_name == "send_request":
        return send_request(
            tool_args.get("raw_request", ""),
            tool_args.get("host", "example.com"),
            tool_args.get("port", "443"),
            tool_args.get("use_https"),
        )
    if tool_name == "browse":
        return browse(tool_args.get("task", ""), tool_args.get("additional_tasks"))
    if tool_name == "generate_poc":
        return generate_poc(tool_args.get("request_id"), tool_args.get("vuln_type", "xss"), provider, model)
    if tool_name == "active_scan":
        return active_scan(
            tool_args.get("request_id"), tool_args.get("parameter", ""),
            tool_args.get("payloads", []), tool_args.get("threads", 1)
        )
    if tool_name == "static_analyze":
        return static_analyze(tool_args.get("request_id"), tool_args.get("scope", "all"))
    if tool_name == "network_map":
        return network_map(tool_args.get("project_id"), tool_args.get("filters"))
    return {"error": f"Unknown tool: {tool_name}"}


def _step_label(tool_name: str) -> str:
    return {
        "query_database": "Querying database",
        "send_request": "Sending HTTP request",
        "browse": "Browsing the web",
        "generate_poc": "Generating PoC exploit",
        "active_scan": "Running active scan",
        "static_analyze": "Running static analysis",
        "network_map": "Mapping network",
    }.get(tool_name, tool_name)


def _result_label(tool_name: str, output: dict) -> str:
    if tool_name == "query_database":
        return f"Found {output.get('count', 0)} requests"
    if tool_name == "send_request":
        return f"Response: {output.get('status_code', '?')}" if not output.get("error") else f"Error: {output['error']}"
    if tool_name == "browse":
        return output.get("message", "Browse completed") if output.get("status") != "error" else f"Browse failed: {output.get('error')}"
    if tool_name == "generate_poc":
        return f"PoC generated ({output.get('severity', '?')} severity)" if not output.get("error") else f"PoC error: {output['error']}"
    if tool_name == "active_scan":
        return f"Scan complete — {output.get('findings_count', 0)} findings in {output.get('payloads_tested', 0)} payloads"
    if tool_name == "static_analyze":
        return f"Analysis complete — {output.get('total', 0)} findings"
    if tool_name == "network_map":
        return f"Mapped {len(output.get('hosts', []))} hosts, {output.get('total_requests', 0)} requests"
    return "Tool completed"


def is_ai_configured() -> bool:
    """True if any supported AI provider key is set."""
    return bool(
        os.environ.get("ANTHROPIC_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("USE_OLLAMA", "").strip().lower() not in ("", "false", "0", "no")
    )


def _default_provider_and_model() -> tuple[str, str]:
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return "anthropic", "claude-sonnet-4-6"
    if os.environ.get("USE_OLLAMA", "").lower() not in ("", "false", "0", "no"):
        return "ollama", os.environ.get("MODEL", "")
    return "openai", os.environ.get("MODEL", "gpt-4o-mini")


@agent_bp.route('/status', methods=['GET'])
def get_ai_status():
    try:
        configured = is_ai_configured()
        return jsonify({'configured': configured, 'message': 'AI is configured' if configured else 'No AI key detected'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/models', methods=['GET'])
def get_models():
    """Return available models for a given provider."""
    provider_name = request.args.get('provider', 'openai')
    try:
        provider = get_provider(provider_name)
        models = provider.list_models()
        return jsonify({'models': models}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error("Error fetching models for %s: %s", provider_name, e)
        return jsonify({'models': [], 'error': str(e)}), 200


@agent_bp.route('/chats', methods=['GET'])
def get_chats():
    try:
        project_id = state.get_current_project()
        if not project_id:
            return jsonify({'error': 'No current project selected'}), 400
        return jsonify(db.get_agent_chats(project_id)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/chats', methods=['POST'])
def create_chat():
    try:
        project_id = state.get_current_project()
        if not project_id:
            return jsonify({'error': 'No current project selected'}), 400
        data = request.get_json() or {}
        default_provider, default_model = _default_provider_and_model()
        chat_id = db.create_agent_chat(
            project_id,
            title=data.get('title', 'New Chat'),
            provider=data.get('provider', default_provider),
            model=data.get('model', default_model),
        )
        return jsonify(db.get_agent_chat(project_id, chat_id)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/chats/<int:chat_id>', methods=['GET'])
def get_chat(chat_id):
    try:
        project_id = state.get_current_project()
        if not project_id:
            return jsonify({'error': 'No current project selected'}), 400
        chat = db.get_agent_chat(project_id, chat_id)
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        messages = db.get_agent_messages(project_id, chat_id)
        return jsonify({'chat': chat, 'messages': messages}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/chats/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    try:
        project_id = state.get_current_project()
        if not project_id:
            return jsonify({'error': 'No current project selected'}), 400
        if not db.delete_agent_chat(project_id, chat_id):
            return jsonify({'error': 'Chat not found'}), 404
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/chat', methods=['POST'])
def chat_with_agent():
    """Process a chat message through the selected AI provider."""
    try:
        if not is_ai_configured():
            return jsonify({'error': 'No AI provider configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or USE_OLLAMA.'}), 400

        data = request.get_json()
        if not data or not data.get('message'):
            return jsonify({'error': 'message is required'}), 400

        message = data['message']
        chat_id = data.get('chat_id')
        request_provider = data.get('provider')
        request_model = data.get('model')

        project_id = state.get_current_project()
        if not project_id:
            return jsonify({'error': 'No current project selected'}), 400

        default_provider, default_model = _default_provider_and_model()

        # Create chat if new
        if not chat_id:
            title = message[:50] if len(message) > 50 else message
            chat_id = db.create_agent_chat(
                project_id, title,
                provider=request_provider or default_provider,
                model=request_model or default_model,
            )

        # Load provider/model from chat record
        chat_record = db.get_agent_chat(project_id, chat_id)
        provider_name = request_provider or (chat_record or {}).get('provider', default_provider)
        model = request_model or (chat_record or {}).get('model', default_model)

        provider = get_provider(provider_name)
        tools = _get_all_tools() if provider.supports_tool_use() else []

        db.add_agent_message(project_id, chat_id, 'user', message)

        db_messages = db.get_agent_messages(project_id, chat_id)
        messages = [
            {'role': m['role'], 'content': m['content']}
            for m in db_messages
            if m['role'] in ('user', 'assistant')
        ]

        max_iterations = 10
        for _ in range(max_iterations):
            text, tool_calls = provider.chat(SYSTEM_MESSAGE, messages, tools, model)

            if tool_calls:
                # Add assistant message with tool calls (OpenAI format for normalization)
                assistant_msg = {
                    'role': 'assistant',
                    'content': text or None,
                    'tool_calls': [
                        {
                            'id': tc['id'],
                            'type': 'function',
                            'function': {'name': tc['name'], 'arguments': json.dumps(tc['input'])},
                        }
                        for tc in tool_calls
                    ],
                }
                messages.append(assistant_msg)

                for tc in tool_calls:
                    db.add_agent_message(
                        project_id, chat_id, 'step', _step_label(tc['name']),
                        step_type='tool_call', tool_name=tc['name'], tool_input=tc['input']
                    )

                    output = _dispatch_tool(tc['name'], tc['input'], provider, model)

                    db.add_agent_message(
                        project_id, chat_id, 'step', _result_label(tc['name'], output),
                        step_type='tool_result', tool_name=tc['name'],
                        tool_input=tc['input'], tool_output=output
                    )

                    messages.append({
                        'role': 'tool',
                        'tool_call_id': tc['id'],
                        'content': json.dumps(output),
                    })
            else:
                if text:
                    db.add_agent_message(project_id, chat_id, 'assistant', text)
                break

        return jsonify({'chat_id': chat_id}), 200

    except Exception as e:
        logger.error("Error in agent chat: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/resender_agent', methods=['POST'])
def resender_agent():
    """AI copilot for resender — query-only, returns modified request text."""
    try:
        if not is_ai_configured():
            return jsonify({'error': 'No AI provider configured.'}), 400
        data = request.get_json()
        if not data or not data.get('text'):
            return jsonify({'error': 'text is required'}), 400

        project_id = state.get_current_project()
        if not project_id:
            return jsonify({'error': 'No current project selected'}), 400

        default_provider, default_model = _default_provider_and_model()
        provider_name = data.get('provider', default_provider)
        model = data.get('model', default_model)
        provider = get_provider(provider_name)

        system = """You are an AI copilot for editing HTTP requests. Query the database for context if needed, then return ONLY the modified HTTP request string with no other text."""
        tools = [get_query_database_tool()] if provider.supports_tool_use() else []
        messages = [{'role': 'user', 'content': data['text']}]

        for _ in range(10):
            text, tool_calls = provider.chat(system, messages, tools, model)
            if not tool_calls:
                return jsonify({'text': text or data['text']}), 200
            messages.append({
                'role': 'assistant', 'content': None,
                'tool_calls': [{'id': tc['id'], 'type': 'function', 'function': {'name': tc['name'], 'arguments': json.dumps(tc['input'])}} for tc in tool_calls]
            })
            for tc in tool_calls:
                output = _dispatch_tool(tc['name'], tc['input'], provider, model)
                messages.append({'role': 'tool', 'tool_call_id': tc['id'], 'content': json.dumps(output)})

        return jsonify({'text': data['text']}), 200

    except Exception as e:
        logger.error("Error in resender agent: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 6.2: Commit**

```bash
git add backend/src/api/agent.py
git commit -m "feat(agent): multi-provider support + 4 security tools + /models endpoint"
```

---

## Task 7: Findings API blueprint

**Files:**
- Create: `backend/src/api/findings.py`
- Modify: `backend/src/api/__init__.py`
- Modify: `backend/main.py`

- [ ] **Step 7.1: Create findings.py blueprint**

Create `backend/src/api/findings.py`:
```python
"""REST endpoints for security findings."""
from flask import Blueprint, jsonify, request
from .. import db, state
import logging

logger = logging.getLogger(__name__)

findings_bp = Blueprint('findings', __name__)


@findings_bp.route('', methods=['GET'])
def get_findings(project_id: int):
    try:
        severity = request.args.get('severity')
        tool = request.args.get('tool')
        findings = db.get_findings(project_id, severity=severity, tool=tool)
        return jsonify(findings), 200
    except Exception as e:
        logger.error("Error getting findings: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500


@findings_bp.route('/<int:finding_id>', methods=['DELETE'])
def delete_finding(project_id: int, finding_id: int):
    try:
        success = db.delete_finding(project_id, finding_id)
        if not success:
            return jsonify({'error': 'Finding not found'}), 404
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error("Error deleting finding: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 7.2: Register findings blueprint in __init__.py**

In `backend/src/api/__init__.py`, add findings registration:

```python
from flask import Blueprint
from .projects import projects_bp
from .requests import requests_bp
from .proxy import proxy_bp
from .resender import resender_bp
from .agent import agent_bp
from .findings import findings_bp

api_bp = Blueprint('api', __name__, url_prefix='/api')

api_bp.register_blueprint(projects_bp, url_prefix='/projects')
api_bp.register_blueprint(proxy_bp, url_prefix='/proxy')
api_bp.register_blueprint(agent_bp, url_prefix='/agent')


def register_requests_blueprint(app):
    app.register_blueprint(requests_bp, url_prefix='/api/projects/<int:project_id>/requests')


def register_resender_blueprint(app):
    app.register_blueprint(resender_bp, url_prefix='/api/projects/<int:project_id>/resender')


def register_findings_blueprint(app):
    app.register_blueprint(findings_bp, url_prefix='/api/projects/<int:project_id>/findings')
```

- [ ] **Step 7.3: Register in main.py**

In `backend/main.py`, update the import and add registration:

```python
from src.api import api_bp, register_requests_blueprint, register_resender_blueprint, register_findings_blueprint
```

Inside `create_app()`, after `register_resender_blueprint(app)`:
```python
    register_findings_blueprint(app)
```

Also update startup print lines to say "OblivionSec":
```python
    print(f"🌐 Starting OblivionSec server on http://localhost:{port}")
    print(f"🔗 CORS enabled for frontend at http://localhost:5173")
    print(f"📡 Proxy API available at /api/proxy")
    print(f"🌍 Proxy available at http://localhost:{proxy_manager.get_proxy_port()}")
```

- [ ] **Step 7.4: Commit**

```bash
git add backend/src/api/findings.py backend/src/api/__init__.py backend/main.py
git commit -m "feat(api): add findings blueprint with GET/DELETE endpoints"
```

---

## Task 8: Frontend API client — models, findings, provider/model in chatWithAgent

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 8.1: Add Finding type and new methods to api.ts**

Add the `Finding` interface after the existing type definitions:

```typescript
export interface Finding {
  id: number;
  request_id: number | null;
  tool: string;
  vuln_type: string | null;
  severity: string;
  title: string;
  description: string | null;
  evidence: string | null;
  remediation: string | null;
  timestamp: string;
  url?: string;
  method?: string;
}
```

Update `chatWithAgent` to accept provider and model:

```typescript
  async chatWithAgent(
    message: string,
    chatId?: number,
    provider?: string,
    model?: string,
  ): Promise<number> {
    const url = `${this.baseUrl}/api/agent/chat`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, chat_id: chatId, provider, model }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    const data = await response.json();
    return data.chat_id || 0;
  }
```

Add new methods inside the `ApiClient` class before the closing `}`:

```typescript
  async getModels(provider: string): Promise<string[]> {
    const data = await this.request<{ models: string[] }>(`/api/agent/models?provider=${provider}`);
    return data.models;
  }

  async getFindings(projectId: number, severity?: string, tool?: string): Promise<Finding[]> {
    const params = new URLSearchParams();
    if (severity) params.append('severity', severity);
    if (tool) params.append('tool', tool);
    const query = params.toString() ? `?${params}` : '';
    return this.request<Finding[]>(`/api/projects/${projectId}/findings${query}`);
  }

  async deleteFinding(projectId: number, findingId: number): Promise<void> {
    return this.request<void>(`/api/projects/${projectId}/findings/${findingId}`, { method: 'DELETE' });
  }

  async createAgentChat(title?: string, provider?: string, model?: string): Promise<any> {
    return this.request<any>('/api/agent/chats', {
      method: 'POST',
      body: JSON.stringify({ title, provider, model }),
    });
  }
```

- [ ] **Step 8.2: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(api-client): add models, findings endpoints; update chatWithAgent signature"
```

---

## Task 9: AgentTab — provider/model selector

**Files:**
- Modify: `frontend/src/components/tabs/AgentTab.tsx`

- [ ] **Step 9.1: Add provider/model state and selector UI to AgentTab.tsx**

Add these imports at the top (after existing imports):
```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
```

Add state variables inside the component (after `const textareaRef`):
```tsx
  const [provider, setProvider] = useState<string>("openai");
  const [model, setModel] = useState<string>("gpt-4o-mini");
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
```

Add a `useEffect` to fetch models when provider changes (after the existing `useEffect` for AI status):
```tsx
  useEffect(() => {
    const fetchModels = async () => {
      setModelsLoading(true);
      try {
        const models = await api.getModels(provider);
        setAvailableModels(models);
        if (models.length > 0 && !models.includes(model)) {
          setModel(models[0]);
        }
      } catch (e) {
        setAvailableModels([]);
      } finally {
        setModelsLoading(false);
      }
    };
    if (aiConfigured) fetchModels();
  }, [provider, aiConfigured]);
```

Update `loadChat` to restore provider/model from chat record:
```tsx
  const loadChat = async (chatId: number) => {
    try {
      setCurrentChatId(chatId);
      setIsLoading(true);
      const { chat, messages: chatMessages } = await api.getAgentChat(chatId);
      if (chat.provider) setProvider(chat.provider);
      if (chat.model) setModel(chat.model);
      // ... rest of existing loadChat logic
```

Update `handleSend` to pass provider/model:
```tsx
      const chatId = await api.chatWithAgent(messageText, currentChatId || undefined, provider, model);
```

Add the provider/model selector bar at the top of the main chat area (replace the existing `{/* Main chat area */}` opening `<div>`):
```tsx
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Provider/Model selector bar */}
        <div className="border-b border-border px-4 py-2 flex items-center gap-4 bg-card">
          <div className="flex items-center gap-2">
            <Label className="text-xs text-muted-foreground whitespace-nowrap">Provider</Label>
            <Select value={provider} onValueChange={setProvider} disabled={isLoading}>
              <SelectTrigger className="h-7 text-xs w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="anthropic">Anthropic</SelectItem>
                <SelectItem value="openai">OpenAI</SelectItem>
                <SelectItem value="ollama">Ollama</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2 flex-1">
            <Label className="text-xs text-muted-foreground whitespace-nowrap">Model</Label>
            {availableModels.length > 0 ? (
              <Select value={model} onValueChange={setModel} disabled={isLoading || modelsLoading}>
                <SelectTrigger className="h-7 text-xs flex-1 max-w-64">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {availableModels.map((m) => (
                    <SelectItem key={m} value={m}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <input
                className="h-7 text-xs border rounded px-2 flex-1 max-w-64 bg-background"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                disabled={isLoading || modelsLoading}
                placeholder="model name"
              />
            )}
          </div>
          {provider === "ollama" && (
            <span className="text-xs text-muted-foreground">(text-only mode)</span>
          )}
        </div>
```

- [ ] **Step 9.2: Commit**

```bash
git add frontend/src/components/tabs/AgentTab.tsx
git commit -m "feat(ui): add provider/model selector to Agent tab"
```

---

## Task 10: Scanner tab

**Files:**
- Create: `frontend/src/components/tabs/ScannerTab.tsx`

- [ ] **Step 10.1: Create ScannerTab.tsx**

Create `frontend/src/components/tabs/ScannerTab.tsx`:
```tsx
import { useState, useEffect, useCallback } from "react";
import { api, Finding } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Trash2, RefreshCw, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-600 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-yellow-500 text-black",
  low: "bg-blue-500 text-white",
  info: "bg-gray-400 text-white",
};

const TOOLS = ["generate_poc", "active_scan", "static_analyze", "network_map"];

export const ScannerTab = () => {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [toolFilter, setToolFilter] = useState<string>("all");
  const [currentProjectId, setCurrentProjectId] = useState<number | null>(null);

  useEffect(() => {
    api.getCurrentProject().then((r) => {
      if (r.project) setCurrentProjectId(r.project.id);
    }).catch(() => {});
  }, []);

  const loadFindings = useCallback(async () => {
    if (!currentProjectId) return;
    setLoading(true);
    try {
      const data = await api.getFindings(
        currentProjectId,
        severityFilter !== "all" ? severityFilter : undefined,
        toolFilter !== "all" ? toolFilter : undefined,
      );
      setFindings(data);
    } catch (e) {
      toast.error("Failed to load findings");
    } finally {
      setLoading(false);
    }
  }, [currentProjectId, severityFilter, toolFilter]);

  useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  const handleDelete = async (findingId: number) => {
    if (!currentProjectId) return;
    try {
      await api.deleteFinding(currentProjectId, findingId);
      setFindings((prev) => prev.filter((f) => f.id !== findingId));
      toast.success("Finding deleted");
    } catch {
      toast.error("Failed to delete finding");
    }
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Toolbar */}
      <div className="border-b border-border px-4 py-2 flex items-center gap-3 bg-card">
        <ShieldAlert className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium">Security Findings</span>
        <div className="flex items-center gap-2 ml-4">
          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger className="h-7 text-xs w-28">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="info">Info</SelectItem>
            </SelectContent>
          </Select>
          <Select value={toolFilter} onValueChange={setToolFilter}>
            <SelectTrigger className="h-7 text-xs w-36">
              <SelectValue placeholder="Tool" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All tools</SelectItem>
              {TOOLS.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button variant="ghost" size="sm" onClick={loadFindings} disabled={loading} className="ml-auto h-7">
          <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
        </Button>
        <span className="text-xs text-muted-foreground">{findings.length} finding{findings.length !== 1 ? "s" : ""}</span>
      </div>

      {/* Table */}
      {findings.length === 0 ? (
        <div className="flex flex-col items-center justify-center flex-1 text-muted-foreground">
          <ShieldAlert className="h-16 w-16 opacity-20 mb-4" />
          <p className="text-sm">No findings yet. Use the Agent tab to run security tools.</p>
        </div>
      ) : (
        <ScrollArea className="flex-1">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-card border-b border-border">
              <tr className="text-left text-xs text-muted-foreground">
                <th className="px-3 py-2 w-24">Severity</th>
                <th className="px-3 py-2 w-32">Tool</th>
                <th className="px-3 py-2 w-32">Type</th>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2 max-w-xs">Evidence</th>
                <th className="px-3 py-2 w-36">Timestamp</th>
                <th className="px-3 py-2 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f) => (
                <tr key={f.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="px-3 py-2">
                    <Badge className={`text-xs ${SEVERITY_COLORS[f.severity] || "bg-gray-400 text-white"}`}>
                      {f.severity}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground font-mono">{f.tool}</td>
                  <td className="px-3 py-2 text-xs font-mono truncate max-w-[128px]" title={f.vuln_type || ""}>{f.vuln_type || "—"}</td>
                  <td className="px-3 py-2 font-medium text-xs">{f.title}</td>
                  <td className="px-3 py-2 text-xs font-mono text-muted-foreground truncate max-w-xs" title={f.evidence || ""}>
                    {f.evidence || "—"}
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(f.timestamp).toLocaleString()}
                  </td>
                  <td className="px-3 py-2">
                    <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handleDelete(f.id)}>
                      <Trash2 className="h-3 w-3 text-destructive" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollArea>
      )}
    </div>
  );
};
```

- [ ] **Step 10.2: Commit**

```bash
git add frontend/src/components/tabs/ScannerTab.tsx
git commit -m "feat(ui): add Scanner tab showing security findings table"
```

---

## Task 11: AppTabs — Scanner tab + agent navigation callback

**Files:**
- Modify: `frontend/src/components/AppTabs.tsx`

- [ ] **Step 11.1: Add Scanner tab and agent navigation to AppTabs.tsx**

Replace the full content of `AppTabs.tsx`:

```tsx
import { useState, useEffect, useRef } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { HomeTab } from "./tabs/HomeTab";
import { ProxyTab } from "./tabs/ProxyTab";
import { ProjectTab } from "./tabs/ProjectTab";
import { ResenderTab } from "./tabs/ResenderTab";
import { AgentTab } from "./tabs/AgentTab";
import { ScannerTab } from "./tabs/ScannerTab";
import { useResender } from "@/contexts/ResenderContext";
import { StatusIndicators } from "./StatusIndicators";
import { Home, Repeat, Globe, Folder, Bot, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";

export const AppTabs = () => {
  const { tabs, setNavigateCallback } = useResender();
  const [activeMainTab, setActiveMainTab] = useState("home");
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);
  const [aiStatusMessage, setAiStatusMessage] = useState<string>("");
  const pendingAgentMessage = useRef<string | null>(null);

  useEffect(() => {
    setNavigateCallback(() => {
      setActiveMainTab("resender");
    });
  }, [setNavigateCallback]);

  useEffect(() => {
    const checkAiStatus = async () => {
      try {
        const status = await api.getAiStatus();
        setAiConfigured(status.configured);
        setAiStatusMessage(status.message);
      } catch {
        setAiConfigured(false);
        setAiStatusMessage("No .env with AI key detected");
      }
    };
    checkAiStatus();
  }, []);

  const navigateToAgent = (message: string) => {
    pendingAgentMessage.current = message;
    setActiveMainTab("agent");
  };

  return (
    <Tabs value={activeMainTab} onValueChange={setActiveMainTab} className="flex-1 flex flex-col min-h-0">
      <div className="border-b bg-card px-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="font-logo text-2xl font-bold text-primary tracking-tight">
              OblivionSec
            </span>
          </div>
          <TabsList className="h-12 gap-1 bg-transparent p-0">
            <TabsTrigger value="home" className="data-[state=active]:bg-muted data-[state=active]:shadow-none gap-2 px-4 hover:bg-success/10 transition-colors">
              <Home className="h-4 w-4" />
              Home
            </TabsTrigger>
            <TabsTrigger value="resender" className="data-[state=active]:bg-muted data-[state=active]:shadow-none gap-2 px-4 hover:bg-success/10 transition-colors">
              <Repeat className="h-4 w-4" />
              Resender
              {tabs.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-primary/20 text-primary">{tabs.length}</span>
              )}
            </TabsTrigger>
            <TabsTrigger value="proxy" className="data-[state=active]:bg-muted data-[state=active]:shadow-none gap-2 px-4 hover:bg-success/10 transition-colors">
              <Globe className="h-4 w-4" />
              Proxy
            </TabsTrigger>
            <TabsTrigger value="scanner" className="data-[state=active]:bg-muted data-[state=active]:shadow-none gap-2 px-4 hover:bg-success/10 transition-colors">
              <ShieldAlert className="h-4 w-4" />
              Scanner
            </TabsTrigger>
            <TabsTrigger value="project" className="data-[state=active]:bg-muted data-[state=active]:shadow-none gap-2 px-4 hover:bg-success/10 transition-colors">
              <Folder className="h-4 w-4" />
              Project
            </TabsTrigger>
            <TabsTrigger
              value="agent"
              disabled={aiConfigured === false}
              className={`data-[state=active]:bg-muted data-[state=active]:shadow-none gap-2 px-4 hover:bg-success/10 transition-colors ${aiConfigured === false ? 'opacity-50 cursor-not-allowed text-destructive' : ''}`}
              title={aiConfigured === false ? aiStatusMessage : undefined}
            >
              <Bot className="h-4 w-4" />
              Agent
              {aiConfigured === false && <span className="ml-1 text-xs text-destructive">⚠</span>}
            </TabsTrigger>
          </TabsList>
        </div>
        <StatusIndicators onProxyClick={() => setActiveMainTab("proxy")} />
      </div>

      <TabsContent value="home" className="flex-1 mt-0 min-h-0">
        <HomeTab onSendToAgent={navigateToAgent} />
      </TabsContent>
      <TabsContent value="resender" className="flex-1 mt-0 min-h-0">
        <ResenderTab />
      </TabsContent>
      <TabsContent value="proxy" className="flex-1 mt-0 min-h-0">
        <ProxyTab />
      </TabsContent>
      <TabsContent value="scanner" className="flex-1 mt-0 min-h-0">
        <ScannerTab />
      </TabsContent>
      <TabsContent value="project" className="flex-1 mt-0 min-h-0">
        <ProjectTab />
      </TabsContent>
      <TabsContent value="agent" className="flex-1 mt-0 min-h-0">
        <AgentTab pendingMessage={pendingAgentMessage} />
      </TabsContent>
    </Tabs>
  );
};
```

- [ ] **Step 11.2: Commit**

```bash
git add frontend/src/components/AppTabs.tsx
git commit -m "feat(ui): add Scanner tab to navigation, agent navigation callback"
```

---

## Task 12: HomeTab right-click context menu + AgentTab pendingMessage prop

**Files:**
- Modify: `frontend/src/components/RequestList.tsx`
- Modify: `frontend/src/components/tabs/HomeTab.tsx`
- Modify: `frontend/src/components/tabs/AgentTab.tsx`

- [ ] **Step 12.1: Add onSendToAgent prop to HomeTab**

In `frontend/src/components/tabs/HomeTab.tsx`, update the component signature to accept the prop:

Find (near line 49):
```tsx
export const HomeTab = () => {
```

Replace with:
```tsx
interface HomeTabProps {
  onSendToAgent?: (message: string) => void;
}

export const HomeTab = ({ onSendToAgent }: HomeTabProps) => {
```

- [ ] **Step 12.2: Add right-click context menu to RequestList**

In `frontend/src/components/RequestList.tsx`, find the component that renders each request row. Add a `onSendToAgent` prop and wrap rows in a `ContextMenu`. Import at the top:

```tsx
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { Bot, Zap, Shield } from "lucide-react";
```

Add `onSendToAgent?: (message: string) => void` to the `RequestList` props interface.

For each request row, wrap with:
```tsx
<ContextMenu key={request.id}>
  <ContextMenuTrigger asChild>
    {/* existing row JSX */}
  </ContextMenuTrigger>
  <ContextMenuContent>
    <ContextMenuItem onClick={() => onSendToAgent?.(`Analyze request #${request.id}: ${request.method} ${request.url}`)}>
      <Bot className="w-4 h-4 mr-2" />
      Analyze with AI
    </ContextMenuItem>
    <ContextMenuItem onClick={() => onSendToAgent?.(`Generate a PoC for request #${request.id} — try XSS, SQLi, SSRF as relevant`)}>
      <Shield className="w-4 h-4 mr-2" />
      Generate PoC
    </ContextMenuItem>
    <ContextMenuItem onClick={() => onSendToAgent?.(`Run an active scan on request #${request.id} — test common injection parameters`)}>
      <Zap className="w-4 h-4 mr-2" />
      Active Scan
    </ContextMenuItem>
  </ContextMenuContent>
</ContextMenu>
```

Pass `onSendToAgent` from `HomeTab` down to `RequestList`.

- [ ] **Step 12.3: Add pendingMessage support to AgentTab**

In `frontend/src/components/tabs/AgentTab.tsx`, update the component to accept and consume a pending message ref:

```tsx
interface AgentTabProps {
  pendingMessage?: React.MutableRefObject<string | null>;
}

export const AgentTab = ({ pendingMessage }: AgentTabProps) => {
```

Add a `useEffect` that fires when the tab becomes active and a pending message exists:
```tsx
  useEffect(() => {
    if (pendingMessage?.current && aiConfigured) {
      const msg = pendingMessage.current;
      pendingMessage.current = null;
      setInput(msg);
      // Optionally auto-send:
      // setTimeout(() => handleSend(), 100);
    }
  }, [aiConfigured, pendingMessage]);
```

- [ ] **Step 12.4: Commit**

```bash
git add frontend/src/components/RequestList.tsx frontend/src/components/tabs/HomeTab.tsx frontend/src/components/tabs/AgentTab.tsx
git commit -m "feat(ui): right-click context menu on requests — Analyze/PoC/Scan actions send to Agent"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ Section 1 Rebranding: Tasks 1 covers all rename locations
- ✅ Section 2 Provider abstraction: Tasks 3–4 + agent.py update in Task 6
- ✅ Section 2 `/models` endpoint: Task 6 (agent.py)
- ✅ Section 2 DB provider/model columns: Task 2
- ✅ Section 3 Four security tools: Task 5
- ✅ Section 3 findings table: Task 2
- ✅ Section 3 tools registered in agent: Task 6
- ✅ Section 4 Provider/model selector in Agent tab: Task 9
- ✅ Section 4 Scanner tab: Tasks 10–11
- ✅ Section 4 Right-click context menu: Task 12

**Type consistency:**
- `add_finding` called with 9 positional args in all tools — matches definition in db.py Task 2
- `get_provider(name)` returns provider instance — used in agent.py
- `provider.chat(system, messages, tools, model)` — consistent signature across all providers
- `tool_calls` format `[{"id", "name", "input"}]` — consistent in all providers and agent loop
- `api.chatWithAgent(message, chatId, provider, model)` — matches updated signature in api.ts
- `AgentTab({ pendingMessage })` — ref type `React.MutableRefObject<string | null>` — matches AppTabs usage
- `HomeTab({ onSendToAgent })` — function type `(message: string) => void` — matches AppTabs call

**No placeholders:** All code blocks are complete and contain actual implementation.
