import { useState } from "react";
import { RotateCcw, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import { useAction } from "@/hooks/useAction";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/auth/Field";
import { StatusPill } from "@/components/common/StatusPill";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fmtDateTime, fromLocalInput } from "@/lib/time";

const TYPES = ["daily", "weekly", "monthly", "rolling"];

export const ResetPanel = () => {
  const resets = useApi("/planner/resets");
  const providers = useApi("/providers");
  const [f, setF] = useState({ provider_id: "", reset_type: "daily", rolling_hours: "5", next: "" });
  const { run, busy, fields, error } = useAction();
  const save = async (e) => {
    e.preventDefault();
    const body = { provider_id: f.provider_id, reset_type: f.reset_type, rolling_hours: f.reset_type === "rolling" ? Number(f.rolling_hours) : null, next_reset_at: fromLocalInput(f.next) };
    if (await run(() => api.post("/planner/resets", body), "Reset time saved")) { resets.reload(); setF({ ...f, next: "" }); }
  };
  const remove = async (id) => { if (await run(() => api.delete(`/planner/resets/${id}`), "Removed")) resets.reload(); };
  return (
    <div className="space-y-4" data-testid="reset-panel">
      <ul className="space-y-2">
        {(resets.data || []).map((r) => (
          <li key={r.id} data-testid={`reset-${r.provider_id}`} className="flex items-start gap-2 rounded-md border border-border-subtle px-3 py-2">
            <RotateCcw className="mt-0.5 h-3.5 w-3.5 text-slate-400" />
            <div className="min-w-0 flex-1 text-sm">
              <div className="font-medium text-slate-900">{r.provider_name} <span className="text-xs font-normal text-slate-500">· {r.reset_type === "rolling" ? `every ${r.rolling_hours} h` : r.reset_type}</span></div>
              <div className="text-xs text-slate-500">Next reset {fmtDateTime(r.next_reset_at)}</div>
              <StatusPill tone="neutral" testId={`reset-${r.provider_id}-label`} className="mt-1">{r.label}</StatusPill>
            </div>
            <button type="button" aria-label={`Remove ${r.provider_name} reset`} onClick={() => remove(r.id)} className="focus-ring rounded p-1 text-slate-400 hover:text-red-600"><Trash2 className="h-3.5 w-3.5" /></button>
          </li>
        ))}
        {resets.data?.length === 0 && <p className="text-sm text-slate-500">No reset times yet. Add the ones you know.</p>}
      </ul>
      <form onSubmit={save} noValidate className="space-y-2.5 border-t border-border-subtle pt-3">
        {error && <p className="text-xs text-red-600">{error}</p>}
        <div className="grid grid-cols-2 gap-2">
          <Select value={f.provider_id} onValueChange={(v) => setF({ ...f, provider_id: v })}>
            <SelectTrigger data-testid="reset-provider" aria-label="Provider" className={`h-10 bg-white ${fields.provider_id ? "border-red-400" : ""}`}><SelectValue placeholder="Provider" /></SelectTrigger>
            <SelectContent>{(providers.data || []).map((p) => <SelectItem key={p.id} value={p.id} data-testid={`reset-provider-${p.id}`}>{p.name}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={f.reset_type} onValueChange={(v) => setF({ ...f, reset_type: v })}>
            <SelectTrigger data-testid="reset-type" aria-label="Reset type" className="h-10 bg-white"><SelectValue /></SelectTrigger>
            <SelectContent>{TYPES.map((t) => <SelectItem key={t} value={t} data-testid={`reset-type-${t}`}>{t === "rolling" ? "Rolling hours" : t[0].toUpperCase() + t.slice(1)}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        {f.reset_type === "rolling" && <Field id="reset-hours" label="Every (hours)" type="number" min="1" max="168" value={f.rolling_hours} onChange={(e) => setF({ ...f, rolling_hours: e.target.value })} error={fields.rolling_hours} />}
        <Field id="reset-next" label="Next reset" type="datetime-local" value={f.next} onChange={(e) => setF({ ...f, next: e.target.value })} error={fields.next_reset_at} />
        <Button type="submit" size="sm" disabled={busy} data-testid="reset-save">Save reset time</Button>
      </form>
    </div>
  );
};
