import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Copy, Check } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { StatusCode } from "./StatusCode";

interface HttpViewerProps {
  content: string;
  className?: string;
  title?: string;
  statusCode?: number;
}

export const HttpViewer = ({ content, className, title, statusCode }: HttpViewerProps) => {
  const [copied, setCopied] = useState(false);

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
      )}
      <div className="flex-1 overflow-auto">
        <pre className="http-viewer p-4 pb-8 text-foreground/90 whitespace-pre-wrap break-words font-mono text-sm">
          {content || '(empty)'}
        </pre>
      </div>
    </div>
  );
};
