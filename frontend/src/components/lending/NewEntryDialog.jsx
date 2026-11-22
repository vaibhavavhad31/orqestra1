import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Field } from "@/components/auth/Field";
import { FormDialog, TextArea, toInt } from "@/components/common/FormDialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LendingDisclaimer } from "@/components/lending/LendingDisclaimer";

const COPY = {
  request: { title: "Request credits", desc: "Ask a friend to lend you credits. They can accept or decline.", text: "Reason", submit: "Send request", path: "/lending/requests" },
  offer: { title: "Lend credits", desc: "Offer credits to a friend. They can accept or decline.", text: "Note (optional)", submit: "Send offer", path: "/lending/offers" },
};

const today = () => new Date().toISOString().slice(0, 10);

export const NewEntryDialog = ({ mode, onClose, friends, onCreated }) => {
  const [form, setForm] = useState({ friend_id: "", amount: "", reason: "", due_date: "" });
  const { run, busy, fields, error, reset } = useAction();
  const copy = COPY[mode] || COPY.request;
  useEffect(() => { setForm({ friend_id: "", amount: "", reason: "", due_date: "" }); reset(); }, [mode]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    const body = { ...form, amount: toInt(form.amount), due_date: form.due_date || null };
    const res = await run(() => api.post(copy.path, body), mode === "request" ? "Request sent" : "Offer sent");
    if (res) onCreated(res);
  };

  return (
    <FormDialog open={!!mode} onOpenChange={(o) => !o && onClose()} title={copy.title} description={copy.desc}
      onSubmit={submit} busy={busy} error={error} submitLabel={copy.submit} testId="new-entry-dialog">
      <div className="space-y-1.5">
        <span className="text-xs font-medium text-slate-700">Friend</span>
        <Select value={form.friend_id} onValueChange={(v) => setForm({ ...form, friend_id: v })}>
          <SelectTrigger data-testid="new-entry-friend" aria-label="Friend" className={`h-10 bg-white ${fields.friend_id ? "border-red-400" : ""}`}>
            <SelectValue placeholder={friends.length ? "Choose a friend" : "Add a friend first"} />
          </SelectTrigger>
          <SelectContent>
            {friends.map((f) => <SelectItem key={f.user.id} value={f.user.id} data-testid={`new-entry-friend-${f.user.id}`}>{f.user.name}</SelectItem>)}
          </SelectContent>
        </Select>
        {fields.friend_id && <p data-testid="field-error-friend_id" className="text-xs text-red-600">{fields.friend_id}</p>}
      </div>
      <Field id="amount" label="Amount (credits)" type="number" inputMode="numeric" min="1" step="1" value={form.amount}
        onChange={(e) => setForm({ ...form, amount: e.target.value })} error={fields.amount} />
      <TextArea id="reason" label={copy.text} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} error={fields.reason} />
      <Field id="due_date" label="Due date (optional)" type="date" min={today()} value={form.due_date}
        onChange={(e) => setForm({ ...form, due_date: e.target.value })} error={fields.due_date} />
      <LendingDisclaimer compact testId="new-entry-disclaimer" />
    </FormDialog>
  );
};
