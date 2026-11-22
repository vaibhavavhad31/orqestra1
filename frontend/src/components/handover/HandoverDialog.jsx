import { useEffect, useState } from "react";
import { Paperclip, X } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import { useAction } from "@/hooks/useAction";
import { Field } from "@/components/auth/Field";
import { FormDialog, TextArea } from "@/components/common/FormDialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export const BAD_FILE = "Unsupported file or file too large (max 10 MB)";
const EXT = ["pdf", "png", "jpg", "jpeg", "docx", "txt", "md"];
const MAX = 10 * 1024 * 1024;
const EMPTY = { title: "", description: "", objective: "", priority: "medium", completed_work: "", pending_work: "", context_notes: "", assignee_id: "" };
export const fileOk = (f) => EXT.includes(f.name.split(".").pop().toLowerCase()) && f.size > 0 && f.size <= MAX;

const PickSelect = ({ id, label, value, onChange, options, error, placeholder }) => (
  <div className="space-y-1.5">
    <span className="text-xs font-medium text-slate-700">{label}</span>
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger data-testid={`handover-${id}`} aria-label={label} className={`h-10 bg-white ${error ? "border-red-400" : ""}`}><SelectValue placeholder={placeholder} /></SelectTrigger>
      <SelectContent>{options.map((o) => <SelectItem key={o.id} value={o.id} data-testid={`handover-${id}-${o.id}`}>{o.name}</SelectItem>)}</SelectContent>
    </Select>
    {error && <p data-testid={`field-error-${id}`} className="text-xs text-red-600">{error}</p>}
  </div>
);

export const HandoverDialog = ({ open, task, onClose, onSaved }) => {
  const [form, setForm] = useState(EMPTY);
  const [files, setFiles] = useState([]);
  const [fileError, setFileError] = useState("");
  const { run, busy, fields, error, reset, setFields } = useAction();
  const people = useApi("/handovers/assignees");
  useEffect(() => { setForm(task ? { ...EMPTY, ...task } : EMPTY); setFiles([]); setFileError(""); reset(); }, [open, task]); // eslint-disable-line react-hooks/exhaustive-deps
  const set = (k) => (e) => setForm({ ...form, [k]: e?.target ? e.target.value : e });

  const pick = (e) => {
    const chosen = [...e.target.files];
    e.target.value = "";
    if (chosen.some((f) => !fileOk(f))) return setFileError(BAD_FILE);
    if (files.length + chosen.length > 5) return setFileError("A handover can have at most 5 attachments");
    setFileError("");
    setFiles([...files, ...chosen]);
  };

  const submit = async () => {
    const local = {};
    if (!form.title.trim()) local.title = "Add a title";
    if (!form.pending_work.trim()) local.pending_work = "Describe the pending work";
    if (!task && !form.assignee_id) local.assignee_id = "Choose who to hand over to";
    if (Object.keys(local).length) return setFields(local);
    const body = Object.fromEntries(Object.keys(EMPTY).map((k) => [k, form[k]]));
    const saved = await run(() => (task ? api.patch(`/handovers/${task.id}`, body) : api.post("/handovers", body)), task ? "Handover updated" : "Handover sent");
    if (!saved) return;
    for (const f of files) {
      const fd = new FormData();
      fd.append("file", f);
      await run(() => api.post(`/handovers/${saved.id}/attachments`, fd));
    }
    onSaved(saved);
  };

  return (
    <FormDialog open={open} onOpenChange={(o) => !o && onClose()} testId="handover-dialog" busy={busy} error={error}
      title={task ? "Edit handover" : "New handover"} submitLabel={task ? "Save changes" : "Send handover"}
      description="Only the context you add here is shared. Your AI chat history is never shared." onSubmit={submit}>
      <Field id="title" label="Title" value={form.title} onChange={set("title")} error={fields.title} />
      {!task && <PickSelect id="assignee" label="Hand over to" value={form.assignee_id} onChange={set("assignee_id")} error={fields.assignee_id}
        options={(people.data || []).map((p) => ({ id: p.id, name: p.department ? `${p.name} · ${p.department}` : p.name }))} placeholder="Choose a person" />}
      <PickSelect id="priority" label="Priority" value={form.priority} onChange={set("priority")} error={fields.priority}
        options={["low", "medium", "high", "urgent"].map((p) => ({ id: p, name: p[0].toUpperCase() + p.slice(1) }))} />
      <Field id="objective" label="Objective" value={form.objective} onChange={set("objective")} />
      <TextArea id="description" label="Description" value={form.description} onChange={set("description")} />
      <TextArea id="completed_work" label="Completed work" value={form.completed_work} onChange={set("completed_work")} />
      <TextArea id="pending_work" label="Pending work" value={form.pending_work} onChange={set("pending_work")} error={fields.pending_work} />
      <TextArea id="context_notes" label="Context notes" value={form.context_notes} onChange={set("context_notes")} />
      {!task && (
        <div className="space-y-1.5">
          <label className="inline-flex cursor-pointer items-center gap-1.5 text-sm font-medium text-indigo-600">
            <Paperclip className="h-4 w-4" /> Add attachments
            <input data-testid="handover-file-input" type="file" multiple className="sr-only" accept=".pdf,.png,.jpg,.jpeg,.docx,.txt,.md" onChange={pick} />
          </label>
          <p className="text-xs text-slate-400">PDF, PNG, JPG, DOCX, TXT or MD · max 10 MB each · up to 5</p>
          {fileError && <p data-testid="handover-file-error" className="text-xs text-red-600">{fileError}</p>}
          {files.map((f, i) => (
            <div key={i} data-testid={`handover-file-${i}`} className="flex items-center justify-between rounded-md border border-border-subtle px-2.5 py-1.5 text-xs text-slate-600">
              <span className="truncate">{f.name}</span>
              <button type="button" aria-label={`Remove ${f.name}`} onClick={() => setFiles(files.filter((_, j) => j !== i))}><X className="h-3.5 w-3.5" /></button>
            </div>
          ))}
        </div>
      )}
    </FormDialog>
  );
};
