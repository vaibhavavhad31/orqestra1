import { useState } from "react";
import { Activity, ArrowDownRight, ArrowUpRight, Hash, Minus, Sparkles, TrendingUp } from "lucide-react";
import { UsageFilters } from "@/components/usage/UsageFilters";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { DashboardSkeleton, EmptyState, ErrorState } from "@/components/common/States";
import { PageHeader, Panel } from "@/components/common/Layout";
import { SimulatedBadge } from "@/components/common/SimulatedBadge";
import { RangeFilter } from "@/components/common/RangeFilter";
import { StatCard } from "@/components/common/StatCard";
import { UsageAreaChart } from "@/components/charts/UsageAreaChart";
import { ProviderBreakdown } from "@/components/charts/ProviderBreakdown";
import { ChartLegend } from "@/components/charts/AllocationBars";
import { MembersTable } from "@/components/usage/MembersTable";
import { BreakdownTable } from "@/components/usage/BreakdownTable";
import { fmt, fmtRange } from "@/lib/format";

const SCOPE_EYEBROW = { organisation: "Scope · Organisation", department: "Scope · Your department", self: "Scope · Only you" };

const ChangeCard = ({ totals, days }) => {
  const pct = totals.change_pct;
  const Icon = pct == null ? Minus : pct >= 0 ? ArrowUpRight : ArrowDownRight;
  const value = pct == null ? "—" : `${pct > 0 ? "+" : ""}${pct}%`;
  return (
    <StatCard testId="usage-change" label="vs previous period" icon={Icon} unit="" value={value} className="sm:col-span-2 lg:col-span-1"
      hint={pct == null ? `No usage in the prior ${days} days` : `${fmt(totals.previous_credits)} credits in the prior ${days} days`} />
  );
};

const Totals = ({ data }) => {
  const top = [...data.providers].sort((a, b) => b.credits - a.credits)[0];
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <StatCard testId="usage-total-credits" label="Credits used" icon={Activity} value={fmt(data.totals.credits)} hint={`Last ${data.days} days`} />
      <StatCard testId="usage-total-requests" label="Requests" icon={Hash} unit="" value={fmt(data.totals.requests)} hint="Simulated request count" />
      <StatCard testId="usage-avg-day" label="Average per day" icon={TrendingUp} value={fmt(data.totals.avg_per_day)} hint={`${data.totals.active_days} active days`} />
      <StatCard testId="usage-top-provider" label="Top provider" icon={Sparkles} unit="" value={data.totals.credits ? top.name : "—"}
        hint={data.totals.credits ? `${top.share}% of credits` : "No usage in this period"} />
      <ChangeCard totals={data.totals} days={data.days} />
    </div>
  );
};

const UsageBody = ({ data }) => {
  const series = data.providers.map((p) => ({ key: p.id, name: p.name, color: p.color }));
  const weekly = data.granularity === "week";
  if (!data.totals.credits) {
    return <EmptyState icon={Activity} title="No usage in this period" description="Simulated usage appears here as credits are consumed. Try a longer range or clear the filters." />;
  }
  return (
    <>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Panel testId="usage-over-time-panel" title="Usage over time" description={weekly ? "Weekly credits, stacked by provider" : "Daily credits, stacked by provider"}
          className="lg:col-span-8" action={<div className="hidden sm:block"><ChartLegend items={series} /></div>}>
          <UsageAreaChart data={data.timeseries} series={series} height={300} weekly={weekly} />
        </Panel>
        <Panel testId="usage-by-provider-panel" title="By provider" className="lg:col-span-4">
          <ProviderBreakdown providers={data.providers} />
        </Panel>
      </div>
      <Panel testId="provider-table-panel" title="Provider breakdown" description="From the provider registry. All providers are simulated, not connected." bodyClassName="p-0">
        <BreakdownTable rows={data.providers} label="Provider" testId="provider-table" total={data.totals.credits} />
      </Panel>
      {data.departments && (
        <Panel testId="department-table-panel" title="By department" bodyClassName="p-0">
          <BreakdownTable rows={data.departments} label="Department" testId="department-table" total={data.totals.credits} />
        </Panel>
      )}
      {data.members && (
        <Panel testId="member-table-panel" title={data.scope.type === "organisation" ? "By member" : "By team member"} bodyClassName="p-0">
          <MembersTable members={data.members} showDepartment={data.scope.type === "organisation"} providers={data.providers} />
        </Panel>
      )}
    </>
  );
};

export default function Usage() {
  const { user } = useAuth();
  const [days, setDays] = useState(30);
  const [filters, setFilters] = useState({});
  const { data, loading, error, reload } = useApi("/usage", { days, uid: user.id, ...filters });

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <DashboardSkeleton />;
  return (
    <div data-testid="usage-page" className="space-y-6 sm:space-y-8">
      <PageHeader
        eyebrow={SCOPE_EYEBROW[data.scope.type]}
        title="AI Usage"
        description={<><span data-testid="usage-scope-label">{data.scope.label}</span> · {fmtRange(data.start, data.end)}</>}
        actions={<><SimulatedBadge /><RangeFilter value={days} onChange={setDays} loading={loading} /></>}
      />
      <UsageFilters filters={filters} setFilters={setFilters} providers={data.providers} options={data.filter_options} scopeType={data.scope.type} />
      <Totals data={data} />
      <UsageBody data={data} />
    </div>
  );
}
