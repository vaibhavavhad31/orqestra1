import { ArrowDownLeft, ArrowLeftRight, ArrowUpRight, ChevronRight } from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/common/States";
import { Skeleton } from "@/components/ui/skeleton";
import { LendingStatus, OverdueBadge } from "@/components/lending/LendingStatus";
import { fmt, fmtDay } from "@/lib/format";

const TABS = [["all", "All"], ["borrowed", "Borrowed"], ["lent", "Lent"], ["pending", "Pending"]];

const EntryRow = ({ e, onOpen }) => (
  <li>
    <button type="button" data-testid={`lending-entry-${e.id}`} onClick={() => onOpen(e.id)}
      className="focus-ring flex w-full items-center gap-3 px-5 py-3.5 text-left transition-colors duration-150 hover:bg-slate-50">
      <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md border ${e.direction === "lent" ? "border-indigo-100 bg-indigo-50 text-indigo-600" : "border-slate-200 bg-slate-50 text-slate-600"}`}>
        {e.direction === "lent" ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownLeft className="h-4 w-4" />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="truncate text-sm font-medium text-slate-900">{e.counterparty_name}</span>
          {e.needs_my_action && <span data-testid={`lending-entry-${e.id}-action-needed`} className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-label="Action needed" />}
        </div>
        <div className="truncate text-xs text-slate-500">
          {e.direction === "lent" ? "You lent" : "You borrowed"} · {fmtDay(e.created_at.slice(0, 10))}{e.due_date ? ` · due ${fmtDay(e.due_date)}` : ""}
        </div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className="num text-sm font-semibold text-slate-900">{fmt(e.credits)}</span>
        <div className="flex items-center gap-1">
          {e.overdue && <OverdueBadge testId={`lending-entry-${e.id}-overdue`} />}
          <LendingStatus status={e.status} testId={`lending-entry-${e.id}-status`} />
        </div>
      </div>
      <ChevronRight className="hidden h-4 w-4 shrink-0 text-slate-300 sm:block" />
    </button>
  </li>
);

export const EntryList = ({ tab, setTab, entries, onOpen }) => (
  <div>
    <div className="overflow-x-auto border-b border-border-subtle px-5 py-3">
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList data-testid="lending-tabs" className="h-9">
          {TABS.map(([id, label]) => (
            <TabsTrigger key={id} value={id} data-testid={`lending-tab-${id}`} className="px-3 text-xs">{label}</TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
    </div>
    {entries === null ? (
      <div className="space-y-2 p-5">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-14" />)}</div>
    ) : entries.length === 0 ? (
      <div className="p-5"><EmptyState icon={ArrowLeftRight} title="Nothing here yet" description="Request or lend credits to a friend to start tracking obligations." /></div>
    ) : (
      <ul data-testid="lending-entry-list" className="divide-y divide-border-subtle">
        {entries.map((e) => <EntryRow key={e.id} e={e} onOpen={onOpen} />)}
      </ul>
    )}
  </div>
);

export const outstandingLabel = (e) => `${fmt(e.outstanding)} outstanding`;
