import { useState, createContext, useContext, ReactNode, useEffect } from "react";
import { HttpRequest, HttpResponse } from "@/data/demoData";
import { api, ResenderTab as BackendResenderTab, ResenderVersion } from "@/lib/api";
import { parseRawResponse } from "@/lib/requestTransform";

export interface RequestVersion {
  id: string;
  timestamp: Date;
  request: string;
  response: HttpResponse | null;
}

export interface ResenderTab {
  id: string;
  name: string;
  request: HttpRequest;
  editedRaw: string;
  host: string;
  port: string;
  response: HttpResponse | null;
  isLoading: boolean;
  versions: RequestVersion[];
  activeVersionId: string | null;
  backendId?: number; // Store backend tab ID for API calls
}

interface ResenderContextType {
  tabs: ResenderTab[];
  activeTabId: string | null;
  addTab: (request?: HttpRequest) => Promise<void>;
  removeTab: (id: string) => Promise<void>;
  setActiveTab: (id: string) => void;
  updateTabRequest: (id: string, editedRaw: string) => void;
  updateTabName: (id: string, name: string) => Promise<void>;
  updateTabHost: (id: string, host: string) => Promise<void>;
  updateTabPort: (id: string, port: string) => Promise<void>;
  sendRequest: (id: string) => Promise<void>;
  setActiveVersion: (tabId: string, versionId: string) => void;
  navigateToResender: () => void;
  setNavigateCallback: (callback: () => void) => void;
}

const ResenderContext = createContext<ResenderContextType | null>(null);

export const useResender = () => {
  const context = useContext(ResenderContext);
  if (!context) {
    throw new Error("useResender must be used within ResenderProvider");
  }
  return context;
};

let tabCounter = 0;

const defaultRequest: HttpRequest = {
  id: 'new',
  method: 'GET',
  host: 'example.com',
  path: '/',
  raw: `GET / HTTP/1.1
Host: example.com
User-Agent: Puke/1.0
Accept: */*`,
  timestamp: new Date(),
};

// Convert backend tab to frontend tab
function backendTabToFrontend(backendTab: BackendResenderTab): ResenderTab {
  const versions = (backendTab.versions || []).map((v: ResenderVersion) => {
    let response: HttpResponse | null = null;
    if (v.raw_response) {
      const parsed = parseRawResponse(v.raw_response);
      if (parsed) {
        response = {
          requestId: String(v.id),
          status: parsed.status,
          statusText: parsed.statusText,
          raw: v.raw_response,
        };
      }
    }
    return {
      id: String(v.id),
      timestamp: new Date(v.timestamp),
      request: v.raw_request,
      response,
    };
  });
  
  // Get the last (newest) request from versions or use default
  // Versions are now sorted ASC (oldest first), so the last one is the newest
  const lastRequest = versions.length > 0 ? versions[versions.length - 1].request : defaultRequest.raw;
  
  // Parse request to get method and path
  const requestLines = lastRequest.split('\n');
  const requestLine = requestLines[0] || '';
  const methodMatch = requestLine.match(/^(\w+)\s+([^\s]+)/);
  const method = (methodMatch?.[1] || 'GET') as HttpRequest['method'];
  const path = methodMatch?.[2] || '/';
  
  const request: HttpRequest = {
    id: String(backendTab.id),
    method,
    host: backendTab.host,
    path,
    raw: lastRequest,
    timestamp: new Date(backendTab.created_at),
  };
  
  // Get the last (newest) version for active version and response
  const lastVersion = versions.length > 0 ? versions[versions.length - 1] : null;
  
  return {
    id: `tab-${backendTab.id}`,
    backendId: backendTab.id,
    name: backendTab.name,
    request,
    editedRaw: lastRequest,
    host: backendTab.host,
    port: backendTab.port,
    response: lastVersion?.response || null,
    isLoading: false,
    versions,
    activeVersionId: lastVersion?.id || null,
  };
}

