import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Copy, Check, Eye, Code } from "lucide-react";
import { useState, useMemo } from "react";
import { toast } from "sonner";
import { StatusCode } from "./StatusCode";
import { parseHttpContent } from "@/lib/requestTransform";

interface HttpViewerProps {
  content: string;
  className?: string;
  title?: string;
  statusCode?: number;
}

export const HttpViewer = ({ content, className, title, statusCode }: HttpViewerProps) => {
  const [copied, setCopied] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  const parsed = useMemo(() => {
    if (!content || showRaw) return null;
    return parseHttpContent(content);
  }, [content, showRaw]);

  const handleCopy = async () => {
    if (!content) return;
    
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.success("Copied to clipboard", {
        description: `${content.length} characters copied`,
      });
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error("Failed to copy", {
        description: "Could not copy to clipboard",
      });
    }
  };

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {title && (
        <div className="px-4 py-2 border-b bg-muted/30 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">{title}</h3>
            {statusCode !== undefined && statusCode !== null && (
              <StatusCode status={statusCode} className="text-xs" />
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowRaw(!showRaw)}
              className="h-7 px-2 text-xs"
              title={showRaw ? "Show parsed view" : "Show raw view"}
            >
              {showRaw ? (
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
              onClick={handleCopy}
              disabled={!content || content.length === 0}
              className="h-7 px-2 text-xs"
            >
              {copied ? (
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
          </div>
        </div>
      )}
      <div className="flex-1 overflow-auto bg-card">
        {!content ? (
          <div className="p-4 text-muted-foreground text-sm">(empty)</div>
        ) : parsed ? (
          <div className="p-4 font-mono text-sm">
            {/* Status/Request Line */}
            {(parsed.statusLine || parsed.requestLine) && (
              <div className="mb-2">
                <span className="text-primary font-semibold">
                  {parsed.statusLine || parsed.requestLine}
                </span>
              </div>
            )}

            {/* Headers */}
            {parsed.headers.length > 0 && (
              <div className="mb-4">
                {parsed.headers.map((header, index) => {
                  const colonIndex = header.raw.indexOf(':');
                  const headerName = colonIndex > 0 ? header.raw.substring(0, colonIndex) : header.name;
                  const headerValue = colonIndex > 0 ? header.raw.substring(colonIndex + 1) : header.value;
                  
                  return (
                    <div key={index} className="mb-1">
                      <span className="text-blue-600 dark:text-blue-400 font-semibold">{headerName}:</span>
                      <span className="text-green-700 dark:text-green-400 ml-2">{headerValue}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Separator */}
            {parsed.body && (
              <div className="my-2 border-t border-border"></div>
            )}

            {/* Body */}
            {parsed.body ? (
              <div className="mt-4">
                <div className="text-muted-foreground text-xs mb-2 uppercase tracking-wide">Body</div>
                <pre className="text-foreground whitespace-pre-wrap break-words">
                  {parsed.body}
                </pre>
              </div>
            ) : parsed.headers.length > 0 ? (
              <div className="mt-4 text-muted-foreground text-xs italic">(no body)</div>
            ) : null}
          </div>
        ) : (
          <pre className="p-4 text-foreground/90 whitespace-pre-wrap break-words font-mono text-sm">
            {content}
          </pre>
        )}
      </div>
    </div>
  );
};
