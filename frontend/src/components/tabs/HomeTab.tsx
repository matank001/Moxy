import { useState, useEffect, useRef, useMemo } from "react";
import * as React from "react";
import { HttpRequest, HttpResponse } from "@/data/demoData";
import { RequestList } from "@/components/RequestList";
import { HttpViewer } from "@/components/HttpViewer";
import { RequestFilters } from "@/components/RequestFilters";
import { StatusCode } from "@/components/StatusCode";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Inbox, Globe, Shield, Filter, Trash2, Send, AlertCircle, X, Copy, Check, Eye, Code, Edit2 } from "lucide-react";
import { api, HttpRequest as BackendRequest, Project } from "@/lib/api";
import { transformRequest, transformResponse, generateCurl } from "@/lib/requestTransform";
import { toast } from "sonner";
import { useResender } from "@/contexts/ResenderContext";

interface RequestFiltersState {
  hideStaticAssets: boolean;
  excludedHosts: string[];
  includedHosts: string[];
  methods: string[]; // HTTP methods to include (empty = all methods)
  statusCodes: string[]; // Status code ranges to include (e.g., '2xx', '3xx', '4xx', '5xx') or empty for all
  textSearch: string;
  textSearchScope: 'both' | 'request' | 'response';
}

// Static asset file extensions to filter
const STATIC_ASSET_EXTENSIONS = [
  '.js', '.jsx', '.ts', '.tsx',
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico', '.bmp',
  '.css', '.scss', '.sass', '.less',
  '.woff', '.woff2', '.ttf', '.otf', '.eot',
  '.mp4', '.webm', '.mp3', '.wav', '.ogg',
  '.pdf', '.zip', '.tar', '.gz',
  '.map', '.json',
];

