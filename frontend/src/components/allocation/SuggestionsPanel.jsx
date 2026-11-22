import { ArrowRight, Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/States";
import { fmt } from "@/lib/format";

export const SuggestionsPanelBody = ({ members, suggestions, onApply }) => {
  const under = members.filter((m) => m.health === "underutilised");
  return (
    <div className="space-y-5" data-testid="underutilised-panel">
      <div>
        <div className="eyebrow mb-2">Underutilised · {under.length}</div>
        {under.length === 0 ? <p className="text-sm text-slate-500">No one is under 40% of their allocation.</p> : (
          <ul className="space-y-1.5">
            {under.map((m) => (
              <li key={m.id} data-testid={`underutilised-${m.id}`} className="flex items-center justify-between gap-2 text-sm">
                <span className="truncate text-slate-700">{m.name}</span>
                <span className="num shrink-0 text-xs text-slate-500">{m.utilisation}% · {fmt(m.unused)} unused</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <div className="eyebrow mb-2">Suggested reallocations</div>
        {suggestions.length === 0 ? (
          <EmptyState icon={Lightbulb} title="No suggestions" description="Suggestions pair someone under 40% with a teammate near their limit, in the same department. Admins also see cross-department moves when the receiving department has unallocated budget." />
        ) : (
          <ul className="space-y-2.5">
            {suggestions.map((s, i) => (
              <li key={i} data-testid={`suggestion-${i}`} className="rounded-md border border-border-subtle bg-slate-50/60 p-3">
                <div className="flex flex-wrap items-center gap-1.5 text-sm text-slate-900">
                  <span className="font-medium">{s.from_name}</span><ArrowRight className="h-3.5 w-3.5 text-slate-400" /><span className="font-medium">{s.to_name}</span>
                  <span className="num ml-auto font-semibold">{fmt(s.credits)}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{s.reason}</p>
                {s.cross_department && <p className="mt-1 text-[11px] font-medium text-indigo-700">Cross-department · internal budget only</p>}
                <Button size="sm" variant="outline" className="mt-2" data-testid={`suggestion-${i}-apply`} onClick={() => onApply(s)}>Review &amp; apply</Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
