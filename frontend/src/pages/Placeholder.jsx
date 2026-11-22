import { CheckCircle2, Clock } from "lucide-react";
import { moduleById } from "@/lib/modules";
import { useAuth } from "@/context/AuthContext";
import { StatusPill } from "@/components/common/StatusPill";

export default function Placeholder({ id }) {
  const { user } = useAuth();
  const base = moduleById(id);
  const module = user.mode === "individual" && base.individual ? { ...base, ...base.individual } : base;
  const Icon = module.icon;
  return (
    <div data-testid={`placeholder-${id}`} className="space-y-8">
      <div>
        <div className="eyebrow mb-2">Module</div>
        <h1 data-testid="page-title" className="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">{module.label}</h1>
        <p data-testid="placeholder-purpose" className="mt-1.5 text-sm text-slate-500">{module.purpose}</p>
      </div>
      <div className="surface grid grid-cols-1 overflow-hidden animate-fade-up lg:grid-cols-5">
        <div className="space-y-5 p-6 sm:p-8 lg:col-span-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-md border border-indigo-100 bg-indigo-50">
            <Icon className="h-5 w-5 text-indigo-600" strokeWidth={1.75} />
          </div>
          <div>
            <StatusPill tone="accent" testId="placeholder-coming-badge">
              <Clock className="mr-1 h-3 w-3" /> Coming in a later phase
            </StatusPill>
            <h2 className="mt-3 text-lg font-semibold text-slate-900">{module.label} is on the roadmap</h2>
            <p className="mt-1 max-w-md text-sm text-slate-500">
              The foundation (data model, permissions and navigation) is in place. The workflows ship in Phase {module.phase}.
            </p>
          </div>
        </div>
        <div className="border-t border-border bg-slate-50/60 p-6 sm:p-8 lg:col-span-2 lg:border-l lg:border-t-0">
          <div className="eyebrow mb-4">Planned for Phase {module.phase}</div>
          <ul className="space-y-3">
            {module.planned.map((p) => (
              <li key={p} className="flex items-start gap-2.5 text-sm text-slate-600">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-slate-300" strokeWidth={1.75} />
                {p}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
