import { cn } from "@/lib/utils";

interface MethodBadgeProps {
  method: string;
  className?: string;
}

export const MethodBadge = ({ method, className }: MethodBadgeProps) => {
  const methodClass = `method-${method.toLowerCase()}`;
  
  return (
    <span className={cn("method-badge", methodClass, className)}>
      {method}
    </span>
  );
};
