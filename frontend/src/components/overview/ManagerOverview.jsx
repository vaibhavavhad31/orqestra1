import { Users } from "lucide-react";
import { Panel } from "@/components/common/Layout";
import { EmptyState } from "@/components/common/States";
import { AllocationBars, ChartLegend, ALLOCATION_LEGEND } from "@/components/charts/AllocationBars";
import { ProviderBreakdown } from "@/components/charts/ProviderBreakdown";
import { MembersTable } from "@/components/usage/MembersTable";
import { CycleCards } from "@/components/overview/CycleCards";
import { DashHeader } from "@/components/overview/DashHeader";

export const ManagerOverview = ({ data, days, setDays, loading }) => {
  const dept = data.department;
  const bars = data.members.map((m) => ({ name: m.name, used: m.credits, allocation: m.allocation }));
  return (
    <div className="space-y-6 sm:space-y-8">
      <DashHeader eyebrow={`Team · ${dept.members} people`} title={`${dept.name} team`} data={data} days={days} setDays={setDays} loading={loading} />
      <CycleCards cycle={data.cycle} days={days} budgetLabel="Team allocation" usedLabel="Team usage" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Panel testId="team-usage-panel" title="Team usage" description="Used vs allocation per person" className="lg:col-span-8" action={<ChartLegend items={ALLOCATION_LEGEND} />}>
          {bars.length ? <AllocationBars data={bars} testId="team-usage-chart" /> : <EmptyState icon={Users} title="No team members yet" />}
        </Panel>
        <Panel testId="team-provider-panel" title="By provider" className="lg:col-span-4">
          {data.totals.credits ? <ProviderBreakdown providers={data.providers} /> : <EmptyState title="No provider usage" />}
        </Panel>
      </div>
      <Panel testId="team-members-panel" title="Team members" description="Allocation and utilisation for the selected period" bodyClassName="p-0">
        <MembersTable members={data.members} showAllocation />
      </Panel>
    </div>
  );
};
