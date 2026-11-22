import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Plus, Sparkles, Trash2, Wand2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/auth/Field";
import { TextArea } from "@/components/common/FormDialog";
import { TYPES, computeWaves, selectCls } from "@/components/tasks/TaskBits";

const blankSub = () => ({ title: "", type: "planning", depends_on: [], estimate_low: 50, estimate_high: 100, provider_id: "", tool_reason: "", basis: "manual" });

export const GoalDialog = ({ open, onClose, onSaved }) => {
  const [form, setForm] = useState({ title: "", description: "", priority: "medium", deadline: "" });
  const [subs, setSubs] = useState([]);
  const [meta, setMeta] = useState(null);
  const [providers, setProviders] = useState([]);
  const breakdown = useAction();
  const save = useAction();

  useEffect(() => {
    if (!open) return;
    setForm({ title: "", description: "", priority: "medium", deadline: "" });
    setSubs([]); setMeta(null); breakdown.reset(); save.reset();
    api.get("/providers").then(({ data }) => setProviders(data)).catch(() => setProviders([]));
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const { waves, cycle } = useMemo(() => computeWaves(subs), [subs]);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const setSub = (i, patch) => setSubs((list) => list.map((s, j) => (j === i ? { ...s, ...patch, basis: patch.basis || (("estimate_low" in patch || "estimate_high" in patch) ? "manual" : s.basis) } : s)));
  const toggleDep = (i, d) => setSub(i, { depends_on: subs[i].depends_on.includes(d) ? subs[i].depends_on.filter((x) => x !== d) : [...subs[i].depends_on, d].sort((a, b) => a - b) });
  const remove = (i) => setSubs((list) => list.filter((_, j) => j !== i).map((s) => ({ ...s, depends_on: s.depends_on.filter((d) => d !== i).map((d) => (d > i ? d - 1 : d)) })));

  const runBreakdown = async () => {
    const res = await breakdown.run(() => api.post("/tasks/decompose", { title: form.title, description: form.description, priority: form.priority }));
    if (res) {
      setSubs(res.subtasks.map((s) => ({ ...s, basis: res.method })));
      setMeta(res);
    }
  };

  const submit = async () => {
    const body = { ...form, deadline: form.deadline || null, method: meta?.method || "manual",
      subtasks: subs.map((s) => ({ ...s, estimate_low: Number(s.estimate_low), estimate_high: Number(s.estimate_high) })) };
    const res = await save.run(() => api.post("/tasks", body), "Goal created");
    if (res) onSaved(res);
  };

  const err = save.fields.title || breakdown.fields.title;
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="goal-dialog" className="max-h-[92vh] w-[calc(100vw-2rem)] max-w-3xl overflow-y-auto rounded-lg">
        <DialogHeader className="text-left">
          <DialogTitle className="text-base">New goal</DialogTitle>
          <DialogDescription className="text-sm">Describe the outcome, then break it into sub-tasks you can assign and plan. Edit anything before saving.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {(save.error || breakdown.error || save.fields.subtasks) && (
            <p data-testid="goal-dialog-error" role="alert" className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {save.fields.subtasks || save.error || breakdown.error}
            </p>
          )}
          <Field id="goal-title" label="Goal" placeholder="e.g. Ship the invoice export API" value={form.title} onChange={set("title")} error={err} />
          <TextArea id="goal-description" label="Details (optional, helps the breakdown)" value={form.description} onChange={set("description")} />
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label htmlFor="goal-priority" className="text-xs font-medium text-slate-700">Priority</label>
              <select id="goal-priority" data-testid="input-goal-priority" className={selectCls} value={form.priority} onChange={set("priority")}>
                {["low", "medium", "high", "urgent"].map((p) => <option key={p} value={p}>{p[0].toUpperCase() + p.slice(1)}</option>)}
              </select>
            </div>
            <Field id="goal-deadline" label="Deadline (optional)" type="date" value={form.deadline} onChange={set("deadline")} error={save.fields.deadline} />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" data-testid="goal-breakdown" onClick={runBreakdown} disabled={breakdown.busy || !form.title.trim()}>
              <Wand2 className="mr-1.5 h-4 w-4" />{breakdown.busy ? "Breaking down…" : subs.length ? "Break down again" : "Break down into sub-tasks"}
            </Button>
            <Button type="button" variant="outline" data-testid="goal-add-subtask" onClick={() => setSubs((l) => [...l, blankSub()])}><Plus className="mr-1.5 h-4 w-4" />Add sub-task</Button>
          </div>
          {meta && (
            <p data-testid="goal-breakdown-notice" className="flex items-start gap-2 rounded-md border border-indigo-100 bg-indigo-50/60 px-3 py-2 text-xs text-indigo-800">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{meta.notice}{meta.usage?.prompt_tokens != null && ` Tokens used: ${meta.usage.prompt_tokens + (meta.usage.completion_tokens || 0)} (${meta.usage.model}).`}</span>
            </p>
          )}
          {cycle && <p className="text-xs text-red-600" data-testid="goal-cycle-warning">These dependencies form a loop. Remove one so the work can start somewhere.</p>}
          {subs.length > 0 && (
            <ol data-testid="goal-subtasks" className="space-y-2.5">
              {subs.map((s, i) => (
                <li key={i} data-testid={`goal-sub-${i}`} className="rounded-md border border-border-subtle bg-white p-3">
                  <div className="flex items-start gap-2">
                    <span className="num mt-2 w-5 shrink-0 text-xs text-slate-400">{i + 1}</span>
                    <div className="min-w-0 flex-1 space-y-2">
                      <input aria-label={`Sub-task ${i + 1} title`} data-testid={`goal-sub-${i}-title`} value={s.title} onChange={(e) => setSub(i, { title: e.target.value })}
                        className="focus-ring h-9 w-full rounded-md border border-input bg-white px-2.5 text-sm" placeholder="What needs doing" />
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                        <select aria-label="Type" className={selectCls} value={s.type} onChange={(e) => setSub(i, { type: e.target.value })}>
                          {TYPES.map((t) => <option key={t} value={t}>{t[0].toUpperCase() + t.slice(1)}</option>)}
                        </select>
                        <select aria-label="AI tool" className={selectCls} value={s.provider_id} onChange={(e) => setSub(i, { provider_id: e.target.value, tool_reason: "Chosen by you" })}>
                          <option value="">Suggest a tool</option>
                          {providers.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                        </select>
                        <input aria-label="Low estimate (credits)" type="number" min="1" className={selectCls} value={s.estimate_low} onChange={(e) => setSub(i, { estimate_low: e.target.value })} />
                        <input aria-label="High estimate (credits)" type="number" min="1" className={selectCls} value={s.estimate_high} onChange={(e) => setSub(i, { estimate_high: e.target.value })} />
                      </div>
                      {i > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
                          <span>Depends on:</span>
                          {subs.slice(0, i).map((_, d) => (
                            <button key={d} type="button" data-testid={`goal-sub-${i}-dep-${d}`} onClick={() => toggleDep(i, d)}
                              className={`focus-ring rounded-full border px-2 py-0.5 ${s.depends_on.includes(d) ? "border-indigo-400 bg-indigo-50 text-indigo-700" : "border-border bg-white text-slate-500"}`}>{d + 1}</button>
                          ))}
                        </div>
                      )}
                      <div className="text-[11px] text-slate-400">
                        Wave {waves[i] + 1}{waves[i] === 0 ? " · can start now" : ""}{s.tool_reason ? ` · ${s.tool_reason}` : ""} · {s.basis === "manual" ? "estimate entered by you" : s.basis === "ai" ? "estimated by your LLM" : "estimated by built-in rules"}
                      </div>
                    </div>
                    <button type="button" aria-label={`Remove sub-task ${i + 1}`} onClick={() => remove(i)} className="focus-ring mt-1 rounded p-1 text-slate-400 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
        <DialogFooter className="flex-row justify-end gap-2 sm:space-x-0">
          <Button type="button" variant="outline" onClick={onClose} data-testid="goal-dialog-cancel">Cancel</Button>
          <Button type="button" onClick={submit} disabled={save.busy || cycle || !form.title.trim() || subs.length === 0} data-testid="goal-dialog-submit">
            {save.busy ? "Saving…" : `Create goal${subs.length ? ` with ${subs.length} sub-tasks` : ""}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
