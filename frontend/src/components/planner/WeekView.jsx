import { AlertTriangle, Clock } from "lucide-react";
import { api } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Button } from "@/components/ui/button";
import { StatusPill } from "@/components/common/StatusPill";
import { dayKey, fmtDateTime, fmtTime, useIsDesktop, weekDays } from "@/lib/time";
import { fmt } from "@/lib/format";

const TONE = { planned: "accent", completed: "success", cancelled: "neutral" };

export const SessionCard = ({ s, team, onEdit, onSuggest, onChanged, compact }) => {
  const { run, busy } = useAction();
  const post = async (path, msg) => { if (await run(() => api.post(path), msg)) onChanged(); };
  const sug = s.suggestion?.status === "pending" ? s.suggestion : null;
  return (
    <div data-testid={`session-${s.id}`} className="space-y-1.5 rounded-md border border-border bg-white p-2.5 text-left shadow-[0_1px_2px_rgba(16,24,40,0.04)]"
      style={{ borderLeft: `3px solid ${s.provider_color || "#94A3B8"}` }}>
      <div className={compact ? "space-y-1" : "flex items-center justify-between gap-1"}>
        <span data-testid={`session-${s.id}-time`} className="num block text-xs font-medium text-slate-900">{compact ? fmtTime(s.start_at) : `${fmtDateTime(s.start_at)}–${fmtTime(s.end_at)}`}</span>
        {(!compact || s.status !== "planned") && <StatusPill tone={TONE[s.status]} testId={`session-${s.id}-status`}>{s.status}</StatusPill>}
      </div>
      <p className="text-sm leading-snug text-slate-800">{s.purpose}</p>
      <p className="break-words text-[11px] text-slate-500">{s.provider_name} · {fmt(s.estimated_credits)} cr{team ? ` · ${s.user_name}` : ""}{!compact && s.reminder_min ? ` · reminder ${s.reminder_min}m` : ""}</p>
      {s.overlaps && <p data-testid={`session-${s.id}-overlap`} className="flex items-center gap-1 text-[11px] text-amber-700"><AlertTriangle className="h-3 w-3" />Overlaps another session</p>}
      {sug && (
        <div data-testid={`session-${s.id}-suggestion`} className="rounded bg-indigo-50 px-2 py-1.5 text-[11px] text-indigo-800">
          <Clock className="mr-1 inline h-3 w-3" />{sug.by_name} suggests {fmtDateTime(sug.start_at)}{sug.note ? `: “${sug.note}”` : ""}
          {s.mine && !team && (
            <span className="mt-1 flex gap-1.5">
              <Button size="sm" className="h-7 px-2 text-xs" disabled={busy} data-testid={`session-${s.id}-suggestion-accept`} onClick={() => post(`/planner/sessions/${s.id}/suggestion/accept`, "New time accepted")}>Accept</Button>
              <Button size="sm" variant="outline" className="h-7 px-2 text-xs" disabled={busy} data-testid={`session-${s.id}-suggestion-dismiss`} onClick={() => post(`/planner/sessions/${s.id}/suggestion/dismiss`, "Suggestion dismissed")}>Dismiss</Button>
            </span>
          )}
        </div>
      )}
      {s.status === "planned" && (
        <div className="flex flex-wrap gap-1 pt-0.5">
          {team ? <Button size="sm" variant="outline" className="h-8 px-2 text-xs" data-testid={`session-${s.id}-suggest`} onClick={() => onSuggest(s)}>Suggest time</Button> : <>
            <Button size="sm" variant="ghost" className="h-8 px-2 text-xs" data-testid={`session-${s.id}-edit`} onClick={() => onEdit(s)}>Edit</Button>
            <Button size="sm" variant="ghost" className="h-8 px-2 text-xs" disabled={busy} data-testid={`session-${s.id}-complete`} onClick={() => post(`/planner/sessions/${s.id}/complete`, "Marked completed")}>Complete</Button>
            <Button size="sm" variant="ghost" className="h-8 px-2 text-xs text-red-600" disabled={busy} data-testid={`session-${s.id}-cancel`} onClick={() => post(`/planner/sessions/${s.id}/cancel`, "Session cancelled")}>Cancel</Button>
          </>}
        </div>
      )}
    </div>
  );
};

export const WeekView = ({ start, sessions, ...cardProps }) => {
  const desktop = useIsDesktop();
  const days = weekDays(start);
  const byDay = Object.fromEntries(days.map((d) => [dayKey(d), []]));
  sessions.forEach((s) => { const k = dayKey(new Date(s.start_at)); if (byDay[k]) byDay[k].push(s); });
  const label = (d) => d.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" });
  const today = dayKey(new Date());
  if (!desktop) {
    return (
      <div data-testid="planner-list-view" className="space-y-4">
        {days.map((d) => (
          <div key={dayKey(d)}>
            <div className={`eyebrow mb-1.5 ${dayKey(d) === today ? "text-indigo-600" : ""}`}>{label(d)}</div>
            {byDay[dayKey(d)].length ? <div className="space-y-2">{byDay[dayKey(d)].map((s) => <SessionCard key={s.id} s={s} {...cardProps} />)}</div>
              : <p className="text-xs text-slate-400">No sessions</p>}
          </div>
        ))}
      </div>
    );
  }
  return (
    <div data-testid="planner-week-grid" className="grid grid-cols-7 gap-2">
      {days.map((d) => (
        <div key={dayKey(d)} data-testid={`planner-day-${dayKey(d)}`} className={`min-h-[220px] min-w-0 rounded-md border p-1.5 ${dayKey(d) === today ? "border-indigo-200 bg-indigo-50/40" : "border-border-subtle bg-slate-50/50"}`}>
          <div className="mb-1.5 px-1 text-[11px] font-medium text-slate-500">{label(d)}</div>
          <div className="space-y-1.5">{byDay[dayKey(d)].map((s) => <SessionCard key={s.id} s={s} compact {...cardProps} />)}</div>
        </div>
      ))}
    </div>
  );
};
