import { useState, useEffect, useCallback } from "react";
import { api, Finding } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Trash2, RefreshCw, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-600 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-yellow-500 text-black",
  low: "bg-blue-500 text-white",
  info: "bg-gray-400 text-white",
};

const TOOLS = ["generate_poc", "active_scan", "static_analyze", "network_map"];

export const ScannerTab = () => {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [toolFilter, setToolFilter] = useState<string>("all");
  const [currentProjectId, setCurrentProjectId] = useState<number | null>(null);

  useEffect(() => {
    api.getCurrentProject().then((r) => {
      if (r.project) setCurrentProjectId(r.project.id);
    }).catch(() => {});
  }, []);

  const loadFindings = useCallback(async () => {
    if (!currentProjectId) return;
    setLoading(true);
    try {
      const data = await api.getFindings(
        currentProjectId,
        severityFilter !== "all" ? severityFilter : undefined,
        toolFilter !== "all" ? toolFilter : undefined,
      );
      setFindings(data);
    } catch (e) {
      toast.error("Failed to load findings");
    } finally {
      setLoading(false);
    }
  }, [currentProjectId, severityFilter, toolFilter]);

  useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  const handleDelete = async (findingId: number) => {
    if (!currentProjectId) return;
    try {
      await api.deleteFinding(currentProjectId, findingId);
      setFindings((prev) => prev.filter((f) => f.id !== findingId));
      toast.success("Finding deleted");
    } catch {
      toast.error("Failed to delete finding");
    }
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Toolbar */}
      <div className="border-b border-border px-4 py-2 flex items-center gap-3 bg-card">
        <ShieldAlert className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium">Security Findings</span>
        <div className="flex items-center gap-2 ml-4">
          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger className="h-7 text-xs w-28">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="info">Info</SelectItem>
            </SelectContent>
          </Select>
          <Select value={toolFilter} onValueChange={setToolFilter}>
            <SelectTrigger className="h-7 text-xs w-36">
              <SelectValue placeholder="Tool" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All tools</SelectItem>
              {TOOLS.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button variant="ghost" size="sm" onClick={loadFindings} disabled={loading} className="ml-auto h-7">
          <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
        </Button>
        <span className="text-xs text-muted-foreground">{findings.length} finding{findings.length !== 1 ? "s" : ""}</span>
      </div>

      {/* Table */}
      {findings.length === 0 ? (
        <div className="flex flex-col items-center justify-center flex-1 text-muted-foreground">
          <ShieldAlert className="h-16 w-16 opacity-20 mb-4" />
          <p className="text-sm">No findings yet. Use the Agent tab to run security tools.</p>
        </div>
      ) : (
        <ScrollArea className="flex-1">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-card border-b border-border">
              <tr className="text-left text-xs text-muted-foreground">
                <th className="px-3 py-2 w-24">Severity</th>
                <th className="px-3 py-2 w-32">Tool</th>
                <th className="px-3 py-2 w-32">Type</th>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2 max-w-xs">Evidence</th>
                <th className="px-3 py-2 w-36">Timestamp</th>
                <th className="px-3 py-2 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f) => (
                <tr key={f.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="px-3 py-2">
                    <Badge className={`text-xs ${SEVERITY_COLORS[f.severity] || "bg-gray-400 text-white"}`}>
                      {f.severity}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground font-mono">{f.tool}</td>
                  <td className="px-3 py-2 text-xs font-mono truncate max-w-[128px]" title={f.vuln_type || ""}>{f.vuln_type || "—"}</td>
                  <td className="px-3 py-2 font-medium text-xs">{f.title}</td>
                  <td className="px-3 py-2 text-xs font-mono text-muted-foreground truncate max-w-xs" title={f.evidence || ""}>
                    {f.evidence || "—"}
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(f.timestamp).toLocaleString()}
                  </td>
                  <td className="px-3 py-2">
                    <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handleDelete(f.id)}>
                      <Trash2 className="h-3 w-3 text-destructive" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollArea>
      )}
    </div>
  );
};
