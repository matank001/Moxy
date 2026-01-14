// API base URL
// If VITE_API_URL is empty or not set, use relative URLs (for same-origin serving)
const envApiUrl = import.meta.env.VITE_API_URL;
const API_BASE_URL = envApiUrl && envApiUrl.trim() !== '' 
  ? envApiUrl 
  : (import.meta.env.DEV ? 'http://localhost:5000' : '');

// Project type
export interface Project {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

// Request type (backend format)
export interface HttpRequest {
  id: number;
  method: string;
  url: string;
  raw_request?: string;
  raw_response?: string;
  status_code?: number;
  duration_ms?: number;
  timestamp: string;
  completed_at?: string;
  flow_id?: string;
}

// Proxy types
export interface ProxyStatus {
  running: boolean;
  port: number;
}

export interface ProxySettings {
  port: number;
  running: boolean;
  host: string;
  url: string;
}

export interface ProxyResponse {
  message: string;
  running: boolean;
  port?: number;
}

export interface BrowserStatus {
  running: boolean;
}

export interface BrowserResponse {
  message: string;
  running: boolean;
}

// API client
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Project endpoints
  async getProjects(): Promise<Project[]> {
    return this.request<Project[]>('/api/projects');
  }

  async getCurrentProject(): Promise<{ current_project_id: number | null; project?: Project }> {
    return this.request<{ current_project_id: number | null; project?: Project }>('/api/projects/current');
  }