export const HomeTab = () => {
  const [requests, setRequests] = useState<HttpRequest[]>([]);
  const [responses, setResponses] = useState<Record<string, HttpResponse>>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [isBrowserLoading, setIsBrowserLoading] = useState(false);
  const [isDocker, setIsDocker] = useState(false);
  const [interceptEnabled, setInterceptEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isFilterDialogOpen, setIsFilterDialogOpen] = useState(false);
  const [interceptedFlowIds, setInterceptedFlowIds] = useState<string[]>([]);
  const [editingInterceptedFlow, setEditingInterceptedFlow] = useState<string | null>(null);
  const [editedRequests, setEditedRequests] = useState<Record<string, string>>({});
  const [requestCopied, setRequestCopied] = useState(false);
  const [showRawRequest, setShowRawRequest] = useState(false);
  const [filters, setFilters] = useState<RequestFiltersState>({
    hideStaticAssets: false,
    excludedHosts: [],
    includedHosts: [],
    methods: [],
    statusCodes: [],
    textSearch: '',
    textSearchScope: 'both',
  });
  const isInitialLoad = React.useRef(true);
  const userHasSelected = React.useRef(false);
  const { addTab, navigateToResender } = useResender();

  const handleSendToResender = async (request: HttpRequest) => {
    try {
      await addTab(request);
      navigateToResender();
      toast.success("Sent to Resender", {
        description: `${request.method} ${request.path}`
      });
    } catch (error) {
      console.error("Failed to send to resender:", error);
      toast.error("Failed to send to Resender", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };


  const handleCopyAsCurl = async (request: HttpRequest) => {
    try {
      const curl = generateCurl(request);
      await navigator.clipboard.writeText(curl);
      toast.success("Copied to clipboard", {
        description: "cURL command copied successfully"
      });
    } catch (error) {
      toast.error("Failed to copy", {
        description: "Could not copy to clipboard",
      });
    }
  };

  const handleCopyRequest = async (request: HttpRequest, flowId?: string | null) => {
    try {
      // If intercepted and edited, copy the edited version, otherwise copy raw
      const contentToCopy = (flowId && editedRequests[flowId]) 
        ? editedRequests[flowId] 
        : (request.raw || '');
      
      await navigator.clipboard.writeText(contentToCopy);
      setRequestCopied(true);
      toast.success("Copied to clipboard", {
        description: `${contentToCopy.length} characters copied`,
      });
      setTimeout(() => setRequestCopied(false), 2000);
    } catch (error) {
      toast.error("Failed to copy", {
        description: "Could not copy to clipboard",
      });
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle if Cmd (Mac) or Ctrl (Windows/Linux) is pressed
      if (!e.metaKey && !e.ctrlKey) return;
      
      // Don't trigger if user is typing in an input/textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      const selectedRequest = requests.find(r => r.id === selectedId);
      if (!selectedRequest) return;

      if (e.key === 'r' || e.key === 'R') {
        // Cmd+R: Send to Resender
        e.preventDefault();
        handleSendToResender(selectedRequest);
      } else if (e.key === 'c' || e.key === 'C') {
        // Cmd+C: Copy as cURL
        e.preventDefault();
        handleCopyAsCurl(selectedRequest);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedId, requests, addTab, navigateToResender]);

  const handleClearAll = async () => {
    if (!currentProject) return;
    
    if (!confirm(`Are you sure you want to delete all ${requests.length} requests? This action cannot be undone.`)) {
      return;
    }

    try {
      setIsLoading(true);
      await api.clearProjectRequests(currentProject.id);
      
      // Clear local state
      setRequests([]);
      setResponses({});
      setSelectedId(null);
      
      toast.success("All requests cleared", {
        description: `Deleted ${requests.length} request(s)`,
      });
    } catch (error) {
      console.error("Failed to clear requests:", error);
      toast.error("Failed to clear requests", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Apply filters to requests
  const filteredRequests = useMemo(() => {
    let filtered = [...requests];

    if (filters.hideStaticAssets) {
      filtered = filtered.filter((req) => {
        const path = req.path.toLowerCase();
        return !STATIC_ASSET_EXTENSIONS.some((ext) => path.endsWith(ext));
      });
    }

    if (filters.excludedHosts.length > 0) {
      filtered = filtered.filter((req) => {
        const host = req.host.toLowerCase();
        return !filters.excludedHosts.includes(host);
      });
    }

    if (filters.includedHosts.length > 0) {
      filtered = filtered.filter((req) => {
        const host = req.host.toLowerCase();
        return filters.includedHosts.includes(host);
      });
    }

    if (filters.methods.length > 0) {
      filtered = filtered.filter((req) => {
        return filters.methods.includes(req.method.toUpperCase());
      });
    }

    if (filters.statusCodes.length > 0) {
      filtered = filtered.filter((req) => {
        if (req.status === undefined || req.status === null) {
          // If no status code, exclude it when status code filters are active
          return false;
        }
        return filters.statusCodes.some((range) => {
          if (range === '2xx') return req.status >= 200 && req.status < 300;
          if (range === '3xx') return req.status >= 300 && req.status < 400;
          if (range === '4xx') return req.status >= 400 && req.status < 500;
          if (range === '5xx') return req.status >= 500 && req.status < 600;
          return false;
        });
      });
    }

    // Text search filter
    if (filters.textSearch.trim()) {
      const searchText = filters.textSearch.toLowerCase();
      filtered = filtered.filter((req) => {
        const requestMatches = filters.textSearchScope === 'both' || filters.textSearchScope === 'request'
          ? (req.raw || '').toLowerCase().includes(searchText)
          : false;
        
        const responseMatches = filters.textSearchScope === 'both' || filters.textSearchScope === 'response'
          ? (responses[req.id]?.raw || '').toLowerCase().includes(searchText)
          : false;
        
        return requestMatches || responseMatches;
      });
    }

    return filtered;
  }, [requests, filters, responses]);

  const checkDockerEnvironment = async () => {
    try {
      const health = await api.healthCheck();
      setIsDocker(health.docker === true);
    } catch (error) {
      console.error("Failed to check Docker environment:", error);
    }
  };

  // Load current project and requests on mount
  useEffect(() => {
    loadCurrentProject();
    loadInterceptStatus();
    checkDockerEnvironment();
  }, []);

  // Load intercept status
  const loadInterceptStatus = async () => {
    try {
      const status = await api.getInterceptStatus();
      setInterceptEnabled(status.enabled);
    } catch (error) {
      console.error("Failed to load intercept status:", error);
    }
  };

  // Poll for intercepted flow IDs when intercept is enabled
  useEffect(() => {
    const loadInterceptedFlowIds = async () => {
      try {
        const data = await api.getInterceptedFlows();
        // Only update if intercept is still enabled (avoid race conditions)
        if (interceptEnabled) {
          const flowIds = data.flow_ids || [];
          setInterceptedFlowIds(flowIds);
        } else {
          // If intercept was disabled, clear the list
          setInterceptedFlowIds([]);
        }
      } catch (error) {
        console.error("Failed to load intercepted flows:", error);
        // On error, clear the list to avoid showing stale data
        if (!interceptEnabled) {
          setInterceptedFlowIds([]);
        }
      }
    };

    if (!interceptEnabled) {
      // When intercept is disabled, clear immediately and check once more
      setInterceptedFlowIds([]);
      // Check once more after a short delay to catch any that were just forwarded
      setTimeout(loadInterceptedFlowIds, 200);
      return;
    }

    // When intercept is enabled, poll more frequently
    loadInterceptedFlowIds();
    const interval = setInterval(loadInterceptedFlowIds, 500); // Poll every 500ms for faster updates
    return () => clearInterval(interval);
  }, [interceptEnabled]);

  // Handle intercept toggle
  const handleInterceptToggle = async (enabled: boolean) => {
    try {
      // Optimistically update UI first for immediate feedback
      setInterceptEnabled(enabled);
      
      await api.setInterceptStatus(enabled);
      
      // Immediately check for intercepted flows after toggle
      if (enabled) {
        try {
          const data = await api.getInterceptedFlows();
          setInterceptedFlowIds(data.flow_ids);
        } catch (e) {
          // Ignore errors in this check
        }
      } else {
        // When disabling, clear immediately
        setInterceptedFlowIds([]);
      }
      
      toast.success(`Intercept ${enabled ? 'enabled' : 'disabled'}`, {
        description: enabled 
          ? 'Requests will be intercepted and paused'
          : 'All queued requests are being forwarded'
      });
    } catch (error) {
      // Revert on error
      setInterceptEnabled(!enabled);
      console.error("Failed to set intercept status:", error);
      toast.error("Failed to update intercept status", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };

  // Handle forwarding an intercepted flow
  const handleForwardFlow = async (flowId: string) => {
    try {
      const editedRequest = editedRequests[flowId];
      await api.forwardInterceptedFlow(flowId, editedRequest);
      
      // Remove from local state
      setInterceptedFlowIds(prev => prev.filter(id => id !== flowId));
      setEditingInterceptedFlow(null);
      delete editedRequests[flowId];
      
      toast.success("Request forwarded", {
        description: "The request has been sent to the server",
      });
    } catch (error) {
      console.error("Failed to forward flow:", error);
      toast.error("Failed to forward request", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };

  // Handle dropping an intercepted flow
  const handleDropFlow = async (flowId: string) => {
    try {
      await api.dropInterceptedFlow(flowId);
      
      // Remove from local state
      setInterceptedFlowIds(prev => prev.filter(id => id !== flowId));
      setEditingInterceptedFlow(null);
      delete editedRequests[flowId];
      
      toast.success("Request dropped", {
        description: "The request has been blocked and will not be sent",
      });
    } catch (error) {
      console.error("Failed to drop flow:", error);
      toast.error("Failed to drop request", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };

  // Load requests when project changes
  useEffect(() => {
    if (currentProject) {
      isInitialLoad.current = true;
      loadRequests().then(() => {
        // Mark initial load as complete after first load
        isInitialLoad.current = false;
      });
      // Poll for new requests every 2 seconds
      const interval = setInterval(() => {
        loadRequests(true); // Silent refresh
      }, 2000);
      return () => clearInterval(interval);
    } else {
      setRequests([]);
      setResponses({});
      setSelectedId(null);
      isInitialLoad.current = true;
    }
  }, [currentProject]);

  const loadCurrentProject = async () => {
    try {
      const data = await api.getCurrentProject();
      if (data.current_project_id && data.project) {
        setCurrentProject(data.project);
      } else {
        // Try to get the first project if no current project
        const projects = await api.getProjects();
        if (projects.length > 0) {
          const firstProject = projects[0];
          setCurrentProject(firstProject);
          await api.setCurrentProject(firstProject.id);
        }
      }
    } catch (error) {
      console.error("Failed to load current project:", error);
    }
  };

  const loadRequests = async (silent = false) => {
    if (!currentProject) return;
    
    if (!silent) {
      setIsLoading(true);
    }
    
    try {
      const backendRequests = await api.getProjectRequests(currentProject.id);

      // Transform requests
      const transformedRequests = backendRequests.map(transformRequest);
      setRequests(transformedRequests);
      
      // Transform responses
      const transformedResponses: Record<string, HttpResponse> = {};
      backendRequests.forEach((req) => {
        const response = transformResponse(req);
        if (response) {
          transformedResponses[String(req.id)] = response;
        }
      });
      setResponses(transformedResponses);
      
      // Only update selection on initial load or if current selection is no longer in list
      if (transformedRequests.length > 0) {
        if (isInitialLoad.current) {
          // On initial load, select the first request
          setSelectedId(transformedRequests[0].id);
          userHasSelected.current = false;
        } else if (!userHasSelected.current) {
          // During polling, only auto-select if user hasn't manually selected anything
          // and there's no current selection or it's not in the list
          setSelectedId((currentSelectedId) => {
            if (!currentSelectedId || !transformedRequests.find(r => r.id === currentSelectedId)) {
              return transformedRequests[0].id;
            }
            return currentSelectedId;
          });
        } else {
          // User has manually selected - only update if selection is no longer in list
          setSelectedId((currentSelectedId) => {
            if (currentSelectedId && transformedRequests.find(r => r.id === currentSelectedId)) {
              // Selection still exists, keep it
              return currentSelectedId;
            }
            // Selection no longer exists, select first
            return transformedRequests[0].id;
          });
        }
      } else {
        setSelectedId(null);
        userHasSelected.current = false;
      }
    } catch (error) {
      console.error("Failed to load requests:", error);
      if (!silent) {
        toast.error("Failed to load requests", {
          description: error instanceof Error ? error.message : "Unknown error",
        });
      }
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  };

  const handleOpenBrowser = async () => {
    setIsBrowserLoading(true);
    try {
      // Check if proxy is running, start it if not
      const proxyStatus = await api.getProxyStatus();
      if (!proxyStatus.running) {
        await api.startProxy();
      }
      
      // Start browser
      await api.startBrowser();
      toast.success("Browser opened", {
        description: "Browser is now running with proxy settings",
      });
    } catch (error) {
      console.error("Failed to open browser:", error);
      toast.error("Failed to open browser", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsBrowserLoading(false);
    }
  };
  
  const selectedRequest = requests.find(r => r.id === selectedId);
  const selectedResponse = selectedId ? responses[selectedId] : null;

  return (
    <div className="h-full p-4 flex flex-col gap-4">
      {/* Top Controls Bar */}
      <div className="flex items-center gap-4 px-4 py-3 rounded-lg border bg-card">
        {!isDocker && (
          <Button 
            size="sm" 
            className="gap-2"
            onClick={handleOpenBrowser}
            disabled={isBrowserLoading}
          >
            <Globe className="w-4 h-4" />
            {isBrowserLoading ? "Opening..." : "Open Browser"}
          </Button>
        )}

        <div className="h-6 w-px bg-border mx-2" />

        <div className="flex items-center gap-3">
          <Shield className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium">Intercept</span>
          <Switch 
            checked={interceptEnabled} 
            onCheckedChange={handleInterceptToggle}
          />
          {interceptEnabled && interceptedFlowIds.length > 0 && (
            <span className="text-xs bg-primary text-primary-foreground px-2 py-0.5 rounded-full font-medium">
              {interceptedFlowIds.length}
            </span>
          )}
        </div>

        <div className="h-6 w-px bg-border mx-2" />

        <Button
          size="sm"
          variant="outline"
          className="gap-2"
          onClick={() => setIsFilterDialogOpen(true)}
        >
          <Filter className="w-4 h-4" />
          Filters
          {(filters.hideStaticAssets || filters.excludedHosts.length > 0 || filters.includedHosts.length > 0 || filters.methods.length > 0 || filters.statusCodes.length > 0 || filters.textSearch.trim().length > 0) && (
            <span className="ml-1 h-2 w-2 rounded-full bg-primary" />
          )}
        </Button>

        <div className="h-6 w-px bg-border mx-2" />

        <Button
          size="sm"
          variant="outline"
          className="gap-2 border-red-300 bg-red-50 hover:bg-red-100 text-red-700 hover:text-red-800"
          onClick={handleClearAll}
          disabled={!currentProject || requests.length === 0 || isLoading}
        >
          <Trash2 className="w-4 h-4" />
          Clear All
        </Button>
      </div>

      {/* Main Content */}
      <ResizablePanelGroup direction="horizontal" className="flex-1 rounded-lg border bg-card">
        {/* Request List Panel */}
        <ResizablePanel defaultSize={35} minSize={25}>
          <div className="h-full flex flex-col">
            <div className="px-4 py-3 border-b bg-muted/30">
              <h2 className="text-sm font-semibold">HTTP History</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {currentProject 
                  ? `${filteredRequests.length} of ${requests.length} requests${requests.length === 0 ? '' : ''}`
                  : 'No project selected - Go to Projects tab to create or select a project'
                }
              </p>
            </div>
            {isLoading && requests.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-muted-foreground">
                <p className="text-sm">Loading requests...</p>
              </div>
            ) : requests.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground p-8">
                <Inbox className="w-12 h-12 mb-3 opacity-40" />
                <p className="text-sm text-center">
                  {currentProject 
                    ? 'No requests captured yet. Start the proxy and make some requests!'
                    : 'Select a project in the Projects tab to start capturing requests'
                  }
                </p>
              </div>
            ) : filteredRequests.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground p-8">
                <Filter className="w-12 h-12 mb-3 opacity-40" />
                <p className="text-sm text-center">
                  No requests match the current filters. Try adjusting your filter settings.
                </p>
              </div>
            ) : (
              <RequestList 
                requests={filteredRequests} 
                selectedId={selectedId} 
                interceptedFlowIds={interceptedFlowIds}
                onSelect={(id) => {
                  userHasSelected.current = true;
                  setSelectedId(id);
                }}
                onExcludeHost={(host) => {
                  const hostLower = host.toLowerCase();
                  if (!filters.excludedHosts.includes(hostLower)) {
                    setFilters({
                      ...filters,
                      excludedHosts: [...filters.excludedHosts, hostLower],
                    });
                  }
                }}
                onIncludeHost={(host) => {
                  const hostLower = host.toLowerCase();
                  if (!filters.includedHosts.includes(hostLower)) {
                    setFilters({
                      ...filters,
                      includedHosts: [...filters.includedHosts, hostLower],
                    });
                  }
                }}
              />
            )}
          </div>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Request/Response Viewer Panel */}
        <ResizablePanel defaultSize={65}>
          <ResizablePanelGroup direction="vertical">
            <ResizablePanel defaultSize={50} minSize={20}>
              {selectedRequest ? (
                (() => {
                  // Check if request is intercepted by flow_id
                  const isIntercepted = selectedRequest.flow_id 
                    ? interceptedFlowIds.includes(selectedRequest.flow_id)
                    : false;
                  const flowId = selectedRequest.flow_id;
                  
                  return (
                    <div className="h-full flex flex-col">
                      <div className="px-4 py-2 border-b bg-muted/30 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold">Request</h3>
                          {isIntercepted && (
                            <span className="text-xs bg-yellow-500 text-yellow-950 px-2 py-0.5 rounded-full flex items-center gap-1">
                              <AlertCircle className="w-3 h-3" />
                              Intercepted
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setShowRawRequest(!showRawRequest)}
                            className="h-7 px-2 text-xs"
                            title={showRawRequest ? "Show parsed view" : "Show raw view"}
                          >
                            {showRawRequest ? (
                              <>
                                <Eye className="w-3 h-3 mr-1" />
                                Parsed
                              </>
                            ) : (
                              <>
                                <Code className="w-3 h-3 mr-1" />
                                Raw
                              </>
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleCopyRequest(selectedRequest, flowId)}
                            disabled={!selectedRequest.raw || selectedRequest.raw.length === 0}
                            className="h-7 px-2 text-xs"
                          >
                            {requestCopied ? (
                              <>
                                <Check className="w-3 h-3 mr-1" />
                                Copied
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3 mr-1" />
                                Copy
                              </>
                            )}
                          </Button>
                          {isIntercepted && flowId && (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  if (editingInterceptedFlow === flowId) {
                                    setEditingInterceptedFlow(null);
                                  } else {
                                    setEditingInterceptedFlow(flowId);
                                  }
                                }}
                                className="h-7 px-2 text-xs"
                                title={editingInterceptedFlow === flowId ? "Exit edit mode" : "Edit request"}
                              >
                                {editingInterceptedFlow === flowId ? (
                                  <>
                                    <Eye className="w-3 h-3 mr-1" />
                                    View
                                  </>
                                ) : (
                                  <>
                                    <Edit2 className="w-3 h-3 mr-1" />
                                    Edit
                                  </>
                                )}
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleDropFlow(flowId)}
                                className="gap-2 border-red-300 bg-red-50 hover:bg-red-100 text-red-700 hover:text-red-800"
                              >
                                <X className="w-3 h-3" />
                                Drop
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => handleForwardFlow(flowId)}
                                className="gap-2"
                              >
                                <Send className="w-3 h-3" />
                                Forward
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                      <div className="flex-1 overflow-auto">
                        {isIntercepted && flowId ? (
                          editingInterceptedFlow === flowId ? (
                            // Edit mode: show textarea
                            <Textarea
                              value={editedRequests[flowId] || selectedRequest.raw || ''}
                              onChange={(e) => {
                                setEditedRequests(prev => ({
                                  ...prev,
                                  [flowId]: e.target.value
                                }));
                              }}
                              className="flex-1 resize-none border-0 rounded-none font-mono text-sm bg-transparent focus-visible:ring-0 h-full min-h-0"
                              placeholder="Edit your request here..."
                            />
                          ) : showRawRequest ? (
                            // Raw view mode
                            <div className="flex-1 overflow-auto bg-card">
                              <pre className="p-4 text-foreground/90 whitespace-pre-wrap break-words font-mono text-sm">
                                {editedRequests[flowId] || selectedRequest.raw || '(empty)'}
                              </pre>
                            </div>
                          ) : (
                            // Color-coded view mode (default)
                            <HttpViewer 
                              content={editedRequests[flowId] || selectedRequest.raw || ''} 
                              title=""
                            />
                          )
                        ) : showRawRequest ? (
                          <div className="flex-1 overflow-auto bg-card">
                            <pre className="p-4 text-foreground/90 whitespace-pre-wrap break-words font-mono text-sm">
                              {selectedRequest.raw || '(empty)'}
                            </pre>
                          </div>
                        ) : (
                          <HttpViewer 
                            content={selectedRequest.raw || ''} 
                            title=""
                          />
                        )}
                      </div>
                    </div>
                  );
                })()
              ) : (
                <div className="h-full flex flex-col">
                  <div className="px-4 py-2 border-b bg-muted/30">
                    <h3 className="text-sm font-semibold">Request</h3>
                  </div>
                  <div className="flex-1 flex items-center justify-center">
                    <EmptyState message="Select a request to view" />
                  </div>
                </div>
              )}
            </ResizablePanel>

            <ResizableHandle withHandle />

            <ResizablePanel defaultSize={50} minSize={20}>
              {selectedResponse ? (
                <HttpViewer 
                  content={selectedResponse.raw || ''} 
                  title="Response"
                  statusCode={selectedRequest?.status}
                />
              ) : (
                <div className="h-full flex flex-col">
                  <div className="px-4 py-2 border-b bg-muted/30 flex items-center gap-2">
                    <h3 className="text-sm font-semibold">Response</h3>
                    {selectedRequest?.status !== undefined && selectedRequest?.status !== null && (
                      <StatusCode status={selectedRequest.status} className="text-xs" />
                    )}
                  </div>
                  <div className="flex-1 flex items-center justify-center">
                    <EmptyState message="No response available" />
                  </div>
                </div>
              )}
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>
      </ResizablePanelGroup>

      {/* Filter Dialog */}
      <RequestFilters
        open={isFilterDialogOpen}
        onOpenChange={setIsFilterDialogOpen}
        filters={filters}
        onFiltersChange={setFilters}
      />
    </div>
  );
};

const EmptyState = ({ message }: { message: string }) => (
  <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
    <Inbox className="w-10 h-10 mb-2 opacity-40" />
    <p className="text-sm">{message}</p>
  </div>
);
