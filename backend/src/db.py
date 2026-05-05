import sqlite3
from contextlib import contextmanager
from datetime import datetime
import os
import re


# Main database for project metadata
# Directory for project-specific databases
PROJECTS_DB_DIR = 'projects_data'

# Ensure projects directory exists
os.makedirs(PROJECTS_DB_DIR, exist_ok=True)

# Main database is now also in projects_data
MAIN_DATABASE_PATH = os.path.join(PROJECTS_DB_DIR, 'oblivionsec.db')


def _migrate_moxy_db():
    """Rename moxy.db to oblivionsec.db on first run if it exists."""
    old_path = os.path.join(PROJECTS_DB_DIR, 'moxy.db')
    if os.path.exists(old_path) and not os.path.exists(MAIN_DATABASE_PATH):
        os.rename(old_path, MAIN_DATABASE_PATH)
        print("📦 Migrated moxy.db → oblivionsec.db")

_migrate_moxy_db()


def sanitize_filename(name):
    """Sanitize project name for use as filename"""
    # Replace spaces with underscores and remove special characters
    sanitized = re.sub(r'[^\w\s-]', '', name)
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    return sanitized.lower()


def get_project_db_path(project_name):
    """Get the database file path for a specific project using project name"""
    sanitized_name = sanitize_filename(project_name)
    return os.path.join(PROJECTS_DB_DIR, f'{sanitized_name}.db')


@contextmanager
def get_db(db_path=None):
    """Get database connection as context manager"""
    if db_path is None:
        db_path = MAIN_DATABASE_PATH
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_available_databases():
    """List all .db files in projects_data directory (excluding oblivionsec.db)"""
    if not os.path.exists(PROJECTS_DB_DIR):
        return []

    db_files = []
    for filename in os.listdir(PROJECTS_DB_DIR):
        if filename.endswith('.db') and filename != 'oblivionsec.db':
            filepath = os.path.join(PROJECTS_DB_DIR, filename)
            if os.path.isfile(filepath):
                # Extract project name from filename (remove .db extension)
                project_name = filename[:-3]  # Remove .db
                db_files.append({
                    'filename': filename,
                    'path': filepath,
                    'project_name': project_name,
                    'size': os.path.getsize(filepath)
                })
    return db_files


def import_project_database(file_path, project_name=None):
    """Import a database file into projects_data directory"""
    if not os.path.exists(file_path):
        raise ValueError(f"File not found: {file_path}")
    
    # If no project name provided, derive from filename
    if project_name is None:
        filename = os.path.basename(file_path)
        if filename.endswith('.db'):
            project_name = filename[:-3]
        else:
            project_name = filename
    
    # Sanitize project name for filename
    sanitized_name = sanitize_filename(project_name)
    target_path = os.path.join(PROJECTS_DB_DIR, f'{sanitized_name}.db')
    
    # Check if project with this name already exists
    existing_project = get_project_by_name(project_name)
    if existing_project:
        raise ValueError(f"Project with name '{project_name}' already exists")
    
    # Check if database file already exists
    if os.path.exists(target_path):
        raise ValueError(f"Database file '{sanitized_name}.db' already exists in projects_data")
    
    # Copy the file to projects_data
    import shutil
    shutil.copy2(file_path, target_path)
    
    # Create new project entry in main database
    # Project-specific databases don't have a projects table, so we create the entry here
    return create_project(name=project_name, description='')


def init_db():
    """Initialize the database with required tables"""
    # List available databases in projects_data for reference
    available_dbs = list_available_databases()
    if available_dbs:
        print(f"📁 Found {len(available_dbs)} database file(s) in projects_data:")
        for db_info in available_dbs:
            size_kb = db_info['size'] / 1024
            print(f"   - {db_info['filename']} ({size_kb:.1f} KB)")
        print("   You can import these by copying them to projects_data or using the import endpoint.")
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Create proxy_state table for storing proxy configuration
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxy_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')


def ensure_default_project():
    """Ensure there's at least one project and return the default project"""
    projects = get_all_projects()
    
    if not projects:
        # Create a default project
        project = create_project(
            name="Default Project",
            description="Default project created automatically"
        )
        return project
    
    # Return the first project as default
    return projects[0]