export const ResenderProvider = ({ children }: { children: ReactNode }) => {
  const [tabs, setTabs] = useState<ResenderTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [navigateCallback, setNavigateCallbackState] = useState<(() => void) | null>(null);
  const [currentProjectId, setCurrentProjectId] = useState<number | null>(null);

  // Load current project on mount and listen for changes
  useEffect(() => {
    const loadProject = async () => {
      try {
        const data = await api.getCurrentProject();
        if (data.current_project_id && data.project) {
          setCurrentProjectId(data.current_project_id);
        } else {
          const projects = await api.getProjects();
          if (projects.length > 0) {
            setCurrentProjectId(projects[0].id);
            await api.setCurrentProject(projects[0].id);
          }
        }
      } catch (error) {
        console.error("Failed to load current project:", error);
      }
    };
    loadProject();

    // Poll for project changes every 1 second to detect when project is switched
    const interval = setInterval(async () => {
      try {
        const data = await api.getCurrentProject();
        if (data.current_project_id) {
          setCurrentProjectId(prev => {
            // Only update if project actually changed
            if (prev !== data.current_project_id) {
              return data.current_project_id;
            }
            return prev;
          });
        }
      } catch (error) {
        // Silently fail - project might not be set yet
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const loadTabs = async () => {
    if (!currentProjectId) return;
    try {
      const backendTabs = await api.getResenderTabs(currentProjectId);
      const frontendTabs = backendTabs.map(backendTabToFrontend);
      setTabs(frontendTabs);
      // Reset active tab when switching projects - select first tab if available
      if (frontendTabs.length > 0) {
        setActiveTabId(frontendTabs[0].id);
      } else {
        setActiveTabId(null);
      }
    } catch (error) {
      console.error("Failed to load resender tabs:", error);
    }
  };

  // Load tabs when project changes
  useEffect(() => {
    if (currentProjectId) {
      loadTabs();
    } else {
      setTabs([]);
      setActiveTabId(null); // Clear active tab when no project
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProjectId]);

  const setNavigateCallback = (callback: () => void) => {
    setNavigateCallbackState(() => callback);
  };

  const navigateToResender = () => {
    if (navigateCallback) {
      navigateCallback();
    }
  };

  const addTab = async (request?: HttpRequest) => {
    if (!currentProjectId) {
      throw new Error("No current project");
    }
    
    tabCounter++;
    const req = request || defaultRequest;
    const name = `tab(${tabCounter})`;
    
    // Extract port from host if it contains a port, otherwise default to 443
    let port = '443';
    if (request && req.host) {
      // Check if host contains a port (e.g., "example.com:8080")
      const hostPortMatch = req.host.match(/:(\d+)$/);
      if (hostPortMatch) {
        port = hostPortMatch[1];
      }
    }
    
    try {
      // Extract just the hostname (without port) for the host field
      const hostname = req.host.split(':')[0];
      
      const backendTab = await api.createResenderTab(currentProjectId, {
        name,
        host: hostname,
        port: port,
      });
      
      const newTab = backendTabToFrontend(backendTab);
      
      // If we have a raw request, set it as editedRaw
      if (req.raw) {
        newTab.editedRaw = req.raw;
      }
      
      setTabs(prev => [...prev, newTab]);
      setActiveTabId(newTab.id);
    } catch (error) {
      console.error("Failed to create tab:", error);
      throw error; // Re-throw so the caller can handle it
    }
  };

  const removeTab = async (id: string) => {
    if (!currentProjectId) return;
    
    const tab = tabs.find(t => t.id === id);
    if (!tab || !tab.backendId) return;
    
    try {
      await api.deleteResenderTab(currentProjectId, tab.backendId);
      setTabs(prev => {
        const filtered = prev.filter(t => t.id !== id);
        if (activeTabId === id && filtered.length > 0) {
          setActiveTabId(filtered[filtered.length - 1].id);
        } else if (filtered.length === 0) {
          setActiveTabId(null);
        }
        return filtered;
      });
    } catch (error) {
      console.error("Failed to delete tab:", error);
    }
  };

  const setActiveTab = (id: string) => {
    setActiveTabId(id);
  };

  const updateTabRequest = (id: string, editedRaw: string) => {
    setTabs(prev => prev.map(tab => 
      tab.id === id ? { ...tab, editedRaw, activeVersionId: null } : tab
    ));
  };

  const updateTabName = async (id: string, name: string) => {
    if (!currentProjectId) return;
    
    const tab = tabs.find(t => t.id === id);
    if (!tab || !tab.backendId) {
      // Update locally if no backend ID (shouldn't happen but handle gracefully)
      setTabs(prev => prev.map(t => t.id === id ? { ...t, name } : t));
      return;
    }
    
    try {
      await api.updateResenderTab(currentProjectId, tab.backendId, { name });
      // Update the name directly without recreating the entire tab
      setTabs(prev => prev.map(t => t.id === id ? { ...t, name } : t));
    } catch (error) {
      console.error("Failed to update tab name:", error);
      throw error; // Re-throw so caller can show error message
    }
  };

  const updateTabHost = async (id: string, host: string) => {
    if (!currentProjectId) return;
    
    const tab = tabs.find(t => t.id === id);
    if (!tab || !tab.backendId) {
      setTabs(prev => prev.map(t => t.id === id ? { ...t, host } : t));
      return;
    }
    
    try {
      const updatedTab = await api.updateResenderTab(currentProjectId, tab.backendId, { host });
      const frontendTab = backendTabToFrontend(updatedTab);
      setTabs(prev => prev.map(t => t.id === id ? frontendTab : t));
    } catch (error) {
      console.error("Failed to update tab host:", error);
      setTabs(prev => prev.map(t => t.id === id ? { ...t, host } : t));
    }
  };

  const updateTabPort = async (id: string, port: string) => {
    if (!currentProjectId) return;
    
    const tab = tabs.find(t => t.id === id);
    if (!tab || !tab.backendId) {
      setTabs(prev => prev.map(t => t.id === id ? { ...t, port } : t));
      return;
    }
    
    try {
      const updatedTab = await api.updateResenderTab(currentProjectId, tab.backendId, { port });
      const frontendTab = backendTabToFrontend(updatedTab);
      setTabs(prev => prev.map(t => t.id === id ? frontendTab : t));
    } catch (error) {
      console.error("Failed to update tab port:", error);
      setTabs(prev => prev.map(t => t.id === id ? { ...t, port } : t));
    }
  };

  const setActiveVersion = (tabId: string, versionId: string) => {
    setTabs(prev => prev.map(tab => {
      if (tab.id !== tabId) return tab;
      const version = tab.versions.find(v => v.id === versionId);
      if (!version) return tab;
      return {
        ...tab,
        activeVersionId: versionId,
        editedRaw: version.request,
        response: version.response,
      };
    }));
  };

  const sendRequest = async (id: string) => {
    if (!currentProjectId) {
      throw new Error("No current project");
    }
    
    const tab = tabs.find(t => t.id === id);
    if (!tab || !tab.backendId) {
      throw new Error("Tab not found");
    }
    
    // Set loading state and clear response
    setTabs(prev => prev.map(t => 
      t.id === id ? { ...t, isLoading: true, response: null } : t
    ));
    
    try {
      await api.sendResenderRequest(currentProjectId, tab.backendId, {
        raw_request: tab.editedRaw,
      });
      
      // Reload tabs to get updated versions
      const backendTabs = await api.getResenderTabs(currentProjectId);
      const frontendTabs = backendTabs.map(backendTabToFrontend);
      
      // Find the updated tab and set it as active with the latest version
      const updatedTab = frontendTabs.find(t => t.backendId === tab.backendId);
      if (updatedTab && updatedTab.versions.length > 0) {
        // Versions are sorted ASC (oldest first), so the last one is the newest
        const latestVersion = updatedTab.versions[updatedTab.versions.length - 1];
        updatedTab.activeVersionId = latestVersion.id;
        updatedTab.editedRaw = latestVersion.request;
        updatedTab.response = latestVersion.response;
        updatedTab.isLoading = false;
      }
      
      // Preserve frontend tab order by mapping backend tabs to existing order
      setTabs(prev => {
        // Create a map of backend tabs by backendId for quick lookup
        const backendTabMap = new Map(frontendTabs.map(t => [t.backendId, t]));
        
        // Preserve the existing order, updating tabs with backend data
        return prev.map(existingTab => {
          const backendTab = existingTab.backendId 
            ? backendTabMap.get(existingTab.backendId)
            : null;
          
          // If this is the tab we just sent, use the updated tab data
          if (existingTab.id === id && updatedTab) {
            return updatedTab;
          }
          
          // Otherwise, update with backend data if available, or keep existing
          return backendTab || existingTab;
        });
      });
      
      // Keep the same active tab (don't change it)
      // The tab should already be active, so we don't need to change activeTabId
      
    } catch (error) {
      console.error("Failed to send request:", error);
      setTabs(prev => prev.map(t => 
        t.id === id ? { ...t, isLoading: false } : t
      ));
      throw error; // Re-throw so the caller can handle it
    }
  };

  return (
    <ResenderContext.Provider value={{
      tabs,
      activeTabId,
      addTab,
      removeTab,
      setActiveTab,
      updateTabRequest,
      updateTabName,
      updateTabHost,
      updateTabPort,
      sendRequest,
      setActiveVersion,
      navigateToResender,
      setNavigateCallback,
    }}>
      {children}
    </ResenderContext.Provider>
  );
};
