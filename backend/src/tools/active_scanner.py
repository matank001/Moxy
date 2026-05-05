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
