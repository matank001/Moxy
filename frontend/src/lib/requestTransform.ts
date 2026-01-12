import { HttpRequest as BackendRequest } from "@/lib/api";
import { HttpRequest, HttpResponse } from "@/data/demoData";

/**
 * Generate a cURL command from an HTTP request
 */
export function generateCurl(request: HttpRequest): string {
  const lines = request.raw.split('\n');
  const methodMatch = lines[0]?.match(/^(\w+)\s+(\S+)/);
  const method = methodMatch?.[1] || request.method;
  const pathOrUri = methodMatch?.[2] || request.path;
  
  const headers: string[] = [];
  let body = '';
  let inBody = false;
  let hostFromHeader = '';
  let protocol = 'https'; // Default to HTTPS
  
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === '') {
      inBody = true;
      continue;
    }
    if (inBody) {
      body += line;
    } else {
      const headerMatch = line.match(/^([^:]+):\s*(.+)$/);
      if (headerMatch) {
        const headerName = headerMatch[1].toLowerCase();
        const headerValue = headerMatch[2].trim();
        
        if (headerName === 'host') {
          hostFromHeader = headerValue;
        }
        
        // Don't include Host header in curl (it's part of the URL)
        if (headerName !== 'host') {
          headers.push(`-H '${headerMatch[1]}: ${headerValue}'`);
        }
      }
    }
  }
  
  // Determine the URL
  let url: string;
  // Check if path is already an absolute URI (starts with http:// or https://)
  if (pathOrUri.startsWith('http://') || pathOrUri.startsWith('https://')) {
    url = pathOrUri;
  } else {
    // Use host from header if available, otherwise fall back to request.host
    const host = hostFromHeader || request.host;
    // Determine protocol from the URI if it was absolute, otherwise default to https
    if (pathOrUri.startsWith('http://')) {
      protocol = 'http';
    }
    url = `${protocol}://${host}${pathOrUri}`;
  }
  
  let curl = `curl -X ${method}`;
  curl += ` '${url}'`;
  headers.forEach(h => {
    curl += ` \\\n  ${h}`;
  });
  if (body) {
    curl += ` \\\n  -d '${body}'`;
  }
  
  return curl;
}

/**
 * Parse raw HTTP request string to extract components
 */
function parseRawRequest(rawRequest: string): {
  method: string;
  path: string;
  host: string;
  status?: number;
} {
  if (!rawRequest) {
    return { method: 'GET', path: '/', host: '' };
  }

  const lines = rawRequest.split(/\r?\n/);
  if (lines.length === 0) {
    return { method: 'GET', path: '/', host: '' };
  }

  // Parse request line: "METHOD PATH PROTOCOL"
  const requestLine = lines[0];
  const match = requestLine.match(/^(\w+)\s+([^\s]+)\s+HTTP\/[\d.]+$/);
  const method = match ? match[1] : 'GET';
  const path = match ? match[2] : '/';

  // Extract host from headers
  let host = '';
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) break; // End of headers (empty line before body)
    
    const colonIndex = line.indexOf(':');
    if (colonIndex > 0) {
      const headerName = line.substring(0, colonIndex).toLowerCase();
      const headerValue = line.substring(colonIndex + 1).trim();
      
      if (headerName === 'host') {
        host = headerValue;
        break;
      }
    }
  }

  return { method, path, host };
}

/**
 * Parse raw HTTP response string to extract status code and status text
 */
export function parseRawResponse(rawResponse: string): {
  status: number;
  statusText: string;
} | null {
  if (!rawResponse) {
    return null;
  }

  const lines = rawResponse.split(/\r?\n/);
  if (lines.length === 0) {
    return null;
  }

  // Parse status line: "HTTP/1.1 STATUS_CODE STATUS_TEXT"
  const statusLine = lines[0];
  const match = statusLine.match(/^HTTP\/[\d.]+\s+(\d+)\s+(.*)$/);
  
  if (match) {
    const status = parseInt(match[1], 10);
    const statusText = match[2] || 'Unknown';
    return { status, statusText };
  }

  return null;
}

