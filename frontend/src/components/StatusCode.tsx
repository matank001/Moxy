import { cn } from "@/lib/utils";

interface StatusCodeProps {
  status?: number;
  className?: string;
}

export const StatusCode = ({ status, className }: StatusCodeProps) => {
  const getStatusClass = () => {
    if (status === undefined || status === null) {
      return "text-muted-foreground";
    }
    if (status >= 200 && status < 300) return "status-2xx";
    if (status >= 300 && status < 400) return "status-3xx";
    if (status >= 400 && status < 500) return "status-4xx";
    return "status-5xx";
  };

  return (
    <span className={cn("font-mono font-semibold", getStatusClass(), className)}>
      {status !== undefined && status !== null ? status : "—"}
    </span>
  );
};
