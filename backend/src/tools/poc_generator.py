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
