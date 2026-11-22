import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import { useAction } from "@/hooks/useAction";
import { Field } from "@/components/auth/Field";
import { FormDialog, TextArea, toInt } from "@/components/common/FormDialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fromLocalInput, overlapsAny, toLocalInput } from "@/lib/time";

const Pick = ({ id, label, value, onChange, options, error }) => (
  <div className="space-y-1.5">
    <span className="text-xs font-medium text-slate-700">{label}</span>
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger data-testid={`session-${id}`} aria-label={label} className={`h-10 bg-white ${error ? "border-red-400" : ""}`}><SelectValue placeholder="Choose" /></SelectTrigger>
      <SelectContent>{options.map((o) => <SelectItem key={o.id} value={o.id} data-testid={`session-${id}-${o.id}`}>{o.name}</SelectItem>)}</SelectContent>
    </Select>
    {error && <p data-testid={`field-error-${id}`} className="text-xs text-red-600">{error}</p>}
  </div>
);

const REMINDERS = [{ id: "none", name: "No reminder" }, { id: "15", name: "15 min before" }, { id: "30", name: "30 min before" }, { id: "60", name: "60 min before" }];

export const SessionDialog = ({ open, session, sessions, onClose, onSaved }) => {
  const providers = useApi("/providers");
  const [f, setF] = useState({});
  const { run, busy, fields, error, reset } = useAction();
  useEffect(() => {
    setF(session ? { provider_id: session.provider_id, start: toLocalInput(session.start_at), end: toLocalInput(session.end_at), credits: String(session.estimated_credits),
      purpose: session.purpose, reminder: session.reminder_min ? String(session.reminder_min) : "none" }
      : { provider_id: "", start: "", end: "", credits: "", purpose: "", reminder: "none" });
    reset();
  }, [open, session]); // eslint-disable-line react-hooks/exhaustive-deps
  const set = (k) => (e) => setF({ ...f, [k]: e?.target ? e.target.value : e });
  const startIso = fromLocalInput(f.start);
  const endIso = fromLocalInput(f.end);
  const overlap = overlapsAny(startIso, endIso, sessions, session?.id);

  const submit = async () => {
    const body = { provider_id: f.provider_id, start_at: startIso, end_at: endIso, estimated_credits: toInt(f.credits), purpose: f.purpose,
      reminder_min: f.reminder === "none" ? null : Number(f.reminder) };
    const res = await run(() => (session ? api.patch(`/planner/sessions/${session.id}`, body) : api.post("/planner/sessions", body)), session ? "Session updated" : "Session planned");
    if (res) { if (res.warning) toast.warning(res.warning); onSaved(); }
  };

  return (
    <FormDialog open={open} onOpenChange={(o) => !o && onClose()} testId="session-dialog" busy={busy} error={error} onSubmit={submit}
      title={session ? "Edit session" : "Plan a session"} submitLabel={session ? "Save" : "Plan session"}
      description="Times are in your local time zone.">
      <Pick id="provider" label="Provider" value={f.provider_id} onChange={set("provider_id")} options={providers.data || []} error={fields.provider_id} />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field id="session-start" label="Start" type="datetime-local" value={f.start || ""} onChange={set("start")} error={fields.start_at} />
        <Field id="session-end" label="End" type="datetime-local" value={f.end || ""} onChange={set("end")} error={fields.end_at} />
      </div>
      {overlap && <p data-testid="session-overlap-warning" className="flex items-center gap-1.5 text-xs text-amber-700"><AlertTriangle className="h-3.5 w-3.5" />Overlaps another session</p>}
      <Field id="session-credits" label="Estimated credits" type="number" inputMode="numeric" min="1" step="1" value={f.credits || ""} onChange={set("credits")} error={fields.estimated_credits} />
      <TextArea id="session-purpose" label="Purpose" value={f.purpose || ""} onChange={set("purpose")} error={fields.purpose} />
      <Pick id="reminder" label="Reminder" value={f.reminder} onChange={set("reminder")} options={REMINDERS} error={fields.reminder_min} />
    </FormDialog>
  );
};

export const SuggestDialog = ({ session, onClose, onSaved }) => {
  const [f, setF] = useState({ start: "", end: "", note: "" });
  const { run, busy, fields, error, reset } = useAction();
  useEffect(() => { setF(session ? { start: toLocalInput(session.start_at), end: toLocalInput(session.end_at), note: "" } : { start: "", end: "", note: "" }); reset(); }, [session]); // eslint-disable-line react-hooks/exhaustive-deps
  const submit = async () => {
    const res = await run(() => api.post(`/planner/team/sessions/${session.id}/suggest`, { start_at: fromLocalInput(f.start), end_at: fromLocalInput(f.end), note: f.note }), "Suggestion sent");
    if (res) onSaved();
  };
  return (
    <FormDialog open={!!session} onOpenChange={(o) => !o && onClose()} testId="suggest-dialog" busy={busy} error={error} onSubmit={submit}
      title="Suggest a new time" submitLabel="Send suggestion" description={session ? `${session.user_name}: ${session.purpose}` : ""}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field id="suggest-start" label="New start" type="datetime-local" value={f.start} onChange={(e) => setF({ ...f, start: e.target.value })} error={fields.start_at} />
        <Field id="suggest-end" label="New end" type="datetime-local" value={f.end} onChange={(e) => setF({ ...f, end: e.target.value })} error={fields.end_at} />
      </div>
      <TextArea id="suggest-note" label="Note" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} />
    </FormDialog>
  );
};