  async setCurrentProject(projectId: number | null): Promise<{ message: string; current_project_id?: number; project?: Project }> {
    return this.request<{ message: string; current_project_id?: number; project?: Project }>('/api/projects/current', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId }),
    });
  }

  async getProject(id: number): Promise<Project> {
    return this.request<Project>(`/api/projects/${id}`);
  }

  async createProject(data: { name: string; description?: string }): Promise<Project> {
    return this.request<Project>('/api/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateProject(
    id: number,
    data: { name?: string; description?: string }
  ): Promise<Project> {
    return this.request<Project>(`/api/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteProject(id: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/projects/${id}`, {
      method: 'DELETE',
    });
  }

  async openProjectFolder(id: number): Promise<{ message: string; path: string }> {
    return this.request<{ message: string; path: string }>(`/api/projects/${id}/open-folder`, {
      method: 'POST',
    });
  }

  async exportProjectDatabase(id: number): Promise<Blob> {
    const url = `${this.baseUrl}/api/projects/${id}/export`;
    const response = await fetch(url);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.blob();
  }

  async importProject(file: File, projectName?: string): Promise<Project> {
    const formData = new FormData();
    formData.append('file', file);
    if (projectName) {
      formData.append('project_name', projectName);
    }

    const url = `${this.baseUrl}/api/projects/import`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    const data = await response.json();
    return data.project;
  }

  async getAvailableDatabases(): Promise<Array<{ filename: string; path: string; project_name: string; size: number }>> {
    return this.request<Array<{ filename: string; path: string; project_name: string; size: number }>>('/api/projects/available-databases');
  }

  // Request endpoints (per project)
  async getProjectRequests(projectId: number, limit?: number): Promise<HttpRequest[]> {
    const params = limit ? `?limit=${limit}` : '';
    return this.request<HttpRequest[]>(`/api/projects/${projectId}/requests${params}`);
  }

  async getProjectRequest(projectId: number, requestId: number): Promise<HttpRequest> {
    return this.request<HttpRequest>(`/api/projects/${projectId}/requests/${requestId}`);
  }

  async addProjectRequest(
    projectId: number,
    data: {
      method: string;
      url: string;
      headers?: string;
      body?: string;
      response_status?: number;
      response_headers?: string;
      response_body?: string;
    }
  ): Promise<HttpRequest> {
    return this.request<HttpRequest>(`/api/projects/${projectId}/requests`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteProjectRequest(projectId: number, requestId: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/projects/${projectId}/requests/${requestId}`, {
      method: 'DELETE',
    });
  }

  async clearProjectRequests(projectId: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/projects/${projectId}/requests`, {
      method: 'DELETE',
    });
  }

  async healthCheck(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health');
  }

  // Proxy endpoints
  async getProxyStatus(): Promise<ProxyStatus> {
    return this.request<ProxyStatus>('/api/proxy/status');
  }

  async getProxySettings(): Promise<ProxySettings> {
    return this.request<ProxySettings>('/api/proxy/settings');
  }

  async startProxy(): Promise<ProxyResponse> {
    return this.request<ProxyResponse>('/api/proxy/start', {
      method: 'POST',
    });
  }

  async stopProxy(): Promise<ProxyResponse> {
    return this.request<ProxyResponse>('/api/proxy/stop', {
      method: 'POST',
    });
  }

  // Browser endpoints
  async getBrowserStatus(): Promise<BrowserStatus> {
    return this.request<BrowserStatus>('/api/proxy/browser/status');
  }

  async startBrowser(): Promise<BrowserResponse> {
    return this.request<BrowserResponse>('/api/proxy/browser/start', {
      method: 'POST',
    });
  }

  // Intercept endpoints
  async getInterceptStatus(): Promise<{ enabled: boolean }> {
    return this.request<{ enabled: boolean }>('/api/proxy/intercept');
  }

  async setInterceptStatus(enabled: boolean): Promise<{ message: string; enabled: boolean }> {
    return this.request<{ message: string; enabled: boolean }>('/api/proxy/intercept', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    });
  }

  async getInterceptedFlows(): Promise<{ flow_ids: string[] }> {
    return this.request<{ flow_ids: string[] }>('/api/proxy/intercepted');
  }

  async forwardInterceptedFlow(flowId: string, editedRequest?: string): Promise<{ message: string; flow_id: string }> {
    return this.request<{ message: string; flow_id: string }>(`/api/proxy/intercepted/${flowId}/forward`, {
      method: 'POST',
      body: JSON.stringify({ edited_request: editedRequest }),
    });
  }

  async dropInterceptedFlow(flowId: string): Promise<{ message: string; flow_id: string }> {
    return this.request<{ message: string; flow_id: string }>(`/api/proxy/intercepted/${flowId}/drop`, {
      method: 'POST',
    });
  }

  // Resender endpoints
  async getResenderTabs(projectId: number): Promise<ResenderTab[]> {
    return this.request<ResenderTab[]>(`/api/projects/${projectId}/resender/tabs`);
  }

  async createResenderTab(
    projectId: number,
    data: { name?: string; host?: string; port?: string }
  ): Promise<ResenderTab> {
    return this.request<ResenderTab>(`/api/projects/${projectId}/resender/tabs`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getResenderTab(projectId: number, tabId: number): Promise<ResenderTab> {
    return this.request<ResenderTab>(`/api/projects/${projectId}/resender/tabs/${tabId}`);
  }

  async updateResenderTab(
    projectId: number,
    tabId: number,
    data: { name?: string; host?: string; port?: string }
  ): Promise<ResenderTab> {
    return this.request<ResenderTab>(`/api/projects/${projectId}/resender/tabs/${tabId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteResenderTab(projectId: number, tabId: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/projects/${projectId}/resender/tabs/${tabId}`, {
      method: 'DELETE',
    });
  }

  async sendResenderRequest(
    projectId: number,
    tabId: number,
    data: { raw_request: string }
  ): Promise<{ version: ResenderVersion; status_code: number; error?: string }> {
    return this.request<{ version: ResenderVersion; status_code: number; error?: string }>(
      `/api/projects/${projectId}/resender/tabs/${tabId}/send`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  }

  async getResenderVersions(projectId: number, tabId: number): Promise<ResenderVersion[]> {
    return this.request<ResenderVersion[]>(`/api/projects/${projectId}/resender/tabs/${tabId}/versions`);
  }

  // Agent endpoints
  async getAiStatus(): Promise<{ configured: boolean; message: string }> {
    return this.request<{ configured: boolean; message: string }>('/api/agent/status', {
      method: 'GET',
    });
  }

  async getAgentChats(): Promise<any[]> {
    return this.request<any[]>('/api/agent/chats', {
      method: 'GET',
    });
  }

  async createAgentChat(title?: string): Promise<any> {
    return this.request<any>('/api/agent/chats', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  }

  async getAgentChat(chatId: number): Promise<{ chat: any; messages: any[] }> {
    return this.request<{ chat: any; messages: any[] }>(`/api/agent/chats/${chatId}`, {
      method: 'GET',
    });
  }

  async deleteAgentChat(chatId: number): Promise<void> {
    return this.request<void>(`/api/agent/chats/${chatId}`, {
      method: 'DELETE',
    });
  }

  async chatWithAgent(
    message: string,
    chatId?: number
  ): Promise<number> {
    const url = `${this.baseUrl}/api/agent/chat`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, chat_id: chatId }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    const data = await response.json();
    return data.chat_id || 0;
  }

  async resenderAgent(text: string): Promise<string> {
    return this.request<{ text: string }>('/api/agent/resender_agent', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }).then(data => data.text);
  }
}

export const api = new ApiClient(API_BASE_URL);

// Resender types
export interface ResenderTab {
  id: number;
  name: string;
  host: string;
  port: string;
  created_at: string;
  versions?: ResenderVersion[];
}

export interface ResenderVersion {
  id: number;
  tab_id: number;
  raw_request: string;
  raw_response: string | null;
  timestamp: string;
}

// Intercept types - now just flow IDs
