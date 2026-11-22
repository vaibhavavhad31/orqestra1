import { useState } from "react";
import { ChevronRight, ListTree, Plus } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, Panel } from "@/components/common/Layout";
import { EmptyState, ErrorState } from "@/components/common/States";
import { StatusPill } from "@/components/common/StatusPill";
import { GoalDialog } from "@/components/tasks/GoalDialog";
import { GoalSheet } from "@/components/tasks/GoalSheet";
import { Estimate, PRIORITY_TONE, Progress } from "@/components/tasks/TaskBits";
import { fmtDateTime } from "@/lib/time";

const GoalRow = ({ g, onOpen }) => (
  <li>
    <button type="button" data-testid={`goal-row-${g.id}`} onClick={() => onOpen(g.id)}
      className="focus-ring flex w-full items-center gap-4 px-5 py-4 text-left hover:bg-slate-50">
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="truncate text-sm font-medium text-slate-900">{g.title}</span>
          {g.status === "done" ? <StatusPill tone="success">Completed</StatusPill> : g.ready_to_consolidate ? <StatusPill tone="success">Ready to close</StatusPill> : null}
          <StatusPill tone={PRIORITY_TONE[g.priority]}>{g.priority}</StatusPill>
        </div>
        <div className="text-xs text-slate-500">
          {g.owner_name} · {g.progress.done}/{g.progress.total} sub-tasks · {g.waves} wave{g.waves !== 1 ? "s" : ""} · <Estimate low={g.estimate_low} high={g.estimate_high} />
          {g.deadline ? ` · due ${fmtDateTime(g.deadline)}` : ""}
          {g.unassigned ? ` · ${g.unassigned} unassigned` : ""}{g.my_open ? ` · ${g.my_open} waiting on you` : ""}
        </div>
        <Progress pct={g.progress.pct} />
      </div>
      <ChevronRight className="hidden h-4 w-4 shrink-0 text-slate-300 sm:block" />
    </button>
  </li>
);

export default function Tasks() {
  const { user } = useAuth();
  const canTeam = user.mode === "organisation" && ["admin", "manager"].includes(user.role);
  const [scope, setScope] = useState("mine");
  const [creating, setCreating] = useState(false);
  const [params] = useSearchParams();
  const [openId, setOpenId] = useState(params.get("open"));
  const { data, error, reload } = useApi("/tasks", { scope });

  return (
    <div data-testid="tasks-page" className="space-y-6 sm:space-y-8">
      <PageHeader eyebrow={user.mode === "organisation" ? "Organisation" : "Personal workspace"} title="Tasks"
        description="Break goals into sub-tasks, match them to people and AI tools, and plan when they run"
        actions={<Button data-testid="open-goal-dialog" onClick={() => setCreating(true)}><Plus className="mr-1.5 h-4 w-4" />New goal</Button>} />
      <div className="grid gap-3 sm:grid-cols-3" data-testid="tasks-how">
        {[["1 · Break down", "Turn a goal into sub-tasks with dependencies. Sub-tasks in the same wave can run in parallel."],
          ["2 · Match", "Orqestra ranks people by remaining capacity, experience with the suggested tool and workload, and explains why."],
          ["3 · Plan", "Get a free slot before the deadline that respects dependencies and existing sessions, then add it to the planner."]].map(([t, d]) => (
          <div key={t} className="surface p-4"><div className="text-sm font-semibold text-slate-900">{t}</div><p className="mt-1 text-xs text-slate-500">{d}</p></div>
        ))}
      </div>
      <Panel testId="goals-panel" bodyClassName="p-0" title="Goals"
        action={canTeam && <Tabs value={scope} onValueChange={setScope}><TabsList className="h-9">
          {["mine", "team"].map((s) => <TabsTrigger key={s} value={s} data-testid={`goals-tab-${s}`} className="px-3 text-xs capitalize">{s === "mine" ? "Mine" : user.role === "admin" ? "Organisation" : "My department"}</TabsTrigger>)}
        </TabsList></Tabs>}>
        {error ? <div className="p-5"><ErrorState message={error} onRetry={reload} /></div>
          : !data ? <div className="space-y-2 p-5">{[0, 1].map((i) => <Skeleton key={i} className="h-16" />)}</div>
          : data.goals.length === 0 ? <div className="p-5"><EmptyState icon={ListTree} title="No goals yet" description="Create a goal and let Orqestra break it into sub-tasks you can assign and plan." /></div>
          : <ul data-testid="goals-list" className="divide-y divide-border-subtle">{data.goals.map((g) => <GoalRow key={g.id} g={g} onOpen={setOpenId} />)}</ul>}
      </Panel>
      <GoalDialog open={creating} onClose={() => setCreating(false)} onSaved={(g) => { setCreating(false); reload(); setOpenId(g.id); }} />
      <GoalSheet goalId={openId} onClose={() => setOpenId(null)} onChanged={reload} />
    </div>
  );
}
