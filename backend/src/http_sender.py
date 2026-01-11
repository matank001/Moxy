"""
HTTP request sender that parses raw HTTP requests and sends them.
"""
import re
import requests
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def parse_raw_http_request(raw_request: str):
    """
    Parse a raw HTTP request string and extract method, URL, headers, and body.
    
    Returns:
        dict with keys: method, url, headers (dict), body (bytes or None)
    """
    if not raw_request or not raw_request.strip():
        raise ValueError("Empty HTTP request")
    
    lines = raw_request.split('\n')
    
    # Parse request line (first line): METHOD PATH HTTP/VERSION
    # Handle both origin-form (/path) and absolute-form (https://host/path)
    request_line = lines[0].strip()
    request_match = re.match(r'^(\w+)\s+([^\s]+)\s+HTTP/[\d.]+$', request_line)
    if not request_match:
        raise ValueError(f"Invalid request line: {request_line}")
    
    method = request_match.group(1)
    path_or_url = request_match.group(2)
    
    # If the path is a full URL (absolute-form), extract just the path component
    # This handles HTTP/2.0 requests which use absolute-form: GET https://host/path HTTP/2.0
    if path_or_url.startswith('http://') or path_or_url.startswith('https://'):
        try:
            parsed_url = urlparse(path_or_url)
            path = parsed_url.path
            if parsed_url.query:
                path += '?' + parsed_url.query
        except Exception:
            # If URL parsing fails, try to extract path manually
            # Format: https://host/path -> /path
            match = re.match(r'https?://[^/]+(.*)', path_or_url)
            path = match.group(1) if match else path_or_url
    else:
        # Origin-form: just the path
        path = path_or_url
    
    # Parse headers
    headers = {}
    body_start = 1
    for i in range(1, len(lines)):
        line = lines[i].strip()
        if not line:  # Empty line marks end of headers
            body_start = i + 1
            break
        
        colon_idx = line.find(':')
        if colon_idx > 0:
            header_name = line[:colon_idx].strip()
            header_value = line[colon_idx + 1:].strip()
            headers[header_name] = header_value
    
    # Parse body (everything after empty line)
    body = None
    if body_start < len(lines):
        body_lines = lines[body_start:]
        body = '\n'.join(body_lines)
        # If body is empty string after join, set to None
        if not body.strip():
            body = None
    
    return {
        'method': method,
        'path': path,
        'headers': headers,
        'body': body
    }


def send_raw_http_request(raw_request: str, host: str, port: str = '443', use_https: bool = True):
    """
    Parse and send a raw HTTP request to the specified host.
    
    Args:
        raw_request: Raw HTTP request string
        host: Target host
        port: Target port (default: '443')
        use_https: Whether to use HTTPS (default: True)
    
    Returns:
        dict with keys: status_code, headers (dict), raw_response (str), error (optional)
    """
    try:
        # Parse the raw request
        parsed = parse_raw_http_request(raw_request)
        method = parsed['method']
        path = parsed['path']
        headers = parsed['headers']
        body = parsed['body']
        
        # Build the URL
        protocol = 'https' if use_https else 'http'
        if port == '80' and not use_https:
            url = f'{protocol}://{host}{path}'
        elif port == '443' and use_https:
            url = f'{protocol}://{host}{path}'
        else:
            url = f'{protocol}://{host}:{port}{path}'
        
        # Remove Host header if present (requests library will set it)
        headers.pop('Host', None)
        headers.pop('host', None)
        
        # Remove Content-Length (requests will set it automatically)
        headers.pop('Content-Length', None)
        headers.pop('content-length', None)
        
        # Send the request
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=body.encode('utf-8') if body else None,
            allow_redirects=False,
            timeout=30,
            verify=False  # Allow self-signed certs for testing
        )
        
        # Build raw response
        status_line = f'HTTP/1.1 {response.status_code} {response.reason}\r\n'
        response_headers = '\r\n'.join(f'{k}: {v}' for k, v in response.headers.items())
        raw_response = status_line + response_headers + '\r\n\r\n'
        
        # Add response body
        try:
            response_text = response.text
            raw_response += response_text
        except:
            raw_response += response.content.decode('utf-8', errors='replace')
        
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'raw_response': raw_response,
            'error': None
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}", exc_info=True)
        # Return error as response
        error_msg = str(e)
        raw_response = f'HTTP/1.1 000 Connection Error\r\nContent-Type: text/plain\r\n\r\n{error_msg}'
        return {
            'status_code': 0,
            'headers': {},
            'raw_response': raw_response,
            'error': error_msg
        }
    except Exception as e:
        logger.error(f"Error parsing/sending request: {e}", exc_info=True)
        error_msg = str(e)
        raw_response = f'HTTP/1.1 500 Parse Error\r\nContent-Type: text/plain\r\n\r\n{error_msg}'
        return {
            'status_code': 500,
            'headers': {},
            'raw_response': raw_response,
            'error': error_msg
        }