/**
 * Parse HTTP content (request or response) into headers and body
 */
export function parseHttpContent(content: string): {
  requestLine?: string;
  statusLine?: string;
  headers: Array<{ name: string; value: string; raw: string }>;
  body: string;
  isResponse: boolean;
} {
  if (!content) {
    return { headers: [], body: '', isResponse: false };
  }

  const lines = content.split(/\r?\n/);
  if (lines.length === 0) {
    return { headers: [], body: '', isResponse: false };
  }

  // Check if it's a response (starts with HTTP/) or request (starts with METHOD)
  const firstLine = lines[0];
  const isResponse = firstLine.startsWith('HTTP/');
  const statusLine = isResponse ? firstLine : undefined;
  const requestLine = !isResponse ? firstLine : undefined;

  const headers: Array<{ name: string; value: string; raw: string }> = [];
  let bodyStart = -1;
  const headerStart = 1; // Skip status/request line

  // Parse headers
  for (let i = headerStart; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === '') {
      bodyStart = i + 1;
      break;
    }
    
    const colonIndex = line.indexOf(':');
    if (colonIndex > 0) {
      const headerName = line.substring(0, colonIndex).trim();
      const headerValue = line.substring(colonIndex + 1).trim();
      headers.push({
        name: headerName,
        value: headerValue,
        raw: line,
      });
    } else {
      // Continuation of previous header (multiline header)
      if (headers.length > 0) {
        headers[headers.length - 1].raw += ' ' + line.trim();
        headers[headers.length - 1].value += ' ' + line.trim();
      }
    }
  }

  // Extract body
  const body = bodyStart >= 0 ? lines.slice(bodyStart).join('\n') : '';

  return { requestLine, statusLine, headers, body, isResponse };
}

/**
 * Extract host from URL
 */
function extractHost(url: string): string {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname;
  } catch {
    // If URL parsing fails, try to extract host manually
    const match = url.match(/^https?:\/\/([^\/]+)/);
    return match ? match[1] : url;
  }
}

/**
 * Transform backend request format to UI format
 */
export function transformRequest(backendRequest: BackendRequest): HttpRequest {
  // Parse raw request if available
  let host = '';
  let path = '/';
  let method: HttpRequest['method'] = 'GET';
  
  if (backendRequest.raw_request) {
    const parsed = parseRawRequest(backendRequest.raw_request);
    method = (parsed.method as HttpRequest['method']) || 'GET';
    path = parsed.path || '/';
    host = parsed.host || '';
  }
  
  // Fallback to URL parsing if raw_request not available or host missing
  if (!host) {
    host = extractHost(backendRequest.url);
  }
  
  // Extract status - prefer status_code from database, fallback to parsing raw_response
  let status: number | undefined;
  if (backendRequest.status_code !== undefined && backendRequest.status_code !== null) {
    status = backendRequest.status_code;
  } else if (backendRequest.raw_response) {
    const parsed = parseRawResponse(backendRequest.raw_response);
    status = parsed?.status;
  }

  return {
    id: String(backendRequest.id),
    method: method || (backendRequest.method as HttpRequest['method']) || 'GET',
    host,
    path: path || '/',
    raw: backendRequest.raw_request || '',
    timestamp: new Date(backendRequest.timestamp),
    status,
    flow_id: backendRequest.flow_id, // Preserve flow_id from backend
  };
}

/**
 * Transform backend request to response format
 */
export function transformResponse(backendRequest: BackendRequest): HttpResponse | null {
  if (!backendRequest.raw_response) {
    return null;
  }

  const parsed = parseRawResponse(backendRequest.raw_response);
  if (!parsed) {
    return null;
  }

  return {
    requestId: String(backendRequest.id),
    status: parsed.status,
    statusText: parsed.statusText,
    raw: backendRequest.raw_response,
  };
}
