"""
API endpoints for agent functionality using OpenAI Completions API.
"""
from flask import Blueprint, request, jsonify
from openai import OpenAI
from .. import db, state
from .tools import (
    get_query_database_tool, 
    get_send_request_tool, 
    get_browse_tool,
    query_database,
    send_request,
    browse
)
import json
import logging
import os

logger = logging.getLogger(__name__)

agent_bp = Blueprint('agent', __name__)

# Initialize OpenAI client
client = None
def get_openai_client():
    global client
    client = OpenAI()
    return client

def is_ai_configured():
    """Check if AI is configured (OPENAI_API_KEY is set)"""
    api_key = os.environ.get('OPENAI_API_KEY')
    return api_key is not None and api_key.strip() != ''


@agent_bp.route('/status', methods=['GET'])
def get_ai_status():
    """Check if AI is configured"""
    try:
        configured = is_ai_configured()
        return jsonify({
            'configured': configured,
            'message': 'AI is configured' if configured else 'No .env with AI key detected'
        }), 200
    except Exception as e:
        logger.error(f"Error checking AI status: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


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
    """Chat with the agent using OpenAI Completions API - processes synchronously and updates DB"""
    try:
        # Check if AI is configured
        if not is_ai_configured():
            return jsonify({'error': 'AI is not configured. Please set OPENAI_API_KEY in .env file'}), 400
        
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
        messages = []
        
        # Add system message
        system_message = """You are a helpful DAST tool for cybersecurity professionals that can query a database of HTTP requests using SQL, send HTTP requests, and browse the web.

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
        
        messages.append({
            'role': 'system',
            'content': system_message
        })
        
        # Add conversation history (only user and assistant messages, skip tool messages)
        for msg in db_messages:
            if msg['role'] in ['user', 'assistant']:
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
        
        client = get_openai_client()
        
        # Define the tools (Completions API format)
        tools = [
            get_query_database_tool(),
            get_send_request_tool(),
            get_browse_tool()
        ]
        
        max_iterations = 10  # Safety limit
        iteration = 0
        
        # Loop until done
        while iteration < max_iterations:
            iteration += 1
            
            # Call OpenAI Completions API with model from environment variable
            model = os.environ.get("MODEL", "gpt-5-mini")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            # Get the assistant's message from the response
            assistant_message = response.choices[0].message
            
            # Build assistant message dict for messages list
            assistant_msg_dict = {
                'role': 'assistant',
                'content': assistant_message.content
            }
            # Include tool_calls if present
            if assistant_message.tool_calls:
                assistant_msg_dict['tool_calls'] = [
                    {
                        'id': tc.id,
                        'type': tc.type,
                        'function': {
                            'name': tc.function.name,
                            'arguments': tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            
            # Add assistant message to messages list
            messages.append(assistant_msg_dict)
            
            # Check for tool calls
            tool_calls = assistant_message.tool_calls if assistant_message.tool_calls else []
            
            if not tool_calls:
                # No more tool calls, extract final text content
                final_content = assistant_message.content or ""
                if final_content:
                    # Save assistant message to database
                    db.add_agent_message(project_id, chat_id, 'assistant', final_content)
                break  # Done, exit loop
            
            # Process tool calls
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args_str = tool_call.function.arguments
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
                
                # Add tool result to messages list (Completions API format)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_output)
                })
        
        # Return chat_id
        return jsonify({'chat_id': chat_id}), 200
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Error in agent chat: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/resender_agent', methods=['POST'])
def resender_agent():
    """AI copilot for resender - takes text from textbox, returns new text to replace it. Only has query_database tool."""
    try:
        # Check if AI is configured
        if not is_ai_configured():
            return jsonify({'error': 'AI is not configured. Please set OPENAI_API_KEY in .env file'}), 400
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'text is required'}), 400
        
        # Check if current project is set
        project_id = state.get_current_project()
        if not project_id:
            return jsonify({'error': 'No current project selected'}), 400
        
        client = get_openai_client()
        
        # System message for resender agent - focused on editing HTTP requests with database context
        system_message = """You are an AI copilot for editing HTTP requests in a resender tool. You can query a database of HTTP requests using SQL to help you understand the context and modify requests appropriately.

You have one main capability:

QUERY DATABASE: You can query the database of captured HTTP requests using SQL SELECT queries.
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

YOUR TASK:
The user will provide you with text from a resender textbox (an HTTP request). You should:
1. Analyze the request and understand what the user wants to do with it
2. Query the database if needed to get context about similar requests
3. Return a modified version of the HTTP request text that accomplishes what the user wants
4. Return ONLY the modified HTTP request text, nothing else

The response should be the complete HTTP request string that will replace the text in the textbox."""
        
        messages = [
            {
                'role': 'system',
                'content': system_message
            },
            {
                'role': 'user',
                'content': text
            }
        ]
        
        # Define only the query_database tool (no send_request or browse)
        tools = [
            get_query_database_tool()
        ]
        
        max_iterations = 10  # Safety limit
        iteration = 0
        
        # Loop until done
        while iteration < max_iterations:
            iteration += 1
            
            # Call OpenAI Completions API with model from environment variable
            model = os.environ.get("MODEL", "gpt-5-mini")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            
            # Get the assistant's message from the response
            assistant_message = response.choices[0].message
            
            # Build assistant message dict for messages list
            assistant_msg_dict = {
                'role': 'assistant',
                'content': assistant_message.content
            }
            # Include tool_calls if present
            if assistant_message.tool_calls:
                assistant_msg_dict['tool_calls'] = [
                    {
                        'id': tc.id,
                        'type': tc.type,
                        'function': {
                            'name': tc.function.name,
                            'arguments': tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            
            # Add assistant message to messages list
            messages.append(assistant_msg_dict)
            
            # Check for tool calls
            tool_calls = assistant_message.tool_calls if assistant_message.tool_calls else []
            
            if not tool_calls:
                # No more tool calls, extract final text content
                final_content = assistant_message.content or ""
                if final_content:
                    # Return the modified text
                    return jsonify({'text': final_content}), 200
                break  # Done, exit loop
            
            # Process tool calls
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args_str = tool_call.function.arguments
                try:
                    tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                except:
                    tool_args = {}
                
                # Execute the tool (only query_database is available)
                if tool_name == "query_database":
                    sql_query = tool_args.get('sql_query', '')
                    tool_output = query_database(sql_query)
                else:
                    tool_output = {"error": f"Unknown tool: {tool_name}"}
                
                # Add tool result to messages list (Completions API format)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_output)
                })
        
        # If we get here, return the last assistant message content
        final_content = messages[-1].get('content', '') if messages else text
        return jsonify({'text': final_content}), 200
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Error in resender agent: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
