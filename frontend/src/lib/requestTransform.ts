import { HttpRequest as BackendRequest } from "@/lib/api";
import { HttpRequest, HttpResponse } from "@/data/demoData";

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
