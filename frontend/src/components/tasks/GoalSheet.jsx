import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CalendarCheck, CalendarPlus, CheckCircle2, Lock, Trash2, UserPlus, Users } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/States";
import { StatusPill } from "@/components/common/StatusPill";
import { TextArea } from "@/components/common/FormDialog";
import { fmtDateTime } from "@/lib/time";
import { Estimate, PRIORITY_TONE, Progress, Provenance, STATUS_LABEL, SubStatus, TypePill, selectCls } from "@/components/tasks/TaskBits";

const Candidates = ({ data, people, onAssign, busy }) => {
  const [other, setOther] = useState("");
  return (
    <div data-testid="candidates-panel" className="mt-3 space-y-2 rounded-md border border-indigo-100 bg-indigo-50/40 p-3">
      <div className="text-xs font-medium text-slate-700">Best matches for {data.tool} · needs <Estimate low={data.estimate.low} high={data.estimate.high} /></div>
      {data.candidates.map((c, i) => (
        <div key={c.user_id} data-testid={`candidate-${i}`} className="flex items-start gap-3 rounded-md bg-white p-2.5">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5 text-sm font-medium text-slate-900">
              {c.name}{c.is_you && <span className="text-xs font-normal text-slate-400">(you)</span>}
              <StatusPill tone={c.fits ? "success" : c.partly_fits ? "warning" : "danger"}>{c.fits ? "Has capacity" : c.partly_fits ? "Tight" : "Short"}</StatusPill>
              <span className="num text-xs text-slate-400">score {c.score}</span>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">{c.reason}</p>
          </div>
          <Button size="sm" variant={i === 0 ? "default" : "outline"} disabled={busy || c.is_current} data-testid={`candidate-${i}-assign`}
            onClick={() => onAssign(c.user_id, c.reason)}>{c.is_current ? "Assigned" : "Assign"}</Button>
        </div>
      ))}
      {data.needs_capacity && (
        <div data-testid="needs-capacity" className="rounded-md border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-800">
          <div className="mb-1 flex items-center gap-1.5 font-medium"><AlertTriangle className="h-3.5 w-3.5" />Nobody has enough capacity for this sub-task</div>
          <ul className="space-y-1">
            {data.capacity_options.map((o) => <li key={o.kind}><Link className="font-medium underline" to={o.link}>{o.label}</Link> — {o.note}</li>)}
          </ul>
        </div>
      )}
      <div className="flex items-center gap-2 pt-1">
        <select aria-label="Assign someone else" className={selectCls} value={other} onChange={(e) => setOther(e.target.value)}>
          <option value="">Assign someone else…</option>
          {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <Button size="sm" variant="outline" disabled={!other || busy} onClick={() => onAssign(other, "Chosen manually")}>Assign</Button>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5"><Provenance>Capacity: {data.provenance.capacity}</Provenance><Provenance>Tool use: {data.provenance.usage}</Provenance></div>
    </div>
  );
};

const Slot = ({ slot, canSchedule, onAccept, busy }) => (
  <div data-testid="slot-panel" className="mt-3 space-y-2 rounded-md border border-emerald-100 bg-emerald-50/40 p-3">
    <div className="text-sm font-medium text-slate-900">{fmtDateTime(slot.start_at)} – {new Date(slot.end_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · {slot.provider_name}</div>
    <ul className="list-disc space-y-0.5 pl-4 text-xs text-slate-600">{slot.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
    {slot.warnings.map((w) => <p key={w} className="flex items-start gap-1.5 text-xs text-amber-700"><AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />{w}</p>)}
    <div className="flex flex-wrap gap-x-3 gap-y-0.5"><Provenance>Estimate: {slot.provenance.estimate}</Provenance><Provenance>Availability: {slot.provenance.availability}</Provenance><Provenance>Reset: {slot.provenance.reset}</Provenance></div>
    <Button size="sm" data-testid="slot-accept" disabled={busy} onClick={onAccept}>
      <CalendarPlus className="mr-1.5 h-4 w-4" />{canSchedule ? "Add to my planner" : "Send this time to the assignee"}
    </Button>
  </div>
);

const SubtaskCard = ({ s, goal, people, reload }) => {
  const act = useAction();
  const [cands, setCands] = useState(null);
  const [slot, setSlot] = useState(null);
  const [doneNote, setDoneNote] = useState(null);

  const patch = async (body, msg) => {
    const res = await act.run(() => api.patch(`/subtasks/${s.id}`, body), msg);
    if (res) { setCands(null); setSlot(null); setDoneNote(null); reload(res); }
  };
  const loadCands = async () => { const r = await act.run(() => api.get(`/subtasks/${s.id}/candidates`)); if (r) setCands(r); };
  const loadSlot = async () => {
    const r = await act.run(() => api.post(`/subtasks/${s.id}/slot`, { tz_offset: new Date().getTimezoneOffset() }));
    if (r) setSlot(r);
  };
  const schedule = async (sl) => {
    const r = await act.run(() => api.post(`/subtasks/${s.id}/schedule`, { start_at: sl.start_at, end_at: sl.end_at, provider_id: sl.provider_id }),
      s.can_schedule ? "Added to your planner" : "Time sent to the assignee");
    if (r) { setSlot(null); reload(r.goal); if (r.warning) toast.warning(r.warning); }
  };
  const onStatus = (v) => (v === "done" ? setDoneNote("") : patch({ status: v }, `Marked ${STATUS_LABEL[v].toLowerCase()}`));

  return (
    <li data-testid={`subtask-${s.id}`} className="rounded-md border border-border-subtle bg-white p-3.5">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-slate-900">{s.title}</div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
            <SubStatus status={s.status} testId={`subtask-${s.id}-status`} /><TypePill type={s.type} />
            <span title={s.tool_reason}>{s.provider_name}</span><span>·</span><Estimate low={s.estimate.low} high={s.estimate.high} />
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {s.assignee_name ? <>Assigned to <span className="font-medium text-slate-700">{s.assignee_name}</span></> : <span className="text-amber-700">Unassigned</span>}
            {s.dependency_titles.length > 0 && <> · after {s.dependency_titles.join(", ")}</>}
          </div>
          {s.blocked_by.length > 0 && s.status !== "done" && <p className="mt-1 flex items-center gap-1 text-xs text-slate-400"><Lock className="h-3 w-3" />Waiting on {s.blocked_by.length} earlier sub-task{s.blocked_by.length > 1 ? "s" : ""}</p>}
          {s.session_id && <p className="mt-1 flex items-center gap-1 text-xs text-emerald-700"><CalendarCheck className="h-3.5 w-3.5" />In {s.assignee_name}'s planner · <Link className="underline" to="/planner">open planner</Link></p>}
          {s.suggested_slot && !s.session_id && (
            <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-indigo-700">
              <span>{s.suggested_slot.by_name} suggested {fmtDateTime(s.suggested_slot.start_at)}</span>
              {s.can_schedule && <Button size="sm" variant="outline" className="h-7" data-testid={`subtask-${s.id}-accept-suggested`} onClick={() => schedule(s.suggested_slot)}>Add to my planner</Button>}
            </div>
          )}
          {s.output?.summary && <p className="mt-1.5 rounded bg-slate-50 px-2 py-1 text-xs text-slate-600">Output: {s.output.summary}</p>}
          <Provenance>{s.estimate.provenance}</Provenance>
        </div>
        {s.can_update && (
          <select aria-label="Status" data-testid={`subtask-${s.id}-status-select`} className="focus-ring h-9 w-32 shrink-0 rounded-md border border-input bg-white px-2 text-sm" value={doneNote !== null ? "done" : s.status} onChange={(e) => onStatus(e.target.value)}>
            {Object.keys(STATUS_LABEL).map((k) => <option key={k} value={k}>{STATUS_LABEL[k]}</option>)}
          </select>
        )}
      </div>
      {act.error && <p className="mt-2 text-xs text-red-600" role="alert">{act.error}</p>}
      {doneNote !== null && (
        <div className="mt-3 space-y-2">
          <TextArea id={`done-${s.id}`} label="What was the output? (shared with the goal owner)" value={doneNote} onChange={(e) => setDoneNote(e.target.value)} />
          <div className="flex gap-2"><Button size="sm" data-testid={`subtask-${s.id}-confirm-done`} disabled={act.busy} onClick={() => patch({ status: "done", output_summary: doneNote }, "Marked done")}>Mark done</Button>
            <Button size="sm" variant="ghost" onClick={() => setDoneNote(null)}>Cancel</Button></div>
        </div>
      )}
      {s.status !== "done" && (
        <div className="mt-2.5 flex flex-wrap gap-2">
          {goal.can_manage && <Button size="sm" variant="outline" data-testid={`subtask-${s.id}-suggest-assignee`} disabled={act.busy} onClick={cands ? () => setCands(null) : loadCands}><UserPlus className="mr-1.5 h-3.5 w-3.5" />{cands ? "Hide matches" : "Suggest assignee"}</Button>}
          {s.assignee_id && !s.session_id && (s.can_schedule || goal.can_manage) && <Button size="sm" variant="outline" data-testid={`subtask-${s.id}-suggest-slot`} disabled={act.busy} onClick={slot ? () => setSlot(null) : loadSlot}><CalendarPlus className="mr-1.5 h-3.5 w-3.5" />{slot ? "Hide slot" : "Suggest slot"}</Button>}
        </div>
      )}
      {cands && <Candidates data={cands} people={people} busy={act.busy} onAssign={(id, reason) => patch({ assignee_id: id, assignment_reason: reason }, "Assigned")} />}
      {slot && <Slot slot={slot} canSchedule={s.can_schedule} busy={act.busy} onAccept={() => schedule(slot)} />}
    </li>
  );
};

export const GoalSheet = ({ goalId, onClose, onChanged }) => {
  const [goal, setGoal] = useState(null);
  const [error, setError] = useState("");
  const [people, setPeople] = useState([]);
  const [summary, setSummary] = useState(null);
  const act = useAction();

  const load = useCallback(async () => {
    if (!goalId) return;
    setError("");
    try {
      const [{ data }, ppl] = await Promise.all([api.get(`/tasks/${goalId}`), api.get("/tasks/people").catch(() => ({ data: { people: [] } }))]);
      setGoal(data); setPeople(ppl.data.people);
    } catch (e) { setError(formatApiError(e)); }
  }, [goalId]);

  useEffect(() => { setGoal(null); setSummary(null); load(); }, [load]);
  const refresh = (g) => { if (g) setGoal(g); else load(); onChanged(); };

  const close = async () => {
    const res = await act.run(() => api.patch(`/tasks/${goalId}`, { status: "done", summary: summary || "" }), "Goal completed");
    if (res) { setSummary(null); refresh(res); }
  };
  const remove = async () => {
    if (!window.confirm("Delete this goal and all its sub-tasks? This can't be undone.")) return;
    const res = await act.run(() => api.delete(`/tasks/${goalId}`), "Goal deleted");
    if (res) { onChanged(); onClose(); }
  };

  const waves = goal ? Array.from({ length: goal.waves }, (_, w) => goal.subtasks.filter((s) => s.wave === w)) : [];
  return (
    <Sheet open={!!goalId} onOpenChange={(o) => !o && onClose()}>
      <SheetContent data-testid="goal-sheet" className="w-full overflow-y-auto sm:max-w-2xl">
        <SheetHeader className="mb-4 text-left">
          <SheetTitle data-testid="goal-title">{goal?.title || "Goal"}</SheetTitle>
          <SheetDescription>{goal ? `Owner: ${goal.owner_name}${goal.deadline ? ` · due ${fmtDateTime(goal.deadline)}` : ""}` : "Loading"}</SheetDescription>
        </SheetHeader>
        {error ? <ErrorState message={error} onRetry={load} /> : !goal ? <Skeleton className="h-64" /> : (
          <div className="space-y-5">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-1.5">
                <StatusPill tone={goal.status === "done" ? "success" : "accent"}>{goal.status === "done" ? "Completed" : "Open"}</StatusPill>
                <StatusPill tone={PRIORITY_TONE[goal.priority]}>{goal.priority} priority</StatusPill>
                <span className="text-xs text-slate-500">{goal.progress.done}/{goal.progress.total} done · <Estimate low={goal.estimate_low} high={goal.estimate_high} /> total · {goal.waves} wave{goal.waves !== 1 ? "s" : ""}</span>
              </div>
              <Progress pct={goal.progress.pct} />
              {goal.description && <p className="whitespace-pre-wrap text-sm text-slate-600">{goal.description}</p>}
            </div>
            {act.error && <p className="text-sm text-red-600" role="alert">{act.error}</p>}
            {goal.ready_to_consolidate && goal.can_manage && (
              <div data-testid="consolidate-panel" className="rounded-md border border-emerald-200 bg-emerald-50/60 p-3">
                <div className="flex items-center gap-1.5 text-sm font-medium text-emerald-800"><CheckCircle2 className="h-4 w-4" />Every sub-task is done. Consolidate the outputs and close the goal.</div>
                {summary === null ? <Button size="sm" className="mt-2" data-testid="goal-consolidate" onClick={() => setSummary(goal.subtasks.map((s) => `- ${s.title}: ${s.output?.summary || "Done"}`).join("\n"))}>Review outputs</Button> : (
                  <div className="mt-2 space-y-2">
                    <TextArea id="goal-summary" label="Consolidated summary" rows={6} value={summary} onChange={(e) => setSummary(e.target.value)} />
                    <Button size="sm" data-testid="goal-close" disabled={act.busy} onClick={close}>Close goal</Button>
                  </div>
                )}
              </div>
            )}
            {goal.status === "done" && goal.summary && <div><div className="eyebrow mb-1">Consolidated summary</div><p className="whitespace-pre-wrap text-sm text-slate-700">{goal.summary}</p></div>}
            {waves.map((items, w) => (
              <section key={w} data-testid={`wave-${w}`}>
                <div className="eyebrow mb-2 flex items-center gap-1.5"><Users className="h-3 w-3" />Wave {w + 1} · {w === 0 ? "can start now" : `after wave ${w}`}{items.length > 1 ? ` · ${items.length} sub-tasks can run in parallel` : ""}</div>
                <ul className="space-y-2">{items.map((s) => <SubtaskCard key={s.id} s={s} goal={goal} people={people} reload={refresh} />)}</ul>
              </section>
            ))}
            <p className="text-xs text-slate-400">Orqestra plans work; people do it in their own AI tools. Moving work never moves provider quota or shares logins.</p>
            {goal.can_manage && <Button size="sm" variant="ghost" className="text-red-600" data-testid="goal-delete" onClick={remove}><Trash2 className="mr-1.5 h-4 w-4" />Delete goal</Button>}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
};
