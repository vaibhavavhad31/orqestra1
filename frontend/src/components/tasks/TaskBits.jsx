import { StatusPill } from "@/components/common/StatusPill";
import { fmt } from "@/lib/format";

export const TYPES = ["planning", "research", "code", "writing", "design", "analysis", "review"];
export const SUB_STATUS = { todo: "neutral", in_progress: "info", blocked: "warning", done: "success" };
export const STATUS_LABEL = { todo: "To do", in_progress: "In progress", blocked: "Blocked", done: "Done" };
export const PRIORITY_TONE = { low: "neutral", medium: "info", high: "warning", urgent: "danger" };

export const SubStatus = ({ status, testId }) => <StatusPill tone={SUB_STATUS[status]} testId={testId}>{STATUS_LABEL[status] || status}</StatusPill>;
export const TypePill = ({ type }) => <StatusPill tone="accent" className="capitalize">{type}</StatusPill>;
export const Estimate = ({ low, high }) => <span className="num">{fmt(low)}–{fmt(high)} credits</span>;

// Small label saying where a number came from: verified, entered by a person, estimated, simulated or unavailable.
export const Provenance = ({ children, testId }) => (
  <span data-testid={testId} className="inline-flex items-center gap-1 text-[11px] text-slate-400">
    <span className="h-1 w-1 rounded-full bg-slate-300" />{children}
  </span>
);

export const Progress = ({ pct }) => (
  <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
    <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${pct}%` }} />
  </div>
);

// Same dependency levels the server computes: wave n can start once every dependency in earlier waves is done.
export function computeWaves(subtasks) {
  const n = subtasks.length;
  const waves = Array(n).fill(-1);
  const state = Array(n).fill(0);
  let cycle = false;
  const visit = (i) => {
    if (state[i] === 1) { cycle = true; return 0; }
    if (state[i] === 2) return waves[i];
    state[i] = 1;
    const deps = (subtasks[i].depends_on || []).filter((d) => d >= 0 && d < n && d !== i);
    waves[i] = 1 + Math.max(-1, ...deps.map(visit));
    state[i] = 2;
    return waves[i];
  };
  for (let i = 0; i < n; i++) visit(i);
  return { waves, cycle };
}

export const selectCls = "focus-ring h-9 w-full rounded-md border border-input bg-white px-2 text-sm";