def get_all_projects():
    """Get all projects from database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM projects ORDER BY created_at DESC')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_project_by_id(project_id):
    """Get a project by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_project_by_name(name):
    """Get a project by name"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM projects WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def init_project_db(project_name):
    """Initialize a project-specific database with required tables"""
    db_path = get_project_db_path(project_name)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        # Create requests table for storing HTTP requests
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
        except Exception:
            # Column already exists, ignore
            pass
        # Add flow_id column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE requests ADD COLUMN flow_id TEXT')
        except Exception:
            # Column already exists, ignore
            pass
        
        # Create sessions table for organizing requests
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create resender_tabs table for resender tabs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resender_tabs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                host TEXT DEFAULT 'example.com',
                port TEXT DEFAULT '443',
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create filters table for storing request filters
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hide_static_assets INTEGER DEFAULT 0,
                excluded_hosts TEXT DEFAULT '[]',
                included_hosts TEXT DEFAULT '[]',
                methods TEXT DEFAULT '[]',
                status_codes TEXT DEFAULT '[]',
                text_search TEXT DEFAULT '',
                text_search_scope TEXT DEFAULT 'both',
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Create resender_versions table for storing request/response pairs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resender_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tab_id INTEGER NOT NULL,
                raw_request TEXT NOT NULL,
                raw_response TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (tab_id) REFERENCES resender_tabs(id) ON DELETE CASCADE
            )
        ''')
        
        # Create intercepted_flows table for storing intercepted flow IDs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intercepted_flows (
                flow_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # Create agent_chats table for storing chat conversations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Create agent_messages table for storing chat messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                step_type TEXT,
                tool_name TEXT,
                tool_input TEXT,
                tool_output TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES agent_chats(id) ON DELETE CASCADE
            )
        ''')


def create_project(name, description=''):
    """Create a new project and its dedicated database"""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO projects (name, description, created_at, updated_at) VALUES (?, ?, ?, ?)',
            (name, description, now, now)
        )
        project_id = cursor.lastrowid
    
    # Initialize the project-specific database using project name
    init_project_db(name)
    
    return get_project_by_id(project_id)


def update_project(project_id, name=None, description=None):
    """Update an existing project"""
    now = datetime.utcnow().isoformat()
    
    # Get current project to check if name is changing
    current_project = get_project_by_id(project_id)
    if not current_project:
        return None
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if name is not None and name != current_project['name']:
            # Rename the database file if name is changing
            old_db_path = get_project_db_path(current_project['name'])
            new_db_path = get_project_db_path(name)
            
            if os.path.exists(old_db_path):
                os.rename(old_db_path, new_db_path)
            
            updates.append('name = ?')
            params.append(name)
        
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        
        updates.append('updated_at = ?')
        params.append(now)
        params.append(project_id)
        
        query = f'UPDATE projects SET {", ".join(updates)} WHERE id = ?'
        cursor.execute(query, params)
        
        return get_project_by_id(project_id)


def delete_project(project_id):
    """Delete a project and its database file"""
    # Get project to find its database file
    project = get_project_by_id(project_id)
    if not project:
        return False
    
    # Delete the project-specific database file
    db_path = get_project_db_path(project['name'])
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Delete the project from main database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        return cursor.rowcount > 0


# ===== Project-specific database operations =====

def add_request_to_project(project_id, method, url, headers=None, body=None, 
                           response_status=None, response_headers=None, response_body=None):
    """Add an HTTP request to a project's database"""
    project = get_project_by_id(project_id)
    if not project:
        raise ValueError("Project not found")
    
    now = datetime.utcnow().isoformat()
    db_path = get_project_db_path(project['name'])
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO requests (method, url, headers, body, response_status, 
                                response_headers, response_body, timestamp, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (method, url, headers, body, response_status, response_headers, response_body, now, now))
        return cursor.lastrowid


