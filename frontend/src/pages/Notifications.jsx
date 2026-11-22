import { useState } from "react";
import { Bell, CheckCheck, ChevronRight, ListTodo } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, Panel } from "@/components/common/Layout";
import { EmptyState, ErrorState } from "@/components/common/States";
import { NotificationItem, announce, useOpenNotification } from "@/components/shell/NotificationBell";

const Pending = () => {
  const { data, error, reload } = useApi("/notifications/pending");
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Skeleton className="h-24" />;
  if (!data.items.length) return <p data-testid="pending-empty" className="text-sm text-slate-500">Nothing is waiting on you.</p>;
  return (
    <ul className="divide-y divide-border-subtle" data-testid="pending-actions-list">
      {data.items.map((i) => (
        <li key={i.key}>
          <Link to={i.link} data-testid={`pending-${i.key}`} className="focus-ring flex items-center gap-3 rounded-md px-1 py-2.5 hover:bg-slate-50">
            <span data-testid={`pending-${i.key}-count`} className="num flex h-7 min-w-[28px] items-center justify-center rounded-md bg-indigo-50 px-1.5 text-xs font-semibold text-indigo-700">{i.count}</span>
            <span className="flex-1 text-sm text-slate-700">{i.label}</span>
            <ChevronRight className="h-4 w-4 text-slate-300" />
          </Link>
        </li>
      ))}
    </ul>
  );
};

export default function Notifications() {
  const [status, setStatus] = useState("all");
  const { data, error, reload } = useApi("/notifications", { status });
  const open = useOpenNotification();
  const readAll = async () => { await api.post("/notifications/read-all"); announce(); reload(); };
  const onOpen = async (n) => { await open(n); if (!n.link) reload(); };

  return (
    <div data-testid="notifications-page" className="space-y-6 sm:space-y-8">
      <PageHeader eyebrow="Inbox" title="Notifications" description="Updates on lending, requests, handovers and sessions"
        actions={<Button variant="outline" data-testid="mark-all-read" disabled={!data?.unread} onClick={readAll}><CheckCheck className="mr-1.5 h-4 w-4" />Mark all as read</Button>} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
        <Panel testId="notifications-list-panel" title="All notifications" className="lg:col-span-8" bodyClassName="p-2 sm:p-3"
          action={<Tabs value={status} onValueChange={setStatus}><TabsList className="h-8">
            <TabsTrigger value="all" data-testid="notifications-filter-all" className="px-3 text-xs">All</TabsTrigger>
            <TabsTrigger value="unread" data-testid="notifications-filter-unread" className="px-3 text-xs">Unread{data ? ` (${data.unread})` : ""}</TabsTrigger>
          </TabsList></Tabs>}>
          {error ? <ErrorState message={error} onRetry={reload} /> : !data ? <div className="space-y-2 p-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-12" />)}</div>
            : data.items.length === 0 ? <EmptyState icon={Bell} title={status === "unread" ? "No unread notifications" : "No notifications yet"} description="Activity on your lending, requests, handovers and sessions shows up here." />
              : <div data-testid="notifications-list" className="space-y-0.5">{data.items.map((n) => <NotificationItem key={n.id} n={n} testId={`notification-${n.id}`} onOpen={onOpen} />)}</div>}
        </Panel>
        <Panel testId="pending-actions-panel" title="Pending actions" description="Items awaiting you" className="lg:col-span-4"
          action={<ListTodo className="h-4 w-4 text-slate-400" />}>
          <Pending />
        </Panel>
      </div>
    </div>
  );
}
