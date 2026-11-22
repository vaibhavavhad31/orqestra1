import { cn } from "@/lib/utils";

export const StatCard = ({ label, value, unit = "credits", hint, icon: Icon, children, testId, className }) => (
  <div data-testid={testId} className={cn("surface p-5 animate-fade-up", className)}>
    <div className="flex items-center justify-between">
      <span className="eyebrow">{label}</span>
      {Icon && <Icon className="h-4 w-4 text-slate-400" strokeWidth={1.75} />}
    </div>
    <div className="mt-3 flex items-baseline gap-1.5">
      <span data-testid={testId ? `${testId}-value` : undefined} className="num text-2xl sm:text-[28px] font-semibold text-slate-900">
        {value}
      </span>
      {unit && <span className="text-xs text-slate-500">{unit}</span>}
    </div>
    {hint && <p className="mt-1.5 text-xs text-slate-500">{hint}</p>}
    {children && <div className="mt-3">{children}</div>}
  </div>
);
