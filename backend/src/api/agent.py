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
