import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { X } from "lucide-react";

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'];
const STATUS_CODE_RANGES = [
  { value: '2xx', label: '2xx (Success)', description: '200-299' },
  { value: '3xx', label: '3xx (Redirection)', description: '300-399' },
  { value: '4xx', label: '4xx (Client Error)', description: '400-499' },
  { value: '5xx', label: '5xx (Server Error)', description: '500-599' },
];

interface RequestFilters {
  hideStaticAssets: boolean;
  excludedHosts: string[];
  includedHosts: string[];
  methods: string[];
  statusCodes: string[];
  textSearch: string;
  textSearchScope: 'both' | 'request' | 'response';
}

interface RequestFiltersProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filters: RequestFilters;
  onFiltersChange: (filters: RequestFilters) => void;
}

export const RequestFilters = ({
  open,
  onOpenChange,
  filters,
  onFiltersChange,
}: RequestFiltersProps) => {
  const [excludedHostInput, setExcludedHostInput] = useState("");
  const [includedHostInput, setIncludedHostInput] = useState("");

  const handleFilterChange = (key: keyof RequestFilters, value: boolean | string | string[]) => {
    onFiltersChange({
      ...filters,
      [key]: value,
    });
  };

  const handleMethodToggle = (method: string) => {
    const currentMethods = filters.methods;
    if (currentMethods.includes(method)) {
      handleFilterChange("methods", currentMethods.filter((m) => m !== method));
    } else {
      handleFilterChange("methods", [...currentMethods, method]);
    }
  };

  const handleStatusCodeToggle = (range: string) => {
    const currentRanges = filters.statusCodes;
    if (currentRanges.includes(range)) {
      handleFilterChange("statusCodes", currentRanges.filter((r) => r !== range));
    } else {
      handleFilterChange("statusCodes", [...currentRanges, range]);
    }
  };

  const handleAddExcludedHost = () => {
    const host = excludedHostInput.trim().toLowerCase();
    if (host && !filters.excludedHosts.includes(host)) {
      handleFilterChange("excludedHosts", [...filters.excludedHosts, host]);
      setExcludedHostInput("");
    }
  };

  const handleRemoveExcludedHost = (hostToRemove: string) => {
    handleFilterChange(
      "excludedHosts",
      filters.excludedHosts.filter((h) => h !== hostToRemove)
    );
  };

  const handleAddIncludedHost = () => {
    const host = includedHostInput.trim().toLowerCase();
    if (host && !filters.includedHosts.includes(host)) {
      handleFilterChange("includedHosts", [...filters.includedHosts, host]);
      setIncludedHostInput("");
    }
  };

  const handleRemoveIncludedHost = (hostToRemove: string) => {
    handleFilterChange(
      "includedHosts",
      filters.includedHosts.filter((h) => h !== hostToRemove)
    );
  };

  const handleExcludedHostInputKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAddExcludedHost();
    }
  };

  const handleIncludedHostInputKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAddIncludedHost();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Filter Requests</DialogTitle>
          <DialogDescription>
            Configure filters to control which requests are displayed
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6 py-4 overflow-y-auto flex-1 min-h-0">
          {/* Text Search Filter */}
          <div className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="text-search" className="text-sm font-medium">
                Text Search
              </Label>
              <p className="text-xs text-muted-foreground">
                Search for text in requests and/or responses. Case-insensitive.
              </p>
            </div>
            <Input
              id="text-search"
              placeholder="Enter search text..."
              value={filters.textSearch}
              onChange={(e) => handleFilterChange("textSearch", e.target.value)}
              className="font-mono text-sm"
            />
            <RadioGroup
              value={filters.textSearchScope}
              onValueChange={(value) => handleFilterChange("textSearchScope", value as 'both' | 'request' | 'response')}
              className="flex gap-4"
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="both" id="scope-both" />
                <Label htmlFor="scope-both" className="text-sm cursor-pointer">
                  Both
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="request" id="scope-request" />
                <Label htmlFor="scope-request" className="text-sm cursor-pointer">
                  Request only
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="response" id="scope-response" />
                <Label htmlFor="scope-response" className="text-sm cursor-pointer">
                  Response only
                </Label>
              </div>
            </RadioGroup>
          </div>

          <div className="flex items-center justify-between space-x-2">
            <div className="space-y-0.5">
              <Label htmlFor="hide-static-assets" className="text-sm font-medium">
                Hide Static Assets
              </Label>
              <p className="text-xs text-muted-foreground">
                Exclude .js, .png, .jpg, .css, .svg, .woff, .woff2, .ttf, .ico, .gif, .webp, and other static files
              </p>
            </div>
            <Switch
              id="hide-static-assets"
              checked={filters.hideStaticAssets}
              onCheckedChange={(checked) =>
                handleFilterChange("hideStaticAssets", checked)
              }
            />
          </div>

          <div className="space-y-3">
            <div className="space-y-2">
              <Label className="text-sm font-medium">
                HTTP Methods
              </Label>
              <p className="text-xs text-muted-foreground">
                Filter requests by HTTP method. Leave all unchecked to show all methods.
              </p>
            </div>
            
            <div className="flex flex-wrap gap-3">
              {HTTP_METHODS.map((method) => (
                <div key={method} className="flex items-center space-x-2">
                  <Checkbox
                    id={`method-${method}`}
                    checked={filters.methods.includes(method)}
                    onCheckedChange={() => handleMethodToggle(method)}
                  />
                  <Label
                    htmlFor={`method-${method}`}
                    className="text-sm font-mono cursor-pointer"
                  >
                    {method}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="space-y-2">
              <Label className="text-sm font-medium">
                Status Codes
              </Label>
              <p className="text-xs text-muted-foreground">
                Filter requests by HTTP status code range. Leave all unchecked to show all status codes.
              </p>
            </div>
            
            <div className="flex flex-wrap gap-3">
              {STATUS_CODE_RANGES.map((range) => (
                <div key={range.value} className="flex items-center space-x-2">
                  <Checkbox
                    id={`status-${range.value}`}
                    checked={filters.statusCodes.includes(range.value)}
                    onCheckedChange={() => handleStatusCodeToggle(range.value)}
                  />
                  <Label
                    htmlFor={`status-${range.value}`}
                    className="text-sm cursor-pointer"
                  >
                    <span className="font-semibold">{range.label}</span>
                    <span className="text-muted-foreground ml-1">({range.description})</span>
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="excluded-hosts" className="text-sm font-medium">
                Excluded Hosts
              </Label>
              <p className="text-xs text-muted-foreground">
                Hosts to exclude from the request list. Add hosts using the input below.
              </p>
            </div>
            
            <div className="space-y-2">
              <div className="flex gap-2">
                <div className="flex-1">
                  <Textarea
                    id="excluded-hosts"
                    placeholder="Enter hostname (e.g., example.com)"
                    value={excludedHostInput}
                    onChange={(e) => setExcludedHostInput(e.target.value)}
                    onKeyDown={handleExcludedHostInputKeyDown}
                    className="min-h-[60px] font-mono text-sm"
                  />
                </div>
                <Button
                  type="button"
                  onClick={handleAddExcludedHost}
                  disabled={!excludedHostInput.trim()}
                  size="sm"
                  className="self-start"
                >
                  Add
                </Button>
              </div>

              {filters.excludedHosts.length > 0 && (
                <div className="flex flex-wrap gap-2 p-3 rounded-md border bg-muted/30 min-h-[60px]">
                  {filters.excludedHosts.map((host) => (
                    <div
                      key={host}
                      className="flex items-center gap-1 px-2 py-1 rounded-md bg-background border text-sm font-mono"
                    >
                      <span>{host}</span>
                      <button
                        onClick={() => handleRemoveExcludedHost(host)}
                        className="hover:bg-muted-foreground/20 rounded p-0.5"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="included-hosts" className="text-sm font-medium">
                Included Hosts (Scope)
              </Label>
              <p className="text-xs text-muted-foreground">
                Only show requests from these hosts. Leave empty to show all hosts.
              </p>
            </div>
            
            <div className="space-y-2">
              <div className="flex gap-2">
                <div className="flex-1">
                  <Textarea
                    id="included-hosts"
                    placeholder="Enter hostname (e.g., api.example.com)"
                    value={includedHostInput}
                    onChange={(e) => setIncludedHostInput(e.target.value)}
                    onKeyDown={handleIncludedHostInputKeyDown}
                    className="min-h-[60px] font-mono text-sm"
                  />
                </div>
                <Button
                  type="button"
                  onClick={handleAddIncludedHost}
                  disabled={!includedHostInput.trim()}
                  size="sm"
                  className="self-start"
                >
                  Add
                </Button>
              </div>

              {filters.includedHosts.length > 0 && (
                <div className="flex flex-wrap gap-2 p-3 rounded-md border bg-green-500/10 border-green-500/20 min-h-[60px]">
                  {filters.includedHosts.map((host) => (
                    <div
                      key={host}
                      className="flex items-center gap-1 px-2 py-1 rounded-md bg-background border border-green-500/30 text-sm font-mono"
                    >
                      <span>{host}</span>
                      <button
                        onClick={() => handleRemoveIncludedHost(host)}
                        className="hover:bg-muted-foreground/20 rounded p-0.5"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
