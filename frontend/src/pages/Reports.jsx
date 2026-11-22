import { useState } from "react";
import { Activity, Download, FileBarChart, Hash, TrendingUp, Wallet } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader, Panel } from "@/components/common/Layout";
import { DashboardSkeleton, EmptyState, ErrorState } from "@/components/common/States";
import { SimulatedBadge } from "@/components/common/SimulatedBadge";
import { RangeFilter } from "@/components/common/RangeFilter";
import { StatCard } from "@/components/common/StatCard";
import { DataTable, health, num, pct } from "@/components/common/DataTable";
import { UsageAreaChart } from "@/components/charts/UsageAreaChart";
import { ProviderBreakdown } from "@/components/charts/ProviderBreakdown";
import { fmt, fmtDay, fmtRange } from "@/lib/format";

const exportCsv = async (kind, days, setBusy) => {
  setBusy(true);
  try {
    const res = await api.get(`/reports/${kind}/csv`, { params: { days }, responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = Object.assign(document.createElement("a"), { href: url, download: `${kind}-report-${days}d.csv` });
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    toast.success("CSV downloaded");
  } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
};

const UsageReport = ({ d }) => {
  const series = d.providers.map((p) => ({ key: p.id, name: p.name, color: p.color }));
  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard testId="report-total-credits" label="Credits used" icon={Activity} value={fmt(d.totals.credits)} hint={fmtRange(d.start, d.end)} />
        <StatCard testId="report-total-requests" label="Requests" icon={Hash} unit="" value={fmt(d.totals.requests)} hint="Simulated request count" />
        <StatCard testId="report-avg-day" label="Average per day" icon={TrendingUp} value={fmt(d.totals.avg_per_day)} hint={`${d.totals.active_days} active days`} />
      </div>
      {!d.totals.credits ? <EmptyState icon={FileBarChart} title="No usage in this period" description="Try a longer range." /> : <>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <Panel testId="report-trend-panel" title="Usage over time" className="lg:col-span-8"><UsageAreaChart data={d.timeseries} series={series} height={260} weekly={d.granularity === "week"} /></Panel>
          <Panel testId="report-provider-panel" title="By provider" className="lg:col-span-4"><ProviderBreakdown providers={d.providers} /></Panel>
        </div>
        {d.departments && <Panel title="By department" bodyClassName="p-0"><DataTable testId="report-departments-table" rows={d.departments}
          columns={[{ key: "name", label: "Department" }, { ...num("credits"), label: "Credits" }, { ...num("requests"), label: "Requests" }]} /></Panel>}
        {d.members && <Panel title="By member" bodyClassName="p-0"><DataTable testId="report-members-table" rows={d.members}
          columns={[{ key: "name", label: "Member" }, { key: "department", label: "Department" }, { ...num("credits"), label: "Credits" }, { ...num("requests"), label: "Requests" }]} /></Panel>}
        <Panel title="Daily totals" bodyClassName="p-0 max-h-[360px] overflow-y-auto"><DataTable testId="report-daily-table" rows={[...d.daily].reverse()} rowKey={(r) => r.date}
          columns={[{ key: "date", label: "Date", render: (r) => fmtDay(r.date) }, { ...num("credits"), label: "Credits" }]} /></Panel>
      </>}
    </>
  );
};

const AllocationReport = ({ d }) => (
  <Panel title="Budget and utilisation" description={`Budgets are prorated to ${d.days} days`} bodyClassName="p-0">
    <DataTable testId="report-allocation-table" rows={d.rows} rowKey={(r, i) => `${r.level}-${r.name}-${i}`} columns={[
      { key: "name", label: "Name" }, { key: "level", label: "Level" }, { ...num("budget"), label: "Budget" }, { ...num("allocated"), label: "Allocated" },
      { ...num("used"), label: "Used" }, { ...num("remaining"), label: "Remaining" }, { ...pct("utilisation"), label: "Utilisation" }, { ...health(), label: "Status" }]} />
  </Panel>
);

const LendingReport = ({ d }) => (
  <>
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard testId="report-personal-used" label="Credits used" icon={Activity} value={fmt(d.totals.credits)} hint={fmtRange(d.start, d.end)} />
      <StatCard testId="report-personal-remaining" label="Remaining" icon={Wallet} value={fmt(d.cycle.remaining)} hint={`of ${fmt(d.cycle.budget)} prorated budget`} />
      <StatCard testId="report-lent" label="Lent outstanding" icon={TrendingUp} value={fmt(d.summary.lent_outstanding)} hint={`${d.summary.active_loans} active loans`} />
      <StatCard testId="report-borrowed" label="Borrowed outstanding" icon={TrendingUp} value={fmt(d.summary.borrowed_outstanding)} hint={`${d.summary.overdue} overdue`} />
    </div>
    <p className="text-xs text-slate-500">{d.summary.simulated_disclaimer}</p>
    <Panel title="Lending entries" bodyClassName="p-0">
      {d.entries.length ? <DataTable testId="report-lending-table" rows={d.entries} columns={[
        { key: "counterparty", label: "With" }, { key: "direction", label: "Direction" }, { ...num("credits"), label: "Credits" }, { ...num("repaid"), label: "Repaid" },
        { ...num("outstanding"), label: "Outstanding" }, { key: "status", label: "Status" }, { key: "due_date", label: "Due" }]} />
        : <div className="p-5"><EmptyState title="No lending entries" description="Entries with friends appear here." /></div>}
    </Panel>
  </>
);

export default function Reports() {
  const { user } = useAuth();
  const second = user.role === "individual" ? "lending" : "allocation";
  const [kind, setKind] = useState("usage");
  const [days, setDays] = useState(30);
  const [busy, setBusy] = useState(false);
  const { data, error, loading, reload } = useApi(`/reports/${kind}`, { days });
  const ready = data && data.kind === kind && data.days === days;
  return (
    <div data-testid="reports-page" className="space-y-6 sm:space-y-8">
      <PageHeader eyebrow={data?.scope ? `Scope · ${data.scope.label}` : "Reports"} title="Reports" description="Usage, allocation and lending in credits"
        actions={<><SimulatedBadge testId="reports-simulated-badge" />
          <Button variant="outline" data-testid="export-csv" disabled={busy || !ready} onClick={() => exportCsv(kind, days, setBusy)}><Download className="mr-1.5 h-4 w-4" />{busy ? "Exporting…" : "Export CSV"}</Button></>} />
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={kind} onValueChange={setKind}><TabsList className="h-9">
          <TabsTrigger value="usage" data-testid="report-tab-usage" className="px-3 text-xs">Usage</TabsTrigger>
          <TabsTrigger value={second} data-testid={`report-tab-${second}`} className="px-3 text-xs">{second === "lending" ? "Lending summary" : "Allocation"}</TabsTrigger>
        </TabsList></Tabs>
        <RangeFilter value={days} onChange={setDays} loading={loading} />
      </div>
      {error ? <ErrorState message={error} onRetry={reload} /> : !ready ? <DashboardSkeleton />
        : kind === "usage" ? <UsageReport d={data} /> : kind === "allocation" ? <AllocationReport d={data} /> : <LendingReport d={data} />}
    </div>
  );
}
