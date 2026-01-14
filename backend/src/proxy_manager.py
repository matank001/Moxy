"""
Proxy management for mitmproxy
"""

import subprocess
import os
import signal
import sys
from pathlib import Path
import json
from . import db

# Global proxy process
_proxy_process = None
_proxy_port = 8081


def save_active_project(project_name):
    """Save the active project name to the database"""
    db.set_proxy_state('active_project', project_name if project_name else '')


def get_intercept_enabled():
    """Get intercept state from database"""
    try:
        value = db.get_proxy_state('intercept_enabled', 'false')
        return value.lower() == 'true'
    except Exception:
        return False


def set_intercept_enabled(enabled):
    """Set intercept state in database"""
    try:
        db.set_proxy_state('intercept_enabled', 'true' if enabled else 'false')
        
        # If disabling intercept, set forward_all flag to forward all queued requests
        if not enabled:
            db.set_proxy_state('forward_all', 'true')
        
        return True
    except Exception as e:
        print(f"Error setting intercept state: {e}", file=sys.stderr)
        return False


def get_intercepted_flows():
    """Get list of intercepted flow IDs from the database"""
    try:
        # Get active project name
        project_name = db.get_proxy_state('active_project')
        if not project_name:
            return []
        
        # Returns just a list of flow IDs
        return db.get_intercepted_flows(project_name)
    except Exception as e:
        print(f"Error getting intercepted flows: {e}", file=sys.stderr)
        return []


def forward_intercepted_flow(flow_id, edited_request=None):
    """Forward a specific intercepted flow"""
    try:
        # Get current forward flows list
        forward_flows_json = db.get_proxy_state('forward_flows', '[]')
        try:
            forward_flows = json.loads(forward_flows_json) if forward_flows_json else []
        except:
            forward_flows = []
        
        # Add flow to forward list
        flow_id_str = str(flow_id)
        if flow_id_str not in forward_flows:
            forward_flows.append(flow_id_str)
            db.set_proxy_state('forward_flows', json.dumps(forward_flows))
        
        # Store edited request if provided
        if edited_request:
            edited_requests_json = db.get_proxy_state('edited_requests', '{}')
            try:
                edited_requests = json.loads(edited_requests_json) if edited_requests_json else {}
            except:
                edited_requests = {}
            
            edited_requests[flow_id_str] = edited_request
            db.set_proxy_state('edited_requests', json.dumps(edited_requests))
        
        return True
    except Exception as e:
        print(f"Error forwarding intercepted flow: {e}", file=sys.stderr)
        return False


def drop_intercepted_flow(flow_id):
    """Drop a specific intercepted flow (kill it without forwarding)"""
    try:
        # Get current drop flows list
        drop_flows_json = db.get_proxy_state('drop_flows', '[]')
        try:
            drop_flows = json.loads(drop_flows_json) if drop_flows_json else []
        except:
            drop_flows = []
        
        # Add flow to drop list
        flow_id_str = str(flow_id)
        if flow_id_str not in drop_flows:
            drop_flows.append(flow_id_str)
            db.set_proxy_state('drop_flows', json.dumps(drop_flows))
        
        return True
    except Exception as e:
        print(f"Error dropping intercepted flow: {e}", file=sys.stderr)
        return False


def start_proxy():
    """Start the mitmproxy process"""
    global _proxy_process
    
    if _proxy_process is not None:
        print("⚠️  Proxy is already running", file=sys.stderr)
        return True
    
    try:
        # Get the path to addon.py
        addon_path = Path(__file__).parent / 'addon.py'
        
        # Set up log files
        log_dir = 'projects_data'
        stdout_log = Path(log_dir) / 'mitmproxy_stdout.log'
        
        # Open log files
        stdout_file = open(stdout_log, 'w')
        
        # Start mitmdump process with verbose logging
        # Set stream_large_bodies=0 to disable streaming and capture full bodies (0 = never stream)
        # block_global=false allows connections from non-localhost IPs (needed for Docker/remote access)
        _proxy_process = subprocess.Popen(
            [
                'mitmdump',
                '-s', str(addon_path),
                '-p', str(_proxy_port),
                '--set', 'termlog_verbosity=info',  # Debug level logging
                '--set', 'block_global=false',  # Allow connections from non-localhost IPs
            ],
            stdout=stdout_file,
            cwd=Path(__file__).parent,
            env={**os.environ, 'PYTHONPATH': str(Path(__file__).parent)}
        )
        
        # Store file handles for cleanup
        _proxy_process._stdout_file = stdout_file
        
        print(f"✅ Proxy started on port {_proxy_port} (PID: {_proxy_process.pid})", file=sys.stderr)
        print(f"📝 Logs: {stdout_log}", file=sys.stderr)
        return True
    except FileNotFoundError:
        print("", file=sys.stderr)
        print("   Note: Do NOT use standalone mitmproxy binary - it lacks sqlite3", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error starting proxy: {e}", file=sys.stderr)
        return False


def stop_proxy():
    """Stop the mitmproxy process"""
    global _proxy_process
    
    if _proxy_process is None:
        print("⚠️  Proxy is not running", file=sys.stderr)
        return True
    
    try:
        # Send SIGTERM to gracefully shutdown
        _proxy_process.terminate()
        
        # Wait for process to terminate (with timeout)
        try:
            _proxy_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't terminate
            _proxy_process.kill()
            _proxy_process.wait()
        
        # Close log files
        if hasattr(_proxy_process, '_stdout_file'):
            _proxy_process._stdout_file.close()
        
        print(f"✅ Proxy stopped", file=sys.stderr)
        _proxy_process = None
        return True
    except Exception as e:
        print(f"❌ Error stopping proxy: {e}", file=sys.stderr)
        return False


def is_proxy_running():
    """Check if the proxy is currently running"""
    global _proxy_process
    
    if _proxy_process is None:
        return False
    
    # Check if process is still alive
    if _proxy_process.poll() is not None:
        # Process has terminated
        _proxy_process = None
        return False
    
    return True


def get_proxy_port():
    """Get the proxy port"""
    return _proxy_port


def cleanup_proxy():
    """Cleanup function to be called on application shutdown"""
    if is_proxy_running():
        print("🧹 Cleaning up proxy process...", file=sys.stderr)
        stop_proxy()
