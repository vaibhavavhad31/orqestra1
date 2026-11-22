import { useState } from "react";
import { CalendarRange, ChevronLeft, ChevronRight, Info, Plus } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader, Panel } from "@/components/common/Layout";
import { EmptyState, ErrorState } from "@/components/common/States";
import { Skeleton } from "@/components/ui/skeleton";
import { WeekView, SessionCard } from "@/components/planner/WeekView";
import { SessionDialog, SuggestDialog } from "@/components/planner/SessionDialogs";
import { ResetPanel } from "@/components/planner/ResetPanel";
import { weekStart } from "@/lib/time";

const DISCLAIMER = "Planning sessions does not create extra provider capacity or bypass usage limits.";

const WeekNav = ({ offset, setOffset, start }) => {
  const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 6);
  const f = (d) => d.toLocaleDateString([], { month: "short", day: "numeric" });
  return (
    <div className="flex items-center gap-1">
      <Button size="icon" variant="outline" className="h-9 w-9" aria-label="Previous week" data-testid="week-prev" onClick={() => setOffset(offset - 1)}><ChevronLeft className="h-4 w-4" /></Button>
      <Button size="sm" variant="outline" className="h-9" data-testid="week-today" onClick={() => setOffset(0)}>This week</Button>
      <Button size="icon" variant="outline" className="h-9 w-9" aria-label="Next week" data-testid="week-next" onClick={() => setOffset(offset + 1)}><ChevronRight className="h-4 w-4" /></Button>
      <span data-testid="week-label" className="ml-2 text-xs text-slate-500">{f(start)} – {f(end)}</span>
    </div>
  );
};

export default function Planner() {
  const { user } = useAuth();
  const canTeam = user.mode === "organisation" && ["admin", "manager"].includes(user.role);
  const [tab, setTab] = useState("mine");
  const [offset, setOffset] = useState(0);
  const [member, setMember] = useState("all");
  const [dialog, setDialog] = useState({ open: false, session: null });
  const [suggest, setSuggest] = useState(null);
  const start = weekStart(offset);
  const range = { start: start.toISOString(), end: new Date(start.getFullYear(), start.getMonth(), start.getDate() + 7).toISOString() };
  const team = tab === "team";
  const { data: raw, error, reload } = useApi(team ? "/planner/team" : "/planner/sessions", { ...range, member_id: team && member !== "all" ? member : undefined });
  const data = raw && (team ? raw.members : !raw.members) ? raw : null;
  const mine = useApi("/planner/sessions");
  const refresh = () => { reload(); mine.reload(); };

  return (
    <div data-testid="planner-page" className="space-y-6 sm:space-y-8">
      <PageHeader eyebrow={user.mode === "organisation" ? "Organisation" : "Personal workspace"} title="Session Planner" description="Plan AI-heavy work around the capacity you have"
        actions={<Button data-testid="open-session-dialog" onClick={() => setDialog({ open: true, session: null })}><Plus className="mr-1.5 h-4 w-4" />Plan session</Button>} />
      <p data-testid="planner-disclaimer" className="flex items-start gap-2 rounded-md border border-border bg-slate-50 px-3.5 py-2.5 text-sm text-slate-600">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" /> {DISCLAIMER}
      </p>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {canTeam ? (
          <Tabs value={tab} onValueChange={setTab}><TabsList className="h-9">
            <TabsTrigger value="mine" data-testid="planner-tab-mine" className="px-3 text-xs">My planner</TabsTrigger>
            <TabsTrigger value="team" data-testid="planner-tab-team" className="px-3 text-xs">Team</TabsTrigger>
          </TabsList></Tabs>
        ) : <span />}
        <div className="flex flex-wrap items-center gap-2">
          {team && data?.members && (
            <Select value={member} onValueChange={setMember}>
              <SelectTrigger data-testid="planner-member-filter" aria-label="Filter by member" className="h-9 w-[180px] bg-white"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all" data-testid="planner-member-all">All members</SelectItem>
                {data.members.map((m) => <SelectItem key={m.id} value={m.id} data-testid={`planner-member-${m.id}`}>{m.name}</SelectItem>)}
              </SelectContent>
            </Select>
          )}
          <WeekNav offset={offset} setOffset={setOffset} start={start} />
        </div>
      </div>
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12 xl:items-start">
        <Panel testId="planner-week-panel" title={team ? "Team sessions" : "Your week"} className="xl:col-span-9">
          {error ? <ErrorState message={error} onRetry={reload} /> : !data ? <Skeleton className="h-56" /> : (
            <WeekView start={start} sessions={data.sessions} team={team} onChanged={refresh}
              onEdit={(s) => setDialog({ open: true, session: s })} onSuggest={setSuggest} />
          )}
        </Panel>
        <div className="space-y-6 xl:col-span-3">
          <Panel testId="planner-upcoming-panel" title="Upcoming">
            {!mine.data ? <Skeleton className="h-24" /> : mine.data.upcoming.length === 0
              ? <EmptyState icon={CalendarRange} title="Nothing planned" description="Plan a session to see it here." />
              : <div data-testid="planner-upcoming-list" className="space-y-2">{mine.data.upcoming.slice(0, 6).map((s) => (
                <SessionCard key={s.id} s={s} onChanged={refresh} onEdit={(x) => setDialog({ open: true, session: x })} />
              ))}</div>}
          </Panel>
          <Panel testId="planner-resets-panel" title="Provider reset times" description="Entered by you, not read from providers">
            <ResetPanel />
          </Panel>
        </div>
      </div>
      <SessionDialog open={dialog.open} session={dialog.session} sessions={mine.data?.upcoming || []}
        onClose={() => setDialog({ open: false, session: null })} onSaved={() => { setDialog({ open: false, session: null }); refresh(); }} />
      <SuggestDialog session={suggest} onClose={() => setSuggest(null)} onSaved={() => { setSuggest(null); refresh(); }} />
    </div>
  );
}
