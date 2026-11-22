import { Blocks, Info } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/common/Layout";
import { EmptyState, ErrorState } from "@/components/common/States";
import { StatusPill } from "@/components/common/StatusPill";
import { SimulatedBadge } from "@/components/common/SimulatedBadge";

export default function Integrations() {
  const { data, error, reload } = useApi("/integrations");
  const toggle = async (p, enabled) => {
    try { await api.put(`/integrations/${p.id}`, { enabled }); toast.success(enabled ? `${p.name}: simulated connection active` : `${p.name}: simulated connection off`); }
    catch (e) { toast.error(formatApiError(e)); }
    reload();
  };
  return (
    <div data-testid="integrations-page" className="space-y-6 sm:space-y-8">
      <PageHeader eyebrow={data?.scope === "org" ? "Organisation-wide" : "Your workspace"} title="Integrations" description="The provider registry and simulated connectors"
        actions={<SimulatedBadge testId="integrations-simulated-badge" />} />
      <p data-testid="integrations-note" className="flex items-start gap-2 rounded-md border border-border bg-slate-50 px-3.5 py-2.5 text-sm text-slate-600">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />No real provider data is retrieved. Connections here are simulated.
      </p>
      {error ? <ErrorState message={error} onRetry={reload} /> : !data ? <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-36" />)}</div>
        : data.providers.length === 0 ? <EmptyState icon={Blocks} title="No providers" description="Providers appear here once registered." />
          : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="integrations-grid">
              {data.providers.map((p) => (
                <div key={p.id} data-testid={`integration-${p.id}`} className="surface flex flex-col gap-4 p-5">
                  <div className="flex items-start gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-sm font-semibold text-white" style={{ background: p.color }}>{p.name[0]}</span>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-semibold text-slate-900">{p.name}</div>
                      <div className="text-xs text-slate-500">{p.vendor}</div>
                    </div>
                  </div>
                  <StatusPill tone={p.simulated_connection ? "accent" : "neutral"} testId={`integration-${p.id}-status`} className="self-start">{p.status}</StatusPill>
                  <label className="mt-auto flex items-center justify-between gap-3 border-t border-border-subtle pt-3 text-sm text-slate-700">
                    Simulated connection
                    <Switch data-testid={`integration-${p.id}-toggle`} checked={p.simulated_connection} onCheckedChange={(v) => toggle(p, v)} aria-label={`Simulated connection for ${p.name}`} />
                  </label>
                  {p.simulated_connection && <p data-testid={`integration-${p.id}-note`} className="-mt-2 text-xs text-slate-500">{data.note}</p>}
                </div>
              ))}
            </div>
          )}
    </div>
  );
}