def get_project_requests(project_id, limit=None, offset=None):
    """Get HTTP requests from a project's database with pagination"""
    project = get_project_by_id(project_id)
    if not project:
        return []
    
    db_path = get_project_db_path(project['name'])
    
    if not os.path.exists(db_path):
        return []
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        if limit is not None:
            if offset is not None:
                cursor.execute('SELECT * FROM requests ORDER BY timestamp DESC LIMIT ? OFFSET ?', (limit, offset))
            else:
                cursor.execute('SELECT * FROM requests ORDER BY timestamp DESC LIMIT ?', (limit,))
        else:
            cursor.execute('SELECT * FROM requests ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_project_requests_count(project_id):
    """Get total count of requests for a project"""
    project = get_project_by_id(project_id)
    if not project:
        return 0
    
    db_path = get_project_db_path(project['name'])
    
    if not os.path.exists(db_path):
        return 0
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM requests')
        row = cursor.fetchone()
        return row['count'] if row else 0


def get_project_request(project_id, request_id):
    """Get a specific request from a project's database"""
    project = get_project_by_id(project_id)
    if not project:
        return None
    
    db_path = get_project_db_path(project['name'])
    
    if not os.path.exists(db_path):
        return None
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM requests WHERE id = ?', (request_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_project_request(project_id, request_id):
    """Delete a request from a project's database"""
    project = get_project_by_id(project_id)
    if not project:
        return False
    
    db_path = get_project_db_path(project['name'])
    
    if not os.path.exists(db_path):
        return False
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM requests WHERE id = ?', (request_id,))
        return cursor.rowcount > 0


def clear_project_requests(project_id):
    """Clear all requests from a project's database"""
    project = get_project_by_id(project_id)
    if not project:
        return False
    
    db_path = get_project_db_path(project['name'])
    
    if not os.path.exists(db_path):
        return False
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM requests')
        return True


# ===== Resender operations =====

def create_resender_tab(project_id, name, host='example.com', port='443'):
    """Create a new resender tab in a project"""
    project = get_project_by_id(project_id)
    if not project:
        raise ValueError("Project not found")
    
    db_path = get_project_db_path(project['name'])
    now = datetime.utcnow().isoformat()
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO resender_tabs (name, host, port, created_at)
            VALUES (?, ?, ?, ?)
        ''', (name, host, port, now))
        return cursor.lastrowid


def get_resender_tabs(project_id):
    """Get all resender tabs for a project"""
    project = get_project_by_id(project_id)
    if not project:
        return []
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return []
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM resender_tabs ORDER BY created_at DESC')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_resender_tab(project_id, tab_id):
    """Get a specific resender tab"""
    project = get_project_by_id(project_id)
    if not project:
        return None
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return None
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM resender_tabs WHERE id = ?', (tab_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_resender_tab(project_id, tab_id, name=None, host=None, port=None):
    """Update a resender tab"""
    project = get_project_by_id(project_id)
    if not project:
        return None
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return None
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        
        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if host is not None:
            updates.append('host = ?')
            params.append(host)
        if port is not None:
            updates.append('port = ?')
            params.append(port)
        
        if not updates:
            return get_resender_tab(project_id, tab_id)
        
        params.append(tab_id)
        query = f'UPDATE resender_tabs SET {", ".join(updates)} WHERE id = ?'
        cursor.execute(query, params)
        return get_resender_tab(project_id, tab_id)


def delete_resender_tab(project_id, tab_id):
    """Delete a resender tab (cascades to versions)"""
    project = get_project_by_id(project_id)
    if not project:
        return False
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return False
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM resender_tabs WHERE id = ?', (tab_id,))
        return cursor.rowcount > 0


def create_resender_version(project_id, tab_id, raw_request, raw_response=None):
    """Create a new request/response version for a tab"""
    project = get_project_by_id(project_id)
    if not project:
        raise ValueError("Project not found")
    
    db_path = get_project_db_path(project['name'])
    now = datetime.utcnow().isoformat()
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO resender_versions (tab_id, raw_request, raw_response, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (tab_id, raw_request, raw_response, now))
        return cursor.lastrowid


def get_resender_versions(project_id, tab_id):
    """Get all versions for a resender tab"""
    project = get_project_by_id(project_id)
    if not project:
        return []
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return []
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM resender_versions 
            WHERE tab_id = ? 
            ORDER BY timestamp ASC
        ''', (tab_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_resender_version(project_id, tab_id, version_id):
    """Get a specific version"""
    project = get_project_by_id(project_id)
    if not project:
        return None
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return None
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM resender_versions 
            WHERE id = ? AND tab_id = ?
        ''', (version_id, tab_id))
        row = cursor.fetchone()
        return dict(row) if row else None


# ===== Proxy State Operations (Main Database) =====

def get_proxy_state(key, default=None):
    """Get a proxy state value from the main database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM proxy_state WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row['value'] if row else default


def set_proxy_state(key, value):
    """Set a proxy state value in the main database"""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO proxy_state (key, value, updated_at)
            VALUES (?, ?, ?)
        ''', (key, value, now))


def get_all_proxy_state():
    """Get all proxy state as a dictionary"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM proxy_state')
        rows = cursor.fetchall()
        return {row['key']: row['value'] for row in rows}


# ===== Intercepted Flows Operations (Project Database) =====

def get_intercepted_flows(project_name):
    """Get all intercepted flow IDs for a project"""
    if not project_name:
        return []
    
    db_path = get_project_db_path(project_name)
    if not os.path.exists(db_path):
        return []
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT flow_id FROM intercepted_flows ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        return [row['flow_id'] for row in rows]


def add_intercepted_flow(project_name, flow_id):
    """Add an intercepted flow ID"""
    if not project_name:
        return False
    
    db_path = get_project_db_path(project_name)
    if not os.path.exists(db_path):
        return False
    
    now = datetime.utcnow().isoformat()
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO intercepted_flows (flow_id, timestamp)
            VALUES (?, ?)
        ''', (flow_id, now))
        return True


def remove_intercepted_flow(project_name, flow_id):
    """Remove an intercepted flow"""
    if not project_name:
        return False
    
    db_path = get_project_db_path(project_name)
    if not os.path.exists(db_path):
        return False
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM intercepted_flows WHERE flow_id = ?', (flow_id,))
        return cursor.rowcount > 0


def clear_intercepted_flows(project_name):
    """Clear all intercepted flows for a project"""
    if not project_name:
        return False
    
    db_path = get_project_db_path(project_name)
    if not os.path.exists(db_path):
        return False
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM intercepted_flows')
        return True


# ===== Agent Chat Operations (Project Database) =====

def create_agent_chat(project_id, title=None):
    """Create a new agent chat"""
    project = get_project_by_id(project_id)
    if not project:
        raise ValueError("Project not found")
    
    db_path = get_project_db_path(project['name'])
    now = datetime.utcnow().isoformat()
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO agent_chats (title, created_at, updated_at)
            VALUES (?, ?, ?)
        ''', (title or "New Chat", now, now))
        return cursor.lastrowid


def get_agent_chats(project_id):
    """Get all agent chats for a project"""
    project = get_project_by_id(project_id)
    if not project:
        return []
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return []
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM agent_chats 
            ORDER BY updated_at DESC
        ''')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_agent_chat(project_id, chat_id):
    """Get a specific agent chat"""
    project = get_project_by_id(project_id)
    if not project:
        return None
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return None
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM agent_chats WHERE id = ?', (chat_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_agent_chat(project_id, chat_id, title=None):
    """Update an agent chat"""
    project = get_project_by_id(project_id)
    if not project:
        return None
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return None
    
    now = datetime.utcnow().isoformat()
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        if title is not None:
            cursor.execute('''
                UPDATE agent_chats 
                SET title = ?, updated_at = ?
                WHERE id = ?
            ''', (title, now, chat_id))
        else:
            cursor.execute('''
                UPDATE agent_chats 
                SET updated_at = ?
                WHERE id = ?
            ''', (now, chat_id))
        return get_agent_chat(project_id, chat_id)


def delete_agent_chat(project_id, chat_id):
    """Delete an agent chat (cascades to messages)"""
    project = get_project_by_id(project_id)
    if not project:
        return False
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return False
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM agent_chats WHERE id = ?', (chat_id,))
        return cursor.rowcount > 0


def add_agent_message(project_id, chat_id, role, content, step_type=None, tool_name=None, tool_input=None, tool_output=None):
    """Add a message to an agent chat"""
    project = get_project_by_id(project_id)
    if not project:
        raise ValueError("Project not found")
    
    db_path = get_project_db_path(project['name'])
    now = datetime.utcnow().isoformat()
    
    import json
    tool_input_json = json.dumps(tool_input) if tool_input is not None else None
    tool_output_json = json.dumps(tool_output) if tool_output is not None else None
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO agent_messages (chat_id, role, content, step_type, tool_name, tool_input, tool_output, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (chat_id, role, content, step_type, tool_name, tool_input_json, tool_output_json, now))
        message_id = cursor.lastrowid
        
        # Update chat's updated_at timestamp in the same transaction
        cursor.execute('''
            UPDATE agent_chats 
            SET updated_at = ?
            WHERE id = ?
        ''', (now, chat_id))
        
        return message_id


def save_project_filters(project_id, filters):
    """Save request filters for a project"""
    project = get_project_by_id(project_id)
    if not project:
        raise ValueError("Project not found")
    
    db_path = get_project_db_path(project['name'])
    now = datetime.utcnow().isoformat()
    
    import json
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        # Check if filters row exists
        cursor.execute('SELECT id FROM filters LIMIT 1')
        existing = cursor.fetchone()
        
        excluded_hosts_json = json.dumps(filters.get('excludedHosts', []))
        included_hosts_json = json.dumps(filters.get('includedHosts', []))
        methods_json = json.dumps(filters.get('methods', []))
        status_codes_json = json.dumps(filters.get('statusCodes', []))
        
        if existing:
            # Update existing row
            cursor.execute('''
                UPDATE filters SET
                    hide_static_assets = ?,
                    excluded_hosts = ?,
                    included_hosts = ?,
                    methods = ?,
                    status_codes = ?,
                    text_search = ?,
                    text_search_scope = ?,
                    updated_at = ?
            ''', (
                int(filters.get('hideStaticAssets', False)),
                excluded_hosts_json,
                included_hosts_json,
                methods_json,
                status_codes_json,
                filters.get('textSearch', ''),
                filters.get('textSearchScope', 'both'),
                now
            ))
        else:
            # Insert new row
            cursor.execute('''
                INSERT INTO filters (
                    hide_static_assets, excluded_hosts, included_hosts,
                    methods, status_codes, text_search, text_search_scope, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                int(filters.get('hideStaticAssets', False)),
                excluded_hosts_json,
                included_hosts_json,
                methods_json,
                status_codes_json,
                filters.get('textSearch', ''),
                filters.get('textSearchScope', 'both'),
                now
            ))


def get_project_filters(project_id):
    """Get request filters for a project"""
    project = get_project_by_id(project_id)
    if not project:
        return None
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return None
    
    import json
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM filters LIMIT 1')
        row = cursor.fetchone()
        
        if not row:
            return None
        
        filters_dict = dict(row)
        return {
            'hideStaticAssets': bool(filters_dict.get('hide_static_assets', False)),
            'excludedHosts': json.loads(filters_dict.get('excluded_hosts', '[]')),
            'includedHosts': json.loads(filters_dict.get('included_hosts', '[]')),
            'methods': json.loads(filters_dict.get('methods', '[]')),
            'statusCodes': json.loads(filters_dict.get('status_codes', '[]')),
            'textSearch': filters_dict.get('text_search', ''),
            'textSearchScope': filters_dict.get('text_search_scope', 'both')
        }


def get_agent_messages(project_id, chat_id):
    """Get all messages for an agent chat"""
    project = get_project_by_id(project_id)
    if not project:
        return []
    
    db_path = get_project_db_path(project['name'])
    if not os.path.exists(db_path):
        return []
    
    import json
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM agent_messages 
            WHERE chat_id = ? 
            ORDER BY created_at ASC
        ''', (chat_id,))
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            msg = dict(row)
            if msg['tool_input']:
                try:
                    msg['tool_input'] = json.loads(msg['tool_input'])
                except:
                    pass
            if msg['tool_output']:
                try:
                    msg['tool_output'] = json.loads(msg['tool_output'])
                except:
                    pass
            messages.append(msg)
        return messages
