import { HttpRequest } from "@/data/demoData";
import { MethodBadge } from "./MethodBadge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuShortcut,
  ContextMenuLabel,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { Terminal, Repeat, Copy, Trash2, Ban, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { useResender } from "@/contexts/ResenderContext";
import { generateCurl } from "@/lib/requestTransform";

interface RequestListProps {
  requests: HttpRequest[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onExcludeHost?: (host: string) => void;
  onIncludeHost?: (host: string) => void;
  interceptedFlowIds?: string[];
}


export const RequestList = ({ 
  requests, 
  selectedId, 
  onSelect,
  onExcludeHost,
  onIncludeHost,
  interceptedFlowIds = []
}: RequestListProps) => {
  const { addTab, navigateToResender } = useResender();

  // Helper function to check if a request is intercepted
  const isRequestIntercepted = (request: HttpRequest): boolean => {
    if (!request.flow_id) {
      return false;
    }
    const isIntercepted = interceptedFlowIds.includes(request.flow_id);
    return isIntercepted;
  };

  const handleCopyAsCurl = (request: HttpRequest) => {
    const curl = generateCurl(request);
    navigator.clipboard.writeText(curl);
    toast.success("Copied to clipboard", {
      description: "cURL command copied successfully"
    });
  };

  const handleCopyUrl = (request: HttpRequest) => {
    const url = `https://${request.host}${request.path}`;
    navigator.clipboard.writeText(url);
    toast.success("URL copied", {
      description: url
    });
  };

  const handleSendToResender = async (request: HttpRequest) => {
    try {
      await addTab(request);
      navigateToResender();
      toast.success("Sent to Resender", {
        description: `${request.method} ${request.path}`
      });
    } catch (error) {
      toast.error("Failed to send to Resender", {
        description: error instanceof Error ? error.message : String(error)
      });
    }
  };

  return (
    <ScrollArea className="h-full">
      <div className="divide-y divide-border">
        {requests.map((request, index) => (
          <ContextMenu key={request.id}>
            <ContextMenuTrigger>
              <div
                onClick={() => onSelect(request.id)}
                className={cn(
                  "w-full text-left px-4 py-3 transition-all duration-150 hover:bg-muted/70 cursor-pointer",
                  "focus:outline-none focus:bg-muted",
                  selectedId === request.id && "bg-primary/5 border-l-2 border-l-primary",
                  "animate-fade-in"
                )}
                style={{ animationDelay: `${index * 30}ms` }}
              >
                <div className="flex items-center gap-3">
                  {isRequestIntercepted(request) && (
                    <span 
                      className="h-2.5 w-2.5 rounded-full bg-primary flex-shrink-0 shadow-sm shadow-primary/50" 
                      title="Intercepted - waiting for forward"
                    />
                  )}
                  <MethodBadge method={request.method} />
                  <span className="flex-1 font-mono text-sm truncate text-foreground/80">
                    {request.host}
                  </span>
                </div>
                <div className="mt-1.5 flex items-center gap-2">
                  <span className="font-mono text-xs text-muted-foreground truncate flex-1">
                    {request.path}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {format(request.timestamp, "HH:mm:ss")}
                  </span>
                </div>
              </div>
            </ContextMenuTrigger>
            <ContextMenuContent className="w-56 bg-card/95 backdrop-blur-sm border-primary/20 shadow-lg shadow-primary/5">
              <ContextMenuLabel className="text-primary font-mono text-xs">
                {request.method} {request.host}
              </ContextMenuLabel>
              <ContextMenuSeparator className="bg-border/50" />
              
              <ContextMenuItem 
                onClick={() => handleCopyAsCurl(request)}
                className="gap-3 cursor-pointer focus:bg-primary/10 focus:text-foreground"
              >
                <Terminal className="w-4 h-4 text-primary" />
                <span>Copy as cURL</span>
                <ContextMenuShortcut>⌘C</ContextMenuShortcut>
              </ContextMenuItem>
              
              <ContextMenuItem 
                onClick={() => handleSendToResender(request)}
                className="gap-3 cursor-pointer focus:bg-primary/10 focus:text-foreground"
              >
                <Repeat className="w-4 h-4 text-primary" />
                <span>Send to Resender</span>
                <ContextMenuShortcut>⌘R</ContextMenuShortcut>
              </ContextMenuItem>
              
              <ContextMenuSeparator className="bg-border/50" />
              
              <ContextMenuItem 
                onClick={() => handleCopyUrl(request)}
                className="gap-3 cursor-pointer focus:bg-muted"
              >
                <Copy className="w-4 h-4 text-muted-foreground" />
                <span>Copy URL</span>
              </ContextMenuItem>
              
              {(onExcludeHost || onIncludeHost) && (
                <>
                  <ContextMenuSeparator className="bg-border/50" />
                  {onIncludeHost && (
                    <ContextMenuItem 
                      onClick={() => {
                        onIncludeHost(request.host);
                        toast.success("Host included", {
                          description: `${request.host} has been added to included hosts (scope)`
                        });
                      }}
                      className="gap-3 cursor-pointer focus:bg-green-500/10 focus:text-green-600 dark:focus:text-green-400"
                    >
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                      <span>Include Host (Scope)</span>
                    </ContextMenuItem>
                  )}
                  {onExcludeHost && (
                    <ContextMenuItem 
                      onClick={() => {
                        onExcludeHost(request.host);
                        toast.success("Host excluded", {
                          description: `${request.host} has been added to excluded hosts`
                        });
                      }}
                      className="gap-3 cursor-pointer focus:bg-orange-500/10 focus:text-orange-600 dark:focus:text-orange-400"
                    >
                      <Ban className="w-4 h-4 text-orange-500" />
                      <span>Exclude Host</span>
                    </ContextMenuItem>
                  )}
                </>
              )}
              
              <ContextMenuSeparator className="bg-border/50" />
              
              <ContextMenuItem className="gap-3 cursor-pointer text-destructive focus:bg-destructive/10 focus:text-destructive">
                <Trash2 className="w-4 h-4" />
                <span>Delete Request</span>
              </ContextMenuItem>
            </ContextMenuContent>
          </ContextMenu>
        ))}
      </div>
    </ScrollArea>
  );
};
