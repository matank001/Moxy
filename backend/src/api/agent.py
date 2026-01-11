"""
API endpoints for agent functionality using OpenAI Responses API.
"""
from flask import Blueprint, request, jsonify
from openai import OpenAI
from .. import db, state, http_sender, proxy_manager, browser_manager
import json
import logging
import os
import re
import asyncio
from browser_use import Agent as BrowserAgent, ChatOpenAI

logger = logging.getLogger(__name__)

agent_bp = Blueprint('agent', __name__)

# Initialize OpenAI client
client = None
def get_openai_client():
    global client
    if client is None:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        client = OpenAI(api_key=api_key)
    return client


def query_database(sql_query: str) -> dict:
    """
    Execute a SQL query against the requests database.
    
    Database schema (requests table):
    - id: INTEGER PRIMARY KEY - Unique request ID
    - method: TEXT NOT NULL - HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
    - url: TEXT NOT NULL - Full URL including path (e.g., "https://example.com/api/users")
    - raw_request: TEXT - Full HTTP request as string
    - raw_response: TEXT - Full HTTP response as string
    - status_code: INTEGER - HTTP response status code (200, 404, 500, etc.)
    - duration_ms: INTEGER - Request duration in milliseconds
    - timestamp: TEXT NOT NULL - Request timestamp in ISO format (e.g., "2024-01-01T12:00:00")
    - completed_at: TEXT - Response completion timestamp in ISO format
    - flow_id: TEXT - Proxy flow identifier
    
    Examples:
    - SELECT * FROM requests WHERE method = 'GET' ORDER BY timestamp DESC LIMIT 10
    - SELECT * FROM requests WHERE url LIKE '%login%' ORDER BY timestamp DESC LIMIT 5
    - SELECT * FROM requests WHERE status_code = 404 ORDER BY timestamp DESC
    - SELECT * FROM requests WHERE method = 'POST' AND url LIKE '%api%' ORDER BY timestamp ASC LIMIT 1
    
    Args:
        sql_query: SQL SELECT query to execute (only SELECT queries allowed)
    
    Returns:
        A dict containing the query results: {"count": int, "requests": [...]}
    """
    try:
        project_id = state.get_current_project()
        if not project_id:
            return {"error": "No current project selected"}
        
        project = db.get_project_by_id(project_id)
        if not project:
            return {"error": "Project not found"}
        
        db_path = db.get_project_db_path(project['name'])
        if not os.path.exists(db_path):
            return {"count": 0, "requests": []}
        
        # Security: Only allow SELECT queries
        sql_query_upper = sql_query.strip().upper()
        if not sql_query_upper.startswith('SELECT'):
            return {"error": "Only SELECT queries are allowed"}
        
        # Use SQLite to execute query
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            
            # Convert rows to dicts
            result = [dict(row) for row in rows]
            
            return {
                "count": len(result),
                "requests": result
            }
        except sqlite3.Error as e:
            logger.error(f"SQL error: {e}")
            return {"error": f"SQL error: {str(e)}"}
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error querying database: {e}", exc_info=True)
        return {"error": str(e)}


def send_request(raw_request: str, host: str = 'example.com', port: str = '443', use_https: bool = None) -> dict:
    """
    Send a raw HTTP request to a specified host.
    
    This function parses a raw HTTP request string and sends it to the specified host and port,
    similar to the resender functionality.
    
    Args:
        raw_request: Raw HTTP request string (e.g., "GET /api/users HTTP/1.1\\nHost: example.com\\n\\n")
        host: Target host (default: 'example.com')
        port: Target port (default: '443')
        use_https: Whether to use HTTPS (default: None, auto-determined from port - True unless port is '80')
    
    Returns:
        A dict containing the response: {
            "status_code": int,
            "headers": dict,
            "raw_response": str,
            "error": str (optional)
        }
    """
    try:
        # Auto-determine HTTPS if not specified
        if use_https is None:
            use_https = port != '80'
        
        # Send the request using http_sender
        result = http_sender.send_raw_http_request(raw_request, host, port, use_https)
        
        return result
    except Exception as e:
        logger.error(f"Error sending request: {e}", exc_info=True)
        return {
            "status_code": 0,
            "headers": {},
            "raw_response": f"Error: {str(e)}",
            "error": str(e)
        }


