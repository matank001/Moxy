export interface HttpRequest {
  id: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'OPTIONS' | 'HEAD';
  host: string;
  path: string;
  raw: string;
  timestamp: Date;
  status?: number;
  flow_id?: string;
}

export interface HttpResponse {
  requestId: string;
  status: number;
  statusText: string;
  raw: string;
}

export const demoRequests: HttpRequest[] = [
  {
    id: '1',
    method: 'GET',
    host: 'api.example.com',
    path: '/users/profile',
    timestamp: new Date('2026-01-10T10:23:45'),
    status: 200,
    raw: `GET /users/profile HTTP/1.1
Host: api.example.com
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
Accept: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Connection: keep-alive
Accept-Encoding: gzip, deflate, br`
  },
  {
    id: '2',
    method: 'POST',
    host: 'api.example.com',
    path: '/auth/login',
    timestamp: new Date('2026-01-10T10:22:30'),
    status: 200,
    raw: `POST /auth/login HTTP/1.1
Host: api.example.com
Content-Type: application/json
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
Accept: application/json
Content-Length: 52

{"username":"admin","password":"supersecret123"}`
  },
  {
    id: '3',
    method: 'GET',
    host: 'cdn.example.com',
    path: '/assets/logo.png',
    timestamp: new Date('2026-01-10T10:21:15'),
    status: 304,
    raw: `GET /assets/logo.png HTTP/1.1
Host: cdn.example.com
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
Accept: image/webp,image/apng,image/*
If-None-Match: "abc123"
Cache-Control: max-age=0`
  },
  {
    id: '4',
    method: 'PUT',
    host: 'api.example.com',
    path: '/users/settings',
    timestamp: new Date('2026-01-10T10:20:00'),
    status: 401,
    raw: `PUT /users/settings HTTP/1.1
Host: api.example.com
Content-Type: application/json
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
Accept: application/json
Content-Length: 34

{"theme":"dark","notifications":true}`
  },
  {
    id: '5',
    method: 'DELETE',
    host: 'api.example.com',
    path: '/posts/42',
    timestamp: new Date('2026-01-10T10:18:45'),
    status: 403,
    raw: `DELETE /posts/42 HTTP/1.1
Host: api.example.com
Authorization: Bearer expired_token
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
Accept: application/json`
  },
  {
    id: '6',
    method: 'GET',
    host: 'vulnerable-app.local',
    path: "/search?q=<script>alert('xss')</script>",
    timestamp: new Date('2026-01-10T10:15:30'),
    status: 200,
    raw: `GET /search?q=<script>alert('xss')</script> HTTP/1.1
Host: vulnerable-app.local
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
Accept: text/html,application/xhtml+xml
Cookie: session=abc123def456`
  }
];

export const demoResponses: Record<string, HttpResponse> = {
  '1': {
    requestId: '1',
    status: 200,
    statusText: 'OK',
    raw: `HTTP/1.1 200 OK
Content-Type: application/json
Date: Fri, 10 Jan 2026 10:23:45 GMT
Server: nginx/1.21.0
Content-Length: 156
X-Request-ID: req_abc123

{
  "id": 12345,
  "username": "admin",
  "email": "admin@example.com",
  "role": "administrator",
  "lastLogin": "2026-01-10T09:00:00Z"
}`
  },
  '2': {
    requestId: '2',
    status: 200,
    statusText: 'OK',
    raw: `HTTP/1.1 200 OK
Content-Type: application/json
Date: Fri, 10 Jan 2026 10:22:30 GMT
Set-Cookie: session=eyJhbGciOiJIUzI1NiIs...; HttpOnly; Secure
X-Request-ID: req_def456
Content-Length: 89

{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expiresIn": 3600
}`
  },
  '3': {
    requestId: '3',
    status: 304,
    statusText: 'Not Modified',
    raw: `HTTP/1.1 304 Not Modified
Date: Fri, 10 Jan 2026 10:21:15 GMT
ETag: "abc123"
Cache-Control: public, max-age=31536000`
  },
  '4': {
    requestId: '4',
    status: 401,
    statusText: 'Unauthorized',
    raw: `HTTP/1.1 401 Unauthorized
Content-Type: application/json
Date: Fri, 10 Jan 2026 10:20:00 GMT
WWW-Authenticate: Bearer
Content-Length: 67

{
  "error": "unauthorized",
  "message": "Invalid or expired token"
}`
  },
  '5': {
    requestId: '5',
    status: 403,
    statusText: 'Forbidden',
    raw: `HTTP/1.1 403 Forbidden
Content-Type: application/json
Date: Fri, 10 Jan 2026 10:18:45 GMT
Content-Length: 82

{
  "error": "forbidden",
  "message": "You do not have permission to delete this post"
}`
  },
  '6': {
    requestId: '6',
    status: 200,
    statusText: 'OK',
    raw: `HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Date: Fri, 10 Jan 2026 10:15:30 GMT
Content-Length: 245

<!DOCTYPE html>
<html>
<head><title>Search Results</title></head>
<body>
  <h1>Search Results for: <script>alert('xss')</script></h1>
  <p>No results found.</p>
</body>
</html>`
  }
};
