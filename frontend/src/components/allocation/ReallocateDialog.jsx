import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Field } from "@/components/auth/Field";
import { FormDialog, toInt } from "@/components/common/FormDialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fmt } from "@/lib/format";

const MemberSelect = ({ id, label, value, onChange, members }) => (
  <div className="space-y-1.5">
    <span className="text-xs font-medium text-slate-700">{label}</span>
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger data-testid={`reallocate-${id}`} aria-label={label} className="h-10 bg-white"><SelectValue placeholder="Choose a member" /></SelectTrigger>
      <SelectContent>
        {members.map((m) => (
          <SelectItem key={m.id} value={m.id} data-testid={`reallocate-${id}-${m.id}`}>
            {m.name} · {fmt(m.unused)} unused
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
);

export const ReallocateDialog = ({ preset, members, onClose, onSaved }) => {
  const [form, setForm] = useState({ from_user_id: "", to_user_id: "", credits: "" });
  const { run, busy, fields, error, reset } = useAction();
  useEffect(() => {
    if (preset) setForm({ from_user_id: preset.from_user_id || "", to_user_id: preset.to_user_id || "", credits: preset.credits ? String(preset.credits) : "" });
    reset();
  }, [preset]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    if (await run(() => api.post("/allocation/reallocate", { ...form, credits: toInt(form.credits) }), "Allocation moved")) onSaved();
  };
  const src = members.find((m) => m.id === form.from_user_id);

  return (
    <FormDialog open={!!preset} onOpenChange={(o) => !o && onClose()} title="Reallocate credits"
      description="Move monthly allocation from one member to another. Only unused credits (last 30 days) can be moved."
      onSubmit={submit} busy={busy} error={error} submitLabel="Move credits" testId="reallocate-dialog">
      <MemberSelect id="from" label="From" value={form.from_user_id} members={members} onChange={(v) => setForm({ ...form, from_user_id: v })} />
      <MemberSelect id="to" label="To" value={form.to_user_id} members={members.filter((m) => m.id !== form.from_user_id)} onChange={(v) => setForm({ ...form, to_user_id: v })} />
      <Field id="realloc-credits" label={`Credits${src ? ` (up to ${fmt(src.unused)})` : ""}`} type="number" inputMode="numeric" min="1" step="1"
        value={form.credits} onChange={(e) => setForm({ ...form, credits: e.target.value })} error={fields.credits} />
    </FormDialog>
  );
};
