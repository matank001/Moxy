import { useState, useEffect, useRef } from "react";
import { useResender } from "@/contexts/ResenderContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { HttpViewer } from "@/components/HttpViewer";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { X, Send, Plus, Pencil, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

export const ResenderTab = () => {
  const { 
    tabs, 
    activeTabId, 
    setActiveTab, 
    removeTab, 
    updateTabRequest, 
    updateTabName,
    updateTabHost,
    updateTabPort,
    sendRequest,
    setActiveVersion,
    addTab 
  } = useResender();
  
  const [editingTabId, setEditingTabId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const editInputRef = useRef<HTMLInputElement>(null);
  const [editingHost, setEditingHost] = useState<string>("");
  const [editingPort, setEditingPort] = useState<string>("");
  const hostInputRef = useRef<HTMLInputElement>(null);
  const portInputRef = useRef<HTMLInputElement>(null);
  const [isAiCopilotLoading, setIsAiCopilotLoading] = useState(false);
  const [isAiCopilotOpen, setIsAiCopilotOpen] = useState(false);
  const [aiCopilotPrompt, setAiCopilotPrompt] = useState("");

  // Dynamic sizing based on tab count
  const tabCount = tabs.length;
  const isCompact = tabCount > 6;
  const isVeryCompact = tabCount > 12;

  useEffect(() => {
    if (editingTabId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingTabId]);

  const handleSend = async (id: string) => {
    try {
      await sendRequest(id);
    } catch (error) {
      toast.error("Failed to send request", { description: error instanceof Error ? error.message : String(error) });
    }
  };

  const handleAiCopilot = async (id: string, prompt: string) => {
    const tab = tabs.find(t => t.id === id);
    if (!tab) return;

    if (!prompt.trim()) {
      toast.error("No prompt provided", { description: "Please enter a prompt for the AI copilot" });
      return;
    }

    // Combine the current request text with the user's prompt
    const currentText = tab.editedRaw;
    const combinedText = currentText ? `${currentText}\n\n---\n\nUser request: ${prompt}` : prompt;

    setIsAiCopilotLoading(true);
    try {
      const newText = await api.resenderAgent(combinedText);
      updateTabRequest(id, newText);
      toast.success("AI copilot completed", { description: "Request text has been updated" });
      setIsAiCopilotOpen(false);
      setAiCopilotPrompt("");
    } catch (error) {
      toast.error("AI copilot failed", { description: error instanceof Error ? error.message : String(error) });
    } finally {
      setIsAiCopilotLoading(false);
    }
  };

  const startEditing = (tab: { id: string; name: string }) => {
    setEditingTabId(tab.id);
    setEditingName(tab.name);
  };

  const finishEditing = async () => {
    if (editingTabId && editingName.trim()) {
      const newName = editingName.trim();
      try {
        await updateTabName(editingTabId, newName);
        // Clear editing state after successful update
        setEditingTabId(null);
        setEditingName("");
      } catch (error) {
        console.error("Failed to update tab name:", error);
        toast.error("Failed to rename tab", {
          description: error instanceof Error ? error.message : "Unknown error",
        });
        // Keep editing state on error so user can try again
      }
    } else {
      setEditingTabId(null);
      setEditingName("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      finishEditing();
    } else if (e.key === 'Escape') {
      setEditingTabId(null);
      setEditingName("");
    }
  };

  const activeTab = tabs.find(t => t.id === activeTabId);

  // Sync editing host/port with active tab
  useEffect(() => {
    if (activeTab) {
      setEditingHost(activeTab.host);
      setEditingPort(activeTab.port);
    }
  }, [activeTab?.id, activeTab?.host, activeTab?.port]);

  const handleHostBlur = async () => {
    if (activeTab && editingHost !== activeTab.host) {
      try {
        await updateTabHost(activeTab.id, editingHost);
      } catch (error) {
        console.error("Failed to update host:", error);
        // Revert to original value on error
        setEditingHost(activeTab.host);
      }
    }
  };

  const handlePortBlur = async () => {
    if (activeTab && editingPort !== activeTab.port) {
      try {
        await updateTabPort(activeTab.id, editingPort);
      } catch (error) {
        console.error("Failed to update port:", error);
        // Revert to original value on error
        setEditingPort(activeTab.port);
      }
    }
  };

  const handleHostKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.currentTarget.blur();
    }
  };

  const handlePortKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.currentTarget.blur();
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Tab Bar */}
      <div className="border-b bg-muted/30 px-2 py-2 max-h-32 overflow-y-auto">
        <div className="flex flex-wrap items-start gap-1">
          {/* New Tab Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              try {
                await addTab();
              } catch (error) {
                toast.error("Failed to create tab", {
                  description: error instanceof Error ? error.message : String(error)
                });
              }
            }}
            className={cn(
              "gap-1 text-muted-foreground hover:text-foreground shrink-0",
              isCompact ? "px-1.5 h-6 text-xs" : "px-2 h-8"
            )}
          >
            <Plus className={cn(isCompact ? "w-3 h-3" : "w-4 h-4")} />
            {!isVeryCompact && "New"}
          </Button>
          
          <div className="w-px h-6 bg-border mx-1 shrink-0" />
          
          {tabs.map(tab => (
            <div key={tab.id} className="flex flex-col shrink-0">
              <ContextMenu>
                <ContextMenuTrigger>
                  <div
                    className={cn(
                      "group flex items-center gap-1.5 font-mono cursor-pointer transition-colors rounded-t-md",
                      isVeryCompact ? "px-1.5 py-1 text-[10px]" : isCompact ? "px-2 py-1 text-xs" : "px-3 py-1.5 text-sm",
                      activeTabId === tab.id 
                        ? 'bg-primary text-primary-foreground' 
                        : 'bg-card hover:bg-muted border border-b-0'
                    )}
                    onClick={() => setActiveTab(tab.id)}
                    onDoubleClick={(e) => {
                      e.stopPropagation();
                      startEditing(tab);
                    }}
                  >
                    {editingTabId === tab.id ? (
                      <input
                        ref={editInputRef}
                        type="text"
                        value={editingName}
                        onChange={(e) => setEditingName(e.target.value)}
                        onBlur={finishEditing}
                        onKeyDown={handleKeyDown}
                        className={cn(
                          "bg-transparent border-b border-current outline-none",
                          isCompact ? "w-14 text-xs" : "w-20 text-sm"
                        )}
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <span className="truncate max-w-20">{tab.name}</span>
                    )}
                    {!isVeryCompact && tab.versions.length > 0 && (
                      <span className="text-[10px] opacity-70">{tab.versions.length}</span>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeTab(tab.id);
                      }}
                      className={cn(
                        "opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-background/20",
                        activeTabId === tab.id && 'hover:bg-primary-foreground/20'
                      )}
                    >
                      <X className={cn(isCompact ? "w-2.5 h-2.5" : "w-3 h-3")} />
                    </button>
                  </div>
                </ContextMenuTrigger>
                <ContextMenuContent className="w-40 bg-card/95 backdrop-blur-sm border-primary/20">
                  <ContextMenuItem 
                    onClick={() => startEditing(tab)}
                    className="gap-2 cursor-pointer"
                  >
                    <Pencil className="w-4 h-4" />
                    Rename Tab
                  </ContextMenuItem>
                </ContextMenuContent>
              </ContextMenu>
              
              {/* History Timeline */}
              {activeTabId === tab.id && tab.versions.length > 0 && (
                <div className="flex items-center gap-0.5 px-1.5 py-1 bg-card border-x rounded-b-md">
                  <TooltipProvider delayDuration={200}>
                    {tab.versions.map((version, index) => (
                      <Tooltip key={version.id}>
                        <TooltipTrigger asChild>
                          <button
                            onClick={() => setActiveVersion(tab.id, version.id)}
                            className={cn(
                              "w-2.5 h-2.5 rounded-full transition-all hover:scale-125",
                              tab.activeVersionId === version.id
                                ? "bg-primary ring-2 ring-primary/30"
                                : "bg-muted-foreground/40 hover:bg-muted-foreground"
                            )}
                          />
                        </TooltipTrigger>
                        <TooltipContent side="bottom" className="text-xs">
                          <p className="font-semibold">#{index + 1}</p>
                          <p className="text-muted-foreground">
                            {format(version.timestamp, "HH:mm:ss")}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    ))}
                  </TooltipProvider>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Active Tab Content */}
      {activeTab ? (
        <div className="flex-1 flex flex-col min-h-0 p-4">
          {/* Controls Bar */}
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center gap-2">
              <Input 
                ref={hostInputRef}
                value={editingHost}
                onChange={(e) => setEditingHost(e.target.value)}
                onBlur={handleHostBlur}
                onKeyDown={handleHostKeyDown}
                placeholder="Host"
                className="w-48 h-9 font-mono text-sm"
              />
              <span className="text-muted-foreground">:</span>
              <Input 
                ref={portInputRef}
                value={editingPort}
                onChange={(e) => setEditingPort(e.target.value)}
                onBlur={handlePortBlur}
                onKeyDown={handlePortKeyDown}
                placeholder="Port"
                className="w-20 h-9 font-mono text-sm"
              />
            </div>
            <Button 
              onClick={() => handleSend(activeTab.id)} 
              className="gap-2"
              disabled={activeTab.isLoading}
            >
              <Send className="w-4 h-4" />
              Send
            </Button>
            
            {activeTab.versions.length > 0 && (
              <span className="text-xs text-muted-foreground ml-auto">
                {activeTab.versions.length} {activeTab.versions.length === 1 ? 'send' : 'sends'}
                {activeTab.activeVersionId && (
                  <> • #{activeTab.versions.findIndex(v => v.id === activeTab.activeVersionId) + 1}</>
                )}
              </span>
            )}
          </div>

          <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
            {/* Request Editor */}
            <div className="flex flex-col border rounded-lg bg-card overflow-hidden">
              <div className="px-4 py-2 border-b bg-muted/30 flex items-center justify-between">
                <h3 className="text-sm font-semibold">Request</h3>
                <Popover open={isAiCopilotOpen} onOpenChange={setIsAiCopilotOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={isAiCopilotLoading}
                      className="h-6 px-2 gap-1 text-xs"
                    >
                      <Sparkles className="w-3 h-3" />
                      AI Copilot
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-3" align="end">
                    <div className="space-y-2">
                      <div className="text-sm font-medium">AI Copilot</div>
                      <Textarea
                        value={aiCopilotPrompt}
                        onChange={(e) => setAiCopilotPrompt(e.target.value)}
                        placeholder="Describe what you want to do with the request. The AI can browse former requests from the database to help modify your request. Examples: 'Change method to POST', 'Add auth header like the login request', 'Update body based on similar requests'..."
                        className="min-h-[80px] text-sm"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                            e.preventDefault();
                            if (activeTab && aiCopilotPrompt.trim()) {
                              handleAiCopilot(activeTab.id, aiCopilotPrompt);
                            }
                          }
                        }}
                      />
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setIsAiCopilotOpen(false);
                            setAiCopilotPrompt("");
                          }}
                          disabled={isAiCopilotLoading}
                          className="h-7 text-xs"
                        >
                          Cancel
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => activeTab && handleAiCopilot(activeTab.id, aiCopilotPrompt)}
                          disabled={isAiCopilotLoading || !aiCopilotPrompt.trim()}
                          className="h-7 text-xs"
                        >
                          {isAiCopilotLoading ? "Processing..." : "Apply"}
                        </Button>
                      </div>
                    </div>
                  </PopoverContent>
                </Popover>
              </div>
              <Textarea
                value={activeTab.editedRaw}
                onChange={(e) => updateTabRequest(activeTab.id, e.target.value)}
                className="flex-1 resize-none border-0 rounded-none font-mono text-sm bg-transparent focus-visible:ring-0"
                placeholder="Edit your request here..."
              />
            </div>

            {/* Response Viewer */}
            <div className="flex flex-col border rounded-lg bg-card overflow-hidden">
              {activeTab.isLoading ? (
                <>
                  <div className="px-4 py-2 border-b bg-muted/30">
                    <h3 className="text-sm font-semibold">Response</h3>
                  </div>
                  <div className="flex-1 flex items-center justify-center text-muted-foreground">
                    <p className="text-sm">Sending request...</p>
                  </div>
                </>
              ) : activeTab.response ? (
                <HttpViewer content={activeTab.response.raw} title="Response" />
              ) : (
                <>
                  <div className="px-4 py-2 border-b bg-muted/30">
                    <h3 className="text-sm font-semibold">Response</h3>
                  </div>
                  <div className="flex-1 flex items-center justify-center text-muted-foreground">
                    <p className="text-sm">Click Send to see response</p>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
          <Plus className="w-16 h-16 mb-4 opacity-30" />
          <h3 className="text-lg font-medium mb-2">No tabs open</h3>
          <p className="text-sm text-center max-w-md mb-4">
            Create a new tab to start crafting and sending requests.
          </p>
          <Button 
            onClick={async () => {
              try {
                await addTab();
              } catch (error) {
                toast.error("Failed to create tab", {
                  description: error instanceof Error ? error.message : String(error)
                });
              }
            }} 
            className="gap-2"
          >
            <Plus className="w-4 h-4" />
            New Tab
          </Button>
        </div>
      )}
    </div>
  );
};
