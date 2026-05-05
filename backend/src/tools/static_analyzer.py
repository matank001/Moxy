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

    patterns_to_run = ALL_PATTERNS
    if scope == "js":
        patterns_to_run = JS_SINK_PATTERNS
    elif scope == "headers":
        patterns_to_run = []
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
