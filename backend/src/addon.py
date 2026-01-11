"""
Mitmproxy addon to capture HTTP requests and responses and store them in the project database.
"""

from mitmproxy.net.http.http1.assemble import assemble_request, assemble_response
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from mitmproxy import http
import sqlite3
from pathlib import Path

# Add parent directory to path to import db module
# When run by mitmproxy, this script is executed standalone, not as a package
addon_dir = Path(__file__).parent
sys.path.insert(0, str(addon_dir))
import db

# Set the database path to be in the parent directory (backend/)
# since mitmproxy runs with cwd=src/, but the database is in backend/
backend_dir = addon_dir.parent
db.MAIN_DATABASE_PATH = str(backend_dir / 'puke.db')
db.PROJECTS_DB_DIR = str(backend_dir / 'projects_data')

# Configure logging to file
log_file = Path(__file__).parent / 'proxy.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
    ]
)
logger = logging.getLogger(__name__)


class ProxyRecorder:
    def __init__(self):
        """Initialize the proxy recorder"""
        self.active_project_name = self._get_active_project()
        # Store request IDs for updating with responses
        self.request_map = {}  # flow.id -> db_request_id
        # Store intercepted flows waiting for user action
        self.intercepted_flows = {}  # flow.id -> flow
        # Start background thread for periodic checks (tick doesn't work in mitmdump mode)
        self._stop_thread = False
        self._check_thread = threading.Thread(target=self._periodic_check, daemon=True)
        self._check_thread.start()
        logger.info(f"ProxyRecorder initialized for project: {self.active_project_name}")
    
    def _periodic_check(self):
        """Background thread to periodically check for forward commands"""
        while not self._stop_thread:
            try:
                # Check every 100ms (same as tick would be)
                time.sleep(0.1)
                self._check_forward_commands()
                
                # Also check if intercept was disabled and we still have flows to forward
                if self.intercepted_flows:
                    intercept_enabled = self._get_intercept_enabled()
                    if not intercept_enabled:
                        # Intercept was disabled but we still have flows - forward them immediately
                        self._forward_all_intercepted()
                        self._save_intercepted_flows_info()
                
                # Sync intercepted flows from memory to database periodically
                if self.intercepted_flows and self.active_project_name:
                    self._save_intercepted_flows_info()
            except Exception as e:
                logger.error(f"Error in periodic check thread: {e}")
    
    def _get_active_project(self):
        """Get the active project name from database"""
        try:
            # Ensure database is initialized (in case addon loads before Flask app)
            db.init_db()
            return db.get_proxy_state('active_project')
        except Exception as e:
            logger.error(f"Error reading active project from database: {e}")
            return None
    
    def _get_intercept_enabled(self):
        """Get intercept state from database"""
        try:
            value = db.get_proxy_state('intercept_enabled', 'false')
            return value.lower() == 'true'
        except Exception as e:
            logger.error(f"Error reading intercept state from database: {e}")
            return False
    
    def _save_intercepted_flows_info(self):
        """Save intercepted flows to database (only flow IDs)"""
        if not self.active_project_name:
            return
        
        try:
            # First, clear all existing intercepted flows for this project
            db.clear_intercepted_flows(self.active_project_name)
            
            # Then, save all current intercepted flow IDs
            for flow_id in list(self.intercepted_flows.keys()):
                db.add_intercepted_flow(self.active_project_name, flow_id)
        except Exception as e:
            logger.error(f"Error saving intercepted flows to database: {e}")
    
    def _check_forward_commands(self):
        """Check for forward commands from API via database"""
        try:
            # Check for forward_all command
            forward_all = db.get_proxy_state('forward_all', 'false')
            if forward_all.lower() == 'true':
                self._forward_all_intercepted()
                db.set_proxy_state('forward_all', 'false')
                return
            
            # Check for individual flow drop commands first (so they take precedence)
            drop_flows_json = db.get_proxy_state('drop_flows', '[]')
            try:
                drop_flows = json.loads(drop_flows_json) if drop_flows_json else []
            except:
                drop_flows = []
            
            if drop_flows:
                flows_dropped = False
                for flow_id_str in drop_flows:
                    try:
                        flow_id = flow_id_str if isinstance(flow_id_str, str) else str(flow_id_str)
                        # Find flow by ID (mitmproxy uses string IDs)
                        flow = self.intercepted_flows.get(flow_id)
                        if flow:
                            # Kill the flow (drop it)
                            flow.kill()
                            del self.intercepted_flows[flow_id]
                            # Remove from database
                            db.remove_intercepted_flow(self.active_project_name, flow_id)
                            flows_dropped = True
                            logger.info(f"Dropped intercepted flow {flow_id}: {flow.request.method} {flow.request.pretty_url}")
                    except Exception as e:
                        logger.error(f"Error dropping flow {flow_id_str}: {e}")
                
                # Save intercepted flows info immediately if any were dropped
                if flows_dropped:
                    self._save_intercepted_flows_info()
                
                # Clear drop commands
                db.set_proxy_state('drop_flows', '[]')
            
            # Check for individual flow forward commands
            forward_flows_json = db.get_proxy_state('forward_flows', '[]')
            try:
                forward_flows = json.loads(forward_flows_json) if forward_flows_json else []
            except:
                forward_flows = []
            
            if forward_flows:
                flows_forwarded = False
                edited_requests_json = db.get_proxy_state('edited_requests', '{}')
                try:
                    edited_requests = json.loads(edited_requests_json) if edited_requests_json else {}
                except:
                    edited_requests = {}
                
                for flow_id_str in forward_flows:
                    try:
                        flow_id = flow_id_str if isinstance(flow_id_str, str) else str(flow_id_str)
                        # Find flow by ID (mitmproxy uses string IDs)
                        flow = self.intercepted_flows.get(flow_id)
                        if flow:
                            # Check if there's an edited request
                            edited_request = edited_requests.get(flow_id)
                            if edited_request:
                                # Parse and apply edited request
                                try:
                                    # This is a simplified approach - in production you'd want proper HTTP parsing
                                    # For now, we'll just resume with the original request
                                    # TODO: Implement proper request editing
                                    logger.info(f"Forwarding flow {flow_id} with edited request (editing not fully implemented)")
                                except Exception as e:
                                    logger.error(f"Error applying edited request to flow {flow_id}: {e}")
                            
                            # Forward the flow
                            flow.resume()
                            del self.intercepted_flows[flow_id]
                            # Remove from database
                            db.remove_intercepted_flow(self.active_project_name, flow_id)
                            flows_forwarded = True
                            logger.info(f"Forwarded intercepted flow {flow_id}: {flow.request.method} {flow.request.pretty_url}")
                    except Exception as e:
                        logger.error(f"Error forwarding flow {flow_id_str}: {e}")
                
                # Save intercepted flows info immediately if any were forwarded
                if flows_forwarded:
                    self._save_intercepted_flows_info()
                
                # Clear forward commands
                db.set_proxy_state('forward_flows', '[]')
                # Clean up edited requests for forwarded flows
                for flow_id_str in forward_flows:
                    edited_requests.pop(flow_id_str, None)
                db.set_proxy_state('edited_requests', json.dumps(edited_requests))
        except Exception as e:
            logger.error(f"Error checking forward commands: {e}")
    
    def _forward_all_intercepted(self):
        """Forward all intercepted flows when intercept is disabled"""
        flows_to_forward = list(self.intercepted_flows.values())
        self.intercepted_flows.clear()
        
        # Save immediately after clearing to update the file
        self._save_intercepted_flows_info()
        
        for flow in flows_to_forward:
            try:
                # Resume the flow to forward it
                flow.resume()
                logger.info(f"Auto-forwarded intercepted flow {flow.id}: {flow.request.method} {flow.request.pretty_url}")
            except Exception as e:
                logger.error(f"Error forwarding flow {flow.id}: {e}")
    
    def _get_project_db_path(self, project_name):
        """Get the database path for a project"""
        if not project_name:
            return None
        # Use the same path logic as the main db module
        # This ensures we use the backend/projects_data directory, not src/projects_data
        return db.get_project_db_path(project_name)
    
    def _ensure_table(self, cursor):
        """Ensure the requests table exists with proper schema"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                raw_request TEXT,
                raw_response TEXT,
                status_code INTEGER,
                duration_ms INTEGER,
                timestamp TEXT NOT NULL,
                completed_at TEXT,
                flow_id TEXT
            )
        ''')
        # Add status_code column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE requests ADD COLUMN status_code INTEGER')
        except sqlite3.OperationalError:
            # Column already exists, ignore
            pass
        # Add flow_id column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE requests ADD COLUMN flow_id TEXT')
        except sqlite3.OperationalError:
            # Column already exists, ignore
            pass
    
    def _save_request(self, flow: http.HTTPFlow):
        """Save request immediately when it's sent"""
        if not self.active_project_name:
            logger.debug("No active project, skipping request save")
            return None
        
        db_path = self._get_project_db_path(self.active_project_name)
        if not db_path:
            return None
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            self._ensure_table(cursor)
            
            # Extract basic info for indexing
            method = flow.request.method
            url = flow.request.pretty_url
            
            # Capture raw HTTP request
            try:
                raw_request_bytes = assemble_request(flow.request)
                raw_request = raw_request_bytes.decode('utf-8', errors='replace')
            except Exception as e:
                logger.warning(f"Could not assemble request: {e}", exc_info=True)
                raw_request = None
            
            # Insert the request (without response data yet)
            now = datetime.utcnow().isoformat()
            flow_id_str = str(flow.id)
            cursor.execute('''
                INSERT INTO requests (
                    method, url, raw_request, timestamp, flow_id
                )
                VALUES (?, ?, ?, ?, ?)
            ''', (method, url, raw_request, now, flow_id_str))
            
            request_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded request {request_id}: {method} {url}")
            return request_id
            
        except Exception as e:
            logger.error(f"Error saving request: {e}", exc_info=True)
            return None
    
    def _update_with_response(self, request_id, flow: http.HTTPFlow, duration_ms):
        """Update the request record with response data"""
        if not self.active_project_name:
            return
        
        db_path = self._get_project_db_path(self.active_project_name)
        if not db_path:
            return
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Capture raw HTTP response
            try:
                raw_response_bytes = assemble_response(flow.response)
                raw_response = raw_response_bytes.decode('utf-8', errors='replace')
            except Exception as e:
                logger.warning(f"Could not assemble response: {e}", exc_info=True)
                raw_response = None
            
            # Extract status code
            status_code = flow.response.status_code if flow.response else None
            
            # Update the request with response data
            completed_at = datetime.utcnow().isoformat()
            cursor.execute('''
                UPDATE requests 
                SET raw_response = ?,
                    status_code = ?,
                    duration_ms = ?,
                    completed_at = ?
                WHERE id = ?
            ''', (raw_response, status_code, duration_ms, completed_at, request_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated request {request_id} with response: {status_code} ({duration_ms}ms)")
            
        except Exception as e:
            logger.error(f"Error updating response: {e}", exc_info=True)
    
    def requestheaders(self, flow: http.HTTPFlow):
        """Called when request headers are received (before body)"""
        # Check for forward commands periodically
        self._check_forward_commands()
        
        # Check if project has changed
        new_project = self._get_active_project()
        if new_project != self.active_project_name:
            self.active_project_name = new_project
            logger.info(f"Switched to project: {self.active_project_name}")
            # Clear old intercepted flows when project changes
            if self.intercepted_flows:
                self.intercepted_flows.clear()
                self._save_intercepted_flows_info()
    
    def request(self, flow: http.HTTPFlow):
        """Called when request is complete (headers + body)"""
        # Check if project has changed
        new_project = self._get_active_project()
        if new_project != self.active_project_name:
            self.active_project_name = new_project
            logger.info(f"Switched to project: {self.active_project_name}")
            # Clear old intercepted flows when project changes
            if self.intercepted_flows:
                self.intercepted_flows.clear()
                self._save_intercepted_flows_info()
        
        # Check intercept state
        intercept_enabled = self._get_intercept_enabled()
        
        # Check for forward commands
        self._check_forward_commands()
        
        if intercept_enabled:
            # Intercept is ON - stop the flow and wait for user action
            flow.intercept()
            self.intercepted_flows[str(flow.id)] = flow
            self._save_intercepted_flows_info()
            logger.info(f"Intercepted request {flow.id}: {flow.request.method} {flow.request.pretty_url}")
        else:
            # Intercept is OFF - forward all queued flows first
            if self.intercepted_flows:
                self._forward_all_intercepted()
                self._save_intercepted_flows_info()
        
        # Save the request - body should be available now
        request_id = self._save_request(flow)
        if request_id:
            # Store the mapping so we can update it when response arrives
            self.request_map[flow.id] = request_id
            # Store the timestamp for duration calculation
            flow.metadata['request_timestamp'] = datetime.utcnow()
    
    def response(self, flow: http.HTTPFlow):
        """Called when a response is received"""
        try:
            # Remove from intercepted flows if it was intercepted
            flow_id_str = str(flow.id)
            if flow_id_str in self.intercepted_flows:
                del self.intercepted_flows[flow_id_str]
                db.remove_intercepted_flow(self.active_project_name, flow_id_str)
                self._save_intercepted_flows_info()
            
            # Calculate duration
            if 'request_timestamp' in flow.metadata:
                duration = datetime.utcnow() - flow.metadata['request_timestamp']
                duration_ms = int(duration.total_seconds() * 1000)
            else:
                duration_ms = None
            
            # Get the request ID we saved earlier
            request_id = self.request_map.get(flow.id)
            if request_id:
                # Update the request with response data
                self._update_with_response(request_id, flow, duration_ms)
                # Clean up the mapping
                del self.request_map[flow.id]
            
        except Exception as e:
            logger.error(f"Error processing response: {e}", exc_info=True)
    
    def error(self, flow: http.HTTPFlow):
        """Called when an error occurs"""
        try:
            # Remove from intercepted flows if it was intercepted
            flow_id_str = str(flow.id)
            if flow_id_str in self.intercepted_flows:
                del self.intercepted_flows[flow_id_str]
                db.remove_intercepted_flow(self.active_project_name, flow_id_str)
                self._save_intercepted_flows_info()
            
            # Log the error
            request_id = self.request_map.get(flow.id)
            if request_id:
                logger.warning(f"Request {request_id} failed: {flow.error}")
                # Clean up the mapping
                del self.request_map[flow.id]
        except Exception as e:
            logger.error(f"Error handling error: {e}", exc_info=True)
    
    def tick(self):
        """Called periodically by mitmproxy (if available) - but tick doesn't work in mitmdump mode"""
        # Note: tick() is not called in mitmdump (non-interactive) mode
        # We use a background thread instead (see _periodic_check)
        pass


# Create the addon instance
addons = [ProxyRecorder()]
