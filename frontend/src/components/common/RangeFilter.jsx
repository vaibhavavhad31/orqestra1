import { cn } from "@/lib/utils";

const OPTIONS = [7, 30, 90];

export const RangeFilter = ({ value, onChange, loading }) => (
  <div data-testid="range-filter" role="tablist" aria-label="Date range" className="inline-flex items-center rounded-md border border-border bg-white p-0.5 shadow-[0_1px_2px_rgba(16,24,40,0.04)]">
    {OPTIONS.map((d) => (
      <button
        key={d}
        role="tab"
        aria-selected={value === d}
        data-testid={`range-filter-${d}d`}
        onClick={() => onChange(d)}
        className={cn(
          "focus-ring min-h-[40px] rounded-[5px] px-3 py-1 text-xs font-medium transition-colors duration-150 sm:min-h-0",
          value === d ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100",
          loading && value === d && "opacity-70"
        )}
      >
        {d} days
      </button>
    ))}
  </div>
);
