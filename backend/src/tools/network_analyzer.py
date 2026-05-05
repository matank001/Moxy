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
