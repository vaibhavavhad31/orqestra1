import { useState } from "react";
import { Inbox, X } from "lucide-react";
import { api } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/common/States";
import { StatusPill } from "@/components/common/StatusPill";
import { fmt, fmtDay } from "@/lib/format";

const STATUS = { pending: "warning", approved: "success", rejected: "danger", cancelled: "neutral" };
const URGENCY = { high: "danger", normal: "neutral", low: "info" };

const RequestRow = ({ r, canDecide, canCancel, onDecide, onCancel, busy }) => (
  <li data-testid={`request-row-${r.id}`} className="space-y-2 px-5 py-4">
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm font-medium text-slate-900">{canDecide ? r.requester_name : "Your request"}</span>
      {canDecide && r.department && <span className="text-xs text-slate-500">{r.department}</span>}
      <span className="num text-sm font-semibold text-slate-900">{fmt(r.credits)} credits</span>
      <StatusPill tone={URGENCY[r.urgency]} testId={`request-urgency-${r.id}`}>{r.urgency} urgency</StatusPill>
      <StatusPill tone={STATUS[r.status]} testId={`request-status-${r.id}`}>{r.status}</StatusPill>
      <span className="ml-auto text-xs text-slate-400">{fmtDay(r.created_at.slice(0, 10))}</span>
    </div>
    <p className="text-sm text-slate-600">{r.reason}</p>
    {r.status === "approved" && <p data-testid={`request-approved-${r.id}`} className="text-xs text-emerald-700">Approved {fmt(r.approved_credits)} credits{r.decided_by_name ? ` by ${r.decided_by_name}` : ""}</p>}
    {r.status === "rejected" && (
      <p data-testid={`request-note-${r.id}`} className="rounded-md bg-red-50 px-2.5 py-1.5 text-xs text-red-700">
        Rejected{r.decided_by_name ? ` by ${r.decided_by_name}` : ""}{r.decision_note ? `: “${r.decision_note}”` : ""}
      </p>
    )}
    {r.status === "pending" && (canDecide || canCancel) && (
      <div className="flex flex-wrap gap-2 pt-1">
        {canDecide && <Button size="sm" data-testid={`request-approve-${r.id}`} onClick={() => onDecide({ type: "approve", request: r })}>Approve</Button>}
        {canDecide && <Button size="sm" variant="outline" data-testid={`request-reject-${r.id}`} onClick={() => onDecide({ type: "reject", request: r })}>Reject</Button>}
        {canCancel && <Button size="sm" variant="outline" disabled={busy} data-testid={`request-cancel-${r.id}`} onClick={() => onCancel(r.id)}><X className="mr-1 h-3.5 w-3.5" />Cancel request</Button>}
      </div>
    )}
  </li>
);

export const RequestsList = ({ requests, canDecide, onDecide, onChanged }) => {
  const [tab, setTab] = useState("pending");
  const { run, busy } = useAction();
  const shown = tab === "pending" ? requests.filter((r) => r.status === "pending") : requests;
  const cancel = async (id) => { if (await run(() => api.post(`/allocation/requests/${id}/cancel`), "Request cancelled")) onChanged(); };
  return (
    <div>
      <div className="border-b border-border-subtle px-5 py-3">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="h-9">
            <TabsTrigger value="pending" data-testid="requests-tab-pending" className="px-3 text-xs">Pending · {requests.filter((r) => r.status === "pending").length}</TabsTrigger>
            <TabsTrigger value="all" data-testid="requests-tab-all" className="px-3 text-xs">All</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      {shown.length === 0
        ? <div className="p-5"><EmptyState icon={Inbox} title="No requests" description={tab === "pending" ? "Nothing is waiting for a decision." : "No resource requests yet."} /></div>
        : <ul data-testid="requests-list" className="divide-y divide-border-subtle">
            {shown.map((r) => <RequestRow key={r.id} r={r} canDecide={canDecide} canCancel={!canDecide} onDecide={onDecide} onCancel={cancel} busy={busy} />)}
          </ul>}
    </div>
  );
};
