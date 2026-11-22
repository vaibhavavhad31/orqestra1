import { Building2, User } from "lucide-react";
import { cn } from "@/lib/utils";

const OPTIONS = [
  { id: "individual", label: "Individual", icon: User, text: "Track personal usage and lend credits to friends." },
  { id: "organisation", label: "Organisation", icon: Building2, text: "Create a new organisation. You become its Admin." },
];

export const ModeSelector = ({ value, onChange, error }) => (
  <div>
    <div role="radiogroup" aria-label="Account mode" className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
      {OPTIONS.map((o) => {
        const active = value === o.id;
        const Icon = o.icon;
        return (
          <button
            key={o.id}
            type="button"
            role="radio"
            aria-checked={active}
            data-testid={`mode-option-${o.id}`}
            onClick={() => onChange(o.id)}
            className={cn(
              "focus-ring flex flex-col items-start gap-2 rounded-lg border bg-white p-3.5 text-left transition-colors duration-150",
              active ? "border-indigo-500 ring-1 ring-indigo-500" : "border-border hover:border-slate-300"
            )}
          >
            <Icon className={cn("h-4 w-4", active ? "text-indigo-600" : "text-slate-400")} strokeWidth={1.75} />
            <span className="text-sm font-medium text-slate-900">{o.label}</span>
            <span className="text-xs leading-relaxed text-slate-500">{o.text}</span>
          </button>
        );
      })}
    </div>
    <p className="mt-2 text-xs text-slate-400">Each account uses exactly one mode. It can't be switched later.</p>
    {error && <p data-testid="field-error-mode" className="mt-1.5 text-xs text-red-600">{error}</p>}
  </div>
);
