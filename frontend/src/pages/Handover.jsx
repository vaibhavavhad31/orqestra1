import { useState } from "react";
import { ChevronRight, GitPullRequestArrow, Plus, ShieldCheck } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader, Panel } from "@/components/common/Layout";
import { EmptyState, ErrorState } from "@/components/common/States";
import { Skeleton } from "@/components/ui/skeleton";
import { HandoverDialog } from "@/components/handover/HandoverDialog";
import { HandoverSheet } from "@/components/handover/HandoverSheet";
import { HandoverStatus, PriorityPill } from "@/components/handover/HandoverBits";
import { fmtDay } from "@/lib/format";

const STATUSES = ["all", "pending", "accepted", "completed", "rejected", "cancelled"];

const Row = ({ t, onOpen }) => (
  <li>
    <button type="button" data-testid={`handover-row-${t.id}`} onClick={() => onOpen(t.id)}
      className="focus-ring flex w-full items-center gap-3 px-5 py-3.5 text-left hover:bg-slate-50">
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-slate-900">{t.title}</div>
        <div className="truncate text-xs text-slate-500">{t.creator_name} → {t.assignee_name} · {fmtDay(t.created_at.slice(0, 10))}{t.attachment_count ? ` · ${t.attachment_count} file${t.attachment_count > 1 ? "s" : ""}` : ""}</div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1 sm:flex-row sm:items-center">
        <PriorityPill priority={t.priority} /><HandoverStatus status={t.status} testId={`handover-row-${t.id}-status`} />
      </div>
      <ChevronRight className="hidden h-4 w-4 text-slate-300 sm:block" />
    </button>
  </li>
);

export default function Handover() {
  const { user } = useAuth();
  const canAll = user.mode === "organisation" && ["admin", "manager"].includes(user.role);
  const [box, setBox] = useState("received");
  const [status, setStatus] = useState("all");
  const [dialog, setDialog] = useState({ open: false, task: null });
  const [params] = useSearchParams();
  const [openId, setOpenId] = useState(params.get("open"));
  const { data, error, reload } = useApi("/handovers", { box, status: status === "all" ? undefined : status });

  return (
    <div data-testid="handover-page" className="space-y-6 sm:space-y-8">
      <PageHeader eyebrow={user.mode === "organisation" ? "Organisation" : "Personal workspace"} title="Task Handover"
        description="Pass work on with the context it needs"
        actions={<Button data-testid="open-handover-dialog" onClick={() => setDialog({ open: true, task: null })}><Plus className="mr-1.5 h-4 w-4" />New handover</Button>} />
      <p data-testid="handover-privacy-note" className="flex items-start gap-2 rounded-md border border-border bg-slate-50 px-3.5 py-2.5 text-sm text-slate-600">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" /> Only the context you add here is shared. Your AI chat history is never shared.
      </p>
      <Panel testId="handover-list-panel" bodyClassName="p-0" title="Handovers"
        action={<Tabs value={box} onValueChange={setBox}><TabsList className="h-9">
          {["received", "sent", ...(canAll ? ["all"] : [])].map((b) => <TabsTrigger key={b} value={b} data-testid={`handover-tab-${b}`} className="px-3 text-xs capitalize">{b}</TabsTrigger>)}
        </TabsList></Tabs>}>
        <div className="flex gap-1.5 overflow-x-auto border-b border-border-subtle px-5 py-3" role="group" aria-label="Status filter">
          {STATUSES.map((s) => (
            <button key={s} type="button" data-testid={`handover-filter-${s}`} onClick={() => setStatus(s)}
              className={`focus-ring min-h-[32px] shrink-0 rounded-full border px-3 text-xs capitalize ${status === s ? "border-slate-900 bg-slate-900 text-white" : "border-border bg-white text-slate-600 hover:bg-slate-50"}`}>{s}</button>
          ))}
        </div>
        {error ? <div className="p-5"><ErrorState message={error} onRetry={reload} /></div>
          : !data ? <div className="space-y-2 p-5">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-14" />)}</div>
          : data.tasks.length === 0 ? <div className="p-5"><EmptyState icon={GitPullRequestArrow} title="No handovers here" description="Hand over a task with its context when you need someone else to continue it." /></div>
          : <ul data-testid="handover-list" className="divide-y divide-border-subtle">{data.tasks.map((t) => <Row key={t.id} t={t} onOpen={setOpenId} />)}</ul>}
      </Panel>
      <HandoverDialog open={dialog.open} task={dialog.task} onClose={() => setDialog({ open: false, task: null })}
        onSaved={(t) => { setDialog({ open: false, task: null }); reload(); setOpenId(null); setTimeout(() => setOpenId(t.id), 0); }} />
      <HandoverSheet taskId={openId} onClose={() => setOpenId(null)} onChanged={reload}
        onEdit={(t) => { setOpenId(null); setDialog({ open: true, task: t }); }} />
    </div>
  );
}
