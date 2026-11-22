import { Link } from "react-router-dom";
import { AlertTriangle, ArrowUpRight, BarChart3 } from "lucide-react";
import { Panel } from "@/components/common/Layout";
import { EmptyState } from "@/components/common/States";
import { StatusPill } from "@/components/common/StatusPill";
import { Meter } from "@/components/common/Meter";
import { AllocationBars, ChartLegend, ALLOCATION_LEGEND } from "@/components/charts/AllocationBars";
import { UsageAreaChart } from "@/components/charts/UsageAreaChart";
import { ProviderBreakdown } from "@/components/charts/ProviderBreakdown";
import { CycleCards } from "@/components/overview/CycleCards";
import { DashHeader } from "@/components/overview/DashHeader";
import { fmt, HEALTH } from "@/lib/format";

const TREND = [{ key: "credits", name: "Credits", color: "#4F46E5" }];

const Attention = ({ health }) => (
  <Panel testId="allocation-health-panel" title="Allocation health" description="People near their limit or underusing credits" className="lg:col-span-4" bodyClassName="p-0">
    <div className="grid grid-cols-2 border-b border-border-subtle">
      <div className="px-5 py-3"><div className="eyebrow">Near limit</div><div data-testid="near-limit-count" className="num mt-1 text-xl font-semibold text-amber-600">{health.near_limit}</div></div>
      <div className="border-l border-border-subtle px-5 py-3"><div className="eyebrow">Underutilised</div><div data-testid="underutilised-count" className="num mt-1 text-xl font-semibold text-sky-600">{health.underutilised}</div></div>
    </div>
    {health.attention.length === 0 ? (
      <div className="p-5"><EmptyState icon={AlertTriangle} title="Everything looks balanced" description="No one is near their limit or underusing credits." /></div>
    ) : (
      <ul className="divide-y divide-border-subtle">
        {health.attention.slice(0, 6).map((m) => (
          <li key={m.id} data-testid={`attention-row-${m.id}`} className="px-5 py-3">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-slate-900">{m.name}</div>
                <div className="truncate text-xs text-slate-500">{m.department} · {fmt(m.credits)} / {fmt(m.allocation)}</div>
              </div>
              <StatusPill tone={HEALTH[m.health].tone}>{m.utilisation}%</StatusPill>
            </div>
            <Meter value={m.utilisation} className="mt-2" />
          </li>
        ))}
      </ul>
    )}
  </Panel>
);

export const AdminOverview = ({ data, days, setDays, loading }) => {
  const org = data.organization;
  const deptData = data.departments.map((d) => ({ name: d.name, used: d.used, allocation: d.allocation }));
  return (
    <div className="space-y-6 sm:space-y-8">
      <DashHeader eyebrow={`Organisation · ${org.employees} people · ${org.departments} departments`} title={org.name} data={data} days={days} setDays={setDays} loading={loading} />
      <CycleCards cycle={data.cycle} days={days} budgetLabel="Org budget" usedLabel="Org spend" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
        <Panel testId="spend-by-department-panel" title="Spend by department" description="Used vs allocation for the selected period" className="lg:col-span-8"
          action={<ChartLegend items={ALLOCATION_LEGEND} />}>
          {deptData.length ? <AllocationBars data={deptData} /> : <EmptyState icon={BarChart3} title="No departments yet" description="Departments appear here once they are created." />}
        </Panel>
        <Attention health={data.health} />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Panel testId="org-trend-panel" title={data.granularity === "week" ? "Weekly spend" : "Daily spend"} description="All departments, simulated" className="lg:col-span-8"
          action={<Link to="/usage" data-testid="view-usage-link" className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700">AI Usage <ArrowUpRight className="h-3 w-3" /></Link>}>
          {data.totals.credits ? <UsageAreaChart data={data.trend} series={TREND} height={240} testId="org-trend-chart" weekly={data.granularity === "week"} /> : <EmptyState title="No usage yet" description="Usage appears once your team starts consuming credits." />}
        </Panel>
        <Panel testId="org-provider-panel" title="By provider" className="lg:col-span-4">
          {data.totals.credits ? <ProviderBreakdown providers={data.providers} /> : <EmptyState title="No provider usage" />}
        </Panel>
      </div>
    </div>
  );
};
