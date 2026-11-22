import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Field } from "@/components/auth/Field";
import { FormDialog, TextArea, toInt } from "@/components/common/FormDialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fmt } from "@/lib/format";

export const DecisionDialog = ({ decision, onClose, onSaved }) => {
  const [value, setValue] = useState("");
  const { run, busy, fields, error, reset } = useAction();
  const approve = decision?.type === "approve";
  useEffect(() => { setValue(approve ? String(decision.request.credits) : ""); reset(); }, [decision]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    const id = decision.request.id;
    const res = approve
      ? await run(() => api.post(`/allocation/requests/${id}/approve`, { credits: toInt(value) }), "Request approved")
      : await run(() => api.post(`/allocation/requests/${id}/reject`, { note: value }), "Request rejected");
    if (res) onSaved();
  };

  const r = decision?.request;
  return (
    <FormDialog open={!!decision} onOpenChange={(o) => !o && onClose()} testId="decision-dialog" destructive={!approve}
      title={approve ? "Approve request" : "Reject request"} submitLabel={approve ? "Approve" : "Reject"}
      description={r ? `${r.requester_name} asked for ${fmt(r.credits)} credits: “${r.reason}”` : ""}
      onSubmit={submit} busy={busy} error={error}>
      {approve
        ? <Field id="approve-credits" label="Credits to approve (partial allowed)" type="number" inputMode="numeric" min="1" step="1"
            value={value} onChange={(e) => setValue(e.target.value)} error={fields.credits} />
        : <TextArea id="reject-note" label="Note for the employee" value={value} onChange={(e) => setValue(e.target.value)} />}
    </FormDialog>
  );
};

export const RequestDialog = ({ open, onClose, onSaved }) => {
  const [form, setForm] = useState({ amount: "", reason: "", urgency: "normal" });
  const { run, busy, fields, error, reset } = useAction();
  useEffect(() => { setForm({ amount: "", reason: "", urgency: "normal" }); reset(); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    if (await run(() => api.post("/allocation/requests", { ...form, amount: toInt(form.amount) }), "Request submitted")) onSaved();
  };

  return (
    <FormDialog open={open} onOpenChange={(o) => !o && onClose()} title="Request more credits"
      description="Your manager and the organisation admin will review it." onSubmit={submit} busy={busy} error={error}
      submitLabel="Submit request" testId="resource-request-dialog">
      <Field id="request-amount" label="Credits" type="number" inputMode="numeric" min="1" step="1" value={form.amount}
        onChange={(e) => setForm({ ...form, amount: e.target.value })} error={fields.amount} />
      <TextArea id="request-reason" label="Reason" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} error={fields.reason} />
      <div className="space-y-1.5">
        <span className="text-xs font-medium text-slate-700">Urgency</span>
        <Select value={form.urgency} onValueChange={(v) => setForm({ ...form, urgency: v })}>
          <SelectTrigger data-testid="request-urgency" aria-label="Urgency" className="h-10 bg-white"><SelectValue /></SelectTrigger>
          <SelectContent>
            {["low", "normal", "high"].map((u) => <SelectItem key={u} value={u} data-testid={`request-urgency-${u}`}>{u[0].toUpperCase() + u.slice(1)}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
    </FormDialog>
  );
};
