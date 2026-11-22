import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/States";
import { LendingDisclaimer } from "@/components/lending/LendingDisclaimer";
import { LendingStatus, OverdueBadge } from "@/components/lending/LendingStatus";
import { Timeline } from "@/components/lending/Timeline";
import { fmt, fmtDay } from "@/lib/format";

const Stat = ({ label, value, testId }) => (
  <div className="rounded-md border border-border-subtle bg-slate-50/60 px-3 py-2.5">
    <div className="text-[11px] text-slate-500">{label}</div>
    <div data-testid={testId} className="num mt-0.5 text-base font-semibold text-slate-900">{value}</div>
  </div>
);

const RepayForm = ({ entry, act }) => {
  const [amount, setAmount] = useState("");
  const max = entry.outstanding - entry.awaiting_repayment;
  return (
    <form noValidate className="space-y-1.5" onSubmit={async (e) => { e.preventDefault(); if (await act.do(`/lending/entries/${entry.id}/repayments`, { amount: amount === "" ? "" : Number(amount) }, "Repayment recorded")) setAmount(""); }}>
      <label htmlFor="repay-amount" className="text-xs font-medium text-slate-700">Record a repayment (up to {fmt(max)})</label>
      <div className="flex gap-2">
        <Input id="repay-amount" data-testid="repay-amount" type="number" inputMode="numeric" min="1" step="1" value={amount}
          onChange={(e) => setAmount(e.target.value)} className={`h-10 bg-white ${act.fields.amount ? "border-red-400" : ""}`} />
        <Button type="submit" data-testid="repay-submit" disabled={act.busy} className="h-10 shrink-0">Record</Button>
      </div>
      {act.fields.amount && <p data-testid="repay-error" className="text-xs text-red-600">{act.fields.amount}</p>}
      <p className="text-xs text-slate-500">The lender confirms or disputes it before the balance changes.</p>
    </form>
  );
};

const Actions = ({ entry, act }) => (
  <div className="space-y-4">
    {(entry.actions.accept || entry.actions.cancel) && (
      <div className="flex flex-wrap gap-2">
        {entry.actions.accept && <Button data-testid="entry-accept" disabled={act.busy} onClick={() => act.do(`/lending/entries/${entry.id}/accept`, {}, "Accepted")}>Accept</Button>}
        {entry.actions.decline && <Button data-testid="entry-decline" variant="outline" disabled={act.busy} onClick={() => act.do(`/lending/entries/${entry.id}/decline`, {}, "Declined")}>Decline</Button>}
        {entry.actions.cancel && <Button data-testid="entry-cancel" variant="outline" disabled={act.busy} onClick={() => act.do(`/lending/entries/${entry.id}/cancel`, {}, "Cancelled")}>Cancel {entry.kind === "offer" ? "offer" : "request"}</Button>}
      </div>
    )}
    {entry.actions.repay && <RepayForm entry={entry} act={act} />}
    {entry.repayments.length > 0 && (
      <div>
        <div className="eyebrow mb-2">Repayments</div>
        <ul className="space-y-2">
          {entry.repayments.map((r) => (
            <li key={r.id} data-testid={`repayment-${r.id}`} className="flex flex-wrap items-center gap-2 rounded-md border border-border-subtle px-3 py-2">
              <span className="num text-sm font-medium text-slate-900">{fmt(r.amount)}</span>
              <span className="text-xs text-slate-500">{fmtDay(r.created_at.slice(0, 10))}</span>
              <LendingStatus status={r.status} testId={`repayment-${r.id}-status`} />
              {r.can_confirm && (
                <span className="ml-auto flex gap-1.5">
                  <Button size="sm" data-testid={`repayment-${r.id}-confirm`} disabled={act.busy} onClick={() => act.do(`/lending/repayments/${r.id}/confirm`, {}, "Repayment confirmed")}>Confirm</Button>
                  <Button size="sm" variant="outline" data-testid={`repayment-${r.id}-dispute`} disabled={act.busy} onClick={() => act.do(`/lending/repayments/${r.id}/dispute`, {}, "Repayment disputed")}>Dispute</Button>
                </span>
              )}
            </li>
          ))}
        </ul>
      </div>
    )}
  </div>
);

const Body = ({ entry, act }) => (
  <div className="space-y-6">
    <div className="flex flex-wrap items-center gap-1.5">
      <LendingStatus status={entry.status} testId="entry-status" />
      {entry.overdue && <OverdueBadge testId="entry-overdue" />}
      <span className="text-xs text-slate-500">{entry.kind === "offer" ? "Lend offer" : "Borrow request"}{entry.due_date ? ` · due ${fmtDay(entry.due_date)}` : ""}</span>
    </div>
    {entry.note && <p data-testid="entry-note" className="text-sm text-slate-600">“{entry.note}”</p>}
    <div className="grid grid-cols-3 gap-2">
      <Stat label="Amount" value={fmt(entry.credits)} testId="entry-amount" />
      <Stat label="Repaid" value={fmt(entry.repaid_credits)} testId="entry-repaid" />
      <Stat label="Outstanding" value={fmt(entry.outstanding)} testId="entry-outstanding" />
    </div>
    {act.error && <p data-testid="entry-action-error" role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{act.error}</p>}
    <Actions entry={entry} act={act} />
    <div>
      <div className="eyebrow mb-3">History</div>
      <Timeline items={entry.history} />
    </div>
    <LendingDisclaimer testId="entry-disclaimer" />
  </div>
);

export const EntrySheet = ({ entryId, onClose, onChanged }) => {
  const [entry, setEntry] = useState(null);
  const [loadError, setLoadError] = useState("");
  const action = useAction();

  const load = useCallback(async () => {
    setLoadError("");
    try { setEntry((await api.get(`/lending/entries/${entryId}`)).data); } catch (e) { setLoadError(formatApiError(e)); }
  }, [entryId]);

  useEffect(() => { setEntry(null); action.reset(); if (entryId) load(); }, [entryId, load]); // eslint-disable-line react-hooks/exhaustive-deps

  const act = {
    ...action,
    do: async (path, body, success) => {
      const res = await action.run(() => api.post(path, body), success);
      if (res) { setEntry(res); onChanged(); } else load();
      return res;
    },
  };

  return (
    <Sheet open={!!entryId} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" data-testid="entry-sheet" className="w-full overflow-y-auto sm:max-w-md">
        <SheetHeader className="mb-5 text-left">
          <SheetTitle data-testid="entry-title">
            {entry ? `${entry.direction === "lent" ? "Lent to" : "Borrowed from"} ${entry.counterparty_name}` : "Lending entry"}
          </SheetTitle>
          <SheetDescription>{entry ? `Created ${fmtDay(entry.created_at.slice(0, 10))}` : "Loading details"}</SheetDescription>
        </SheetHeader>
        {loadError ? <ErrorState message={loadError} onRetry={load} /> : entry ? <Body entry={entry} act={act} /> : <Skeleton className="h-64" />}
      </SheetContent>
    </Sheet>
  );
};
