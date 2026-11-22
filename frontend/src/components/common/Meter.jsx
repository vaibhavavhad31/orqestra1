import { cn } from "@/lib/utils";

export const Meter = ({ value, className, testId }) => {
  const pct = Math.min(100, Math.max(0, value || 0));
  const color = value >= 85 ? "bg-amber-500" : value < 40 ? "bg-sky-500" : "bg-indigo-500";
  return (
    <div data-testid={testId} className={cn("h-1.5 w-full overflow-hidden rounded-full bg-slate-100", className)}>
      <div className={cn("h-full rounded-full transition-[width] duration-500", color)} style={{ width: `${pct}%` }} />
    </div>
  );
};