async def _browse_async(task: str, additional_tasks: list = None) -> dict:
    """
    Async helper function to browse using browser-use Agent.
    
    Args:
        task: Initial task for the browser agent
        additional_tasks: Optional list of additional tasks to execute
    
    Returns:
        A dict with the result: {"status": "success", "message": str, "error": str (optional)}
    """
    try:
        # Ensure proxy is running
        if not proxy_manager.is_proxy_running():
            logger.info("Proxy not running, starting proxy...")
            if not proxy_manager.start_proxy():
                return {"status": "error", "error": "Failed to start proxy"}
            # Wait a bit for proxy to start
            await asyncio.sleep(2)
        
        # Get or create browser session
        browser = await browser_manager.get_or_create_browser()
        
        # Create Agent with browser session and LLM
        llm = ChatOpenAI(model="gpt-5-mini")
        agent = BrowserAgent(
            task=task,
            browser_session=browser,
            llm=llm
        )
        
        # Run the initial task
        result = await agent.run()
        
        # Execute additional tasks if provided
        if additional_tasks:
            for additional_task in additional_tasks:
                agent.add_new_task(additional_task)
                result = await agent.run()
        
        return {
            "status": "success",
            "message": f"Completed task: {task}",
            "result": str(result) if result else "Task completed successfully"
        }
    except Exception as e:
        logger.error(f"Error browsing: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def browse(task: str, additional_tasks: list = None) -> dict:
    """
    Browse using browser-use Agent.
    
    This function ensures the proxy is running, gets or creates a browser session,
    and uses the Agent from browser_use to execute browsing tasks.
    
    Args:
        task: Initial task description (e.g., "search for dogs")
        additional_tasks: Optional list of additional tasks to execute sequentially
    
    Returns:
        A dict with the result: {"status": "success", "message": str, "error": str (optional)}
    """
    try:
        # Run async function in new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_browse_async(task, additional_tasks))
        finally:
            loop.close()
        return result
    except Exception as e:
        logger.error(f"Error running browse: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@agent_bp.route('/chats', methods=['GET'])
def get_chats():
    """Get all chats for the current project"""
    try:
        project_id = state.get_current_project()
        if not project_id:
            return jsonify({'error': 'No current project selected'}), 400
        
        chats = db.get_agent_chats(project_id)
        return jsonify(chats), 200
    except Exception as e:
        logger.error(f"Error getting chats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/chats', methods=['POST'])
def create_chat():
    """Create a new chat"""
    try:
        project_id = state.get_current_project()
        if not project_id:
            return jsonify({'error': 'No current project selected'}), 400
        
        data = request.get_json() or {}
        title = data.get('title', 'New Chat')
        
        chat_id = db.create_agent_chat(project_id, title)
        chat = db.get_agent_chat(project_id, chat_id)
        return jsonify(chat), 201
    except Exception as e:
        logger.error(f"Error creating chat: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/chats/<int:chat_id>', methods=['GET'])
def get_chat(chat_id):
    """Get a specific chat with its messages"""
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
        logger.error(f"Error getting chat: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/chats/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    """Delete a chat"""
    try:
        project_id = state.get_current_project()
        if not project_id:
            return jsonify({'error': 'No current project selected'}), 400
        
        success = db.delete_agent_chat(project_id, chat_id)
        if not success:
            return jsonify({'error': 'Chat not found'}), 404
        
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Error deleting chat: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/chat', methods=['POST'])
def chat_with_agent():
    """Chat with the agent using OpenAI Responses API - processes synchronously and updates DB"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        message = data.get('message', '')
        if not message:
            return jsonify({'error': 'message is required'}), 400
        
        chat_id = data.get('chat_id')  # Optional, if None, create new chat
        
        # Check if current project is set
        project_id = state.get_current_project()
        if not project_id:
            return jsonify({'error': 'No current project selected'}), 400
        
        # Create new chat if chat_id not provided
        if not chat_id:
            chat_id = db.create_agent_chat(project_id, message[:50] if len(message) > 50 else message)
        
        # Save user message to database
        db.add_agent_message(project_id, chat_id, 'user', message)
        
        # Get conversation history from database
        db_messages = db.get_agent_messages(project_id, chat_id)
        history = []
        for msg in db_messages:
            if msg['role'] in ['user', 'assistant']:
                history.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
        
        client = get_openai_client()
        
        # Define the tools (Responses API uses flat structure)
        tools = [
            {
                "type": "function",
                "name": "query_database",
                "description": """Execute SQL SELECT queries against the HTTP requests database.

Database schema (requests table):
- id: INTEGER PRIMARY KEY - Unique request ID
- method: TEXT NOT NULL - HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- url: TEXT NOT NULL - Full URL including path (e.g., "https://example.com/api/users")
- raw_request: TEXT - Full HTTP request as string
- raw_response: TEXT - Full HTTP response as string  
- status_code: INTEGER - HTTP response status code (200, 404, 500, etc.)
- duration_ms: INTEGER - Request duration in milliseconds
- timestamp: TEXT NOT NULL - Request timestamp in ISO format (e.g., "2024-01-01T12:00:00"), use for ordering
- completed_at: TEXT - Response completion timestamp in ISO format
- flow_id: TEXT - Proxy flow identifier

Common query patterns:
- Filter by method: WHERE method = 'GET'
- Filter by URL: WHERE url LIKE '%login%'
- Filter by status: WHERE status_code = 404
- Order by time: ORDER BY timestamp DESC (newest first) or ORDER BY timestamp ASC (oldest first)
- Limit results: LIMIT 10
- Combine filters: WHERE method = 'POST' AND url LIKE '%api%' ORDER BY timestamp DESC LIMIT 5

Examples:
- "SELECT * FROM requests WHERE method = 'GET' ORDER BY timestamp DESC LIMIT 10"
- "SELECT * FROM requests WHERE url LIKE '%login%' ORDER BY timestamp DESC LIMIT 5"
- "SELECT * FROM requests WHERE status_code = 404 ORDER BY timestamp DESC"
- "SELECT * FROM requests WHERE method = 'POST' AND url LIKE '%api%' ORDER BY timestamp ASC LIMIT 1"
- "SELECT * FROM requests ORDER BY timestamp ASC LIMIT 1" (first/oldest request)
- "SELECT * FROM requests ORDER BY timestamp DESC LIMIT 10" (last 10/recent requests)

When user asks for specific requests, construct a SQL SELECT query. Use LIKE for URL searches, = for exact matches (method, status_code). Always use ORDER BY timestamp with appropriate LIMIT.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": """A SQL SELECT query to execute. Only SELECT queries are allowed.
Build queries based on what the user asks:
- User says "GET requests" → SELECT * FROM requests WHERE method = 'GET' ORDER BY timestamp DESC LIMIT 100
- User says "first request" → SELECT * FROM requests ORDER BY timestamp ASC LIMIT 1
- User says "last 10 requests" → SELECT * FROM requests ORDER BY timestamp DESC LIMIT 10
- User says "login requests" → SELECT * FROM requests WHERE url LIKE '%login%' ORDER BY timestamp DESC LIMIT 100
- User says "POST /api/login" → SELECT * FROM requests WHERE method = 'POST' AND url LIKE '%/api/login%' ORDER BY timestamp DESC LIMIT 100
- User says "status 404" → SELECT * FROM requests WHERE status_code = 404 ORDER BY timestamp DESC LIMIT 100

Always include ORDER BY timestamp (DESC for newest/recent, ASC for oldest/first) and appropriate LIMIT."""
                        }
                    },
                    "required": ["sql_query"]
                }
            },
            {
                "type": "function",
                "name": "send_request",
                "description": """Send a raw HTTP request to a specified host and port.

This tool allows you to send HTTP requests similar to the resender functionality. You can send GET, POST, PUT, DELETE, PATCH, or any other HTTP method.

The raw_request should be a complete HTTP request string in the following format:
```
GET /api/users HTTP/1.1
Host: example.com
Content-Type: application/json

[optional body]
```

For POST/PUT/PATCH requests with a body:
```
POST /api/users HTTP/1.1
Host: example.com
Content-Type: application/json

{"name": "John", "email": "john@example.com"}
```

The host, port, and use_https parameters allow you to specify where to send the request.
- host: The target hostname (e.g., "example.com", "api.example.com")
- port: The target port (default: "443" for HTTPS, "80" for HTTP)
- use_https: Whether to use HTTPS (default: True unless port is "80")

Returns the HTTP response including status_code, headers, raw_response, and any error.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "raw_request": {
                            "type": "string",
                            "description": "The raw HTTP request string. Must include the request line (METHOD PATH HTTP/VERSION), headers, and optional body separated by newlines."
                        },
                        "host": {
                            "type": "string",
                            "description": "The target hostname (e.g., 'example.com', 'api.example.com'). Default: 'example.com'"
                        },
                        "port": {
                            "type": "string",
                            "description": "The target port. Default: '443' for HTTPS, '80' for HTTP"
                        },
                        "use_https": {
                            "type": "boolean",
                            "description": "Whether to use HTTPS. Default: True unless port is '80'"
                        }
                    },
                    "required": ["raw_request"]
                }
            },
            {
                "type": "function",
                "name": "browse",
                "description": """Browse the web using an automated browser.

This tool allows you to control a browser to navigate websites, interact with pages, search for information, and perform various browsing tasks. The browser uses a proxy to capture all HTTP requests and responses.

The tool will automatically:
- Start the proxy if it's not running
- Create a browser session if one doesn't exist
- Execute the browsing task using an AI agent

You can provide a task description and optionally additional tasks to execute sequentially.

Examples:
- "search for dogs" - Search for dogs on a search engine
- "go to example.com and click the login button"
- "navigate to https://example.com and fill out the contact form"

Returns status and result message.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "The browsing task to execute. Describe what you want the browser to do, e.g., 'search for dogs', 'go to example.com', 'click the login button'"
                        },
                        "additional_tasks": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Optional list of additional tasks to execute sequentially after the initial task"
                        }
                    },
                    "required": ["task"]
                }
            }
        ]
        
        # Instructions (system message equivalent)
        instructions = """You are a helpful DAST tool for cybersecurity professionals that can query a database of HTTP requests using SQL, send HTTP requests, and browse the web.

You have three main capabilities:

1. QUERY DATABASE: You can query the database of captured HTTP requests using SQL SELECT queries.
   The database has a 'requests' table with these fields:
   - id: INTEGER (primary key)
   - method: TEXT (HTTP method: GET, POST, PUT, DELETE, etc.)
   - url: TEXT (full URL)
   - status_code: INTEGER (HTTP status code: 200, 404, 500, etc.)
   - timestamp: TEXT (ISO timestamp, use for ordering - DESC = newest first, ASC = oldest first)
   - raw_request: TEXT (full request)
   - raw_response: TEXT (full response)
   - duration_ms: INTEGER (request duration)
   - completed_at: TEXT (completion timestamp)
   - flow_id: TEXT (proxy flow ID)

   When users ask about requests, construct a SQL SELECT query:
   - Use WHERE for filtering (method = 'GET', url LIKE '%keyword%', status_code = 404)
   - Use ORDER BY timestamp DESC for newest/recent requests
   - Use ORDER BY timestamp ASC for oldest/first requests  
   - Use LIMIT to restrict results (LIMIT 1 for "first", LIMIT 10 for "last 10", etc.)
   - Combine conditions with AND: WHERE method = 'POST' AND url LIKE '%api%'

   Examples:
   - User: "GET requests" → SELECT * FROM requests WHERE method = 'GET' ORDER BY timestamp DESC LIMIT 100
   - User: "first request" → SELECT * FROM requests ORDER BY timestamp ASC LIMIT 1
   - User: "login requests" → SELECT * FROM requests WHERE url LIKE '%login%' ORDER BY timestamp DESC LIMIT 100

2. SEND REQUESTS: You can send HTTP requests to any host, similar to the resender functionality.
   Use this when users ask you to:
   - Send a request
   - Test an endpoint
   - Resend a modified request
   - Make a new API call
   
   To send a request, provide the raw_request string with the full HTTP request including:
   - Request line: METHOD PATH HTTP/VERSION
   - Headers (Host, Content-Type, etc.)
   - Optional body (for POST/PUT/PATCH)
   
   Example raw_request:
   ```
   POST /api/users HTTP/1.1
   Host: api.example.com
   Content-Type: application/json
   
   {"name": "John", "email": "john@example.com"}
   ```
   
   You can also specify host, port, and use_https to control where the request is sent.

3. BROWSE: You can control an automated browser to navigate websites, interact with pages, and perform browsing tasks.
   Use this when users ask you to:
   - Browse a website
   - Search for something
   - Navigate to a URL
   - Interact with web pages (click buttons, fill forms, etc.)
   - Perform web-based security testing
   
   The browser automatically uses a proxy to capture all HTTP requests and responses, which are then stored in the database.
   
   Examples:
   - User says "browse to example.com" → use browse with task "navigate to https://example.com"
   - User says "search for dogs" → use browse with task "search for dogs"
   - User says "go to login page and fill the form" → use browse with task "go to the login page and fill out the form"
   
   You can optionally provide additional_tasks to execute multiple steps sequentially.

AFTER YOU BROWSE, THE PACKETS WILL BE STORED IN THE DATABASE. YOU CAN QUERY THE DATABASE TO GET THE PACKETS.
After executing queries, sending requests, or browsing, analyze results and provide clear summaries."""
        
        # Build input list from history + current message
        input_list = []
        
        # Add previous messages from history
        for msg in history:
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role == 'user' and content:
                input_list.append({
                    "role": "user",
                    "content": [{"type": "input_text", "text": content}]
                })
            elif role == 'assistant' and content:
                input_list.append({
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": content}]
                })
        
        # Add current message
        input_list.append({
            "role": "user",
            "content": [{"type": "input_text", "text": message}]
        })
        
        final_content = ""
        max_iterations = 10  # Safety limit
        iteration = 0
        
        # Loop until done
        while iteration < max_iterations:
            iteration += 1
            
            # Call OpenAI Responses API
            response = client.responses.create(
                model="gpt-5-mini",
                instructions=instructions,
                tools=tools,
                input=input_list,
            )
            
            # Add response output to input list for next iteration
            input_list += response.output
            
            # Check for tool calls
            tool_calls = [item for item in response.output if item.type == "function_call"]
            
            if not tool_calls:
                # No more tool calls, extract final text output
                text_outputs = [item for item in response.output if item.type == "message"]
                if text_outputs:
                    # Get text content from message
                    for text_item in text_outputs:
                        if hasattr(text_item, 'content') and text_item.content:
                            for content_item in text_item.content:
                                if hasattr(content_item, 'text'):
                                    final_content = content_item.text
                                    # Save assistant message to database
                                    db.add_agent_message(project_id, chat_id, 'assistant', final_content)
                break  # Done, exit loop
            
            # Process tool calls
            for tool_call in tool_calls:
                tool_name = tool_call.name
                tool_args_str = tool_call.arguments if hasattr(tool_call, 'arguments') else '{}'
                try:
                    tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                except:
                    tool_args = {}
                
                # Save tool_call to database
                step_description = {
                    "query_database": "Querying database",
                    "send_request": "Sending HTTP request",
                    "browse": "Browsing the web"
                }.get(tool_name, tool_name)
                
                db.add_agent_message(
                    project_id, chat_id, 'step', 
                    step_description,
                    step_type='tool_call',
                    tool_name=tool_name,
                    tool_input=tool_args
                )
                
                # Execute the tool
                if tool_name == "query_database":
                    sql_query = tool_args.get('sql_query', '')
                    tool_output = query_database(sql_query)
                elif tool_name == "send_request":
                    raw_request = tool_args.get('raw_request', '')
                    host = tool_args.get('host', 'example.com')
                    port = tool_args.get('port', '443')
                    use_https = tool_args.get('use_https')
                    tool_output = send_request(raw_request, host, port, use_https)
                elif tool_name == "browse":
                    task = tool_args.get('task', '')
                    additional_tasks = tool_args.get('additional_tasks', None)
                    tool_output = browse(task, additional_tasks)
                else:
                    tool_output = {"error": f"Unknown tool: {tool_name}"}
                
                # Save tool_result to database
                result_description = ""
                if tool_name == "query_database":
                    result_description = f"Found {tool_output.get('count', 0)} requests"
                elif tool_name == "send_request":
                    status_code = tool_output.get('status_code', 0)
                    if tool_output.get('error'):
                        result_description = f"Request failed: {tool_output.get('error')}"
                    else:
                        result_description = f"Received response: {status_code}"
                elif tool_name == "browse":
                    if tool_output.get('status') == 'error':
                        result_description = f"Browse failed: {tool_output.get('error', 'Unknown error')}"
                    else:
                        result_description = tool_output.get('message', 'Browse completed')
                else:
                    result_description = f"Tool completed"
                
                db.add_agent_message(
                    project_id, chat_id, 'step',
                    result_description,
                    step_type='tool_result',
                    tool_name=tool_name,
                    tool_input=tool_args,
                    tool_output=tool_output
                )
                
                # Add tool result to input list
                input_list.append({
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps(tool_output)
                })
        
        # Return chat_id
        return jsonify({'chat_id': chat_id}), 200
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Error in agent chat: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
