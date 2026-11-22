import { Link } from "react-router-dom";
import { ArrowDownLeft, ArrowUpRight, Clock, Info, Scale, Activity, Wallet } from "lucide-react";
import { Panel } from "@/components/common/Layout";
import { EmptyState } from "@/components/common/States";
import { UsageAreaChart } from "@/components/charts/UsageAreaChart";
import { ProviderBreakdown } from "@/components/charts/ProviderBreakdown";
import { CycleCards } from "@/components/overview/CycleCards";
import { DashHeader } from "@/components/overview/DashHeader";
import { StatCard } from "@/components/common/StatCard";
import { fmt } from "@/lib/format";

const TREND = [{ key: "credits", name: "Credits", color: "#4F46E5" }];

const LendingSummary = ({ lending }) => (
  <Panel testId="lending-summary-panel" title="Lending summary" description="Obligations with friends"
    action={<Link to="/lending" data-testid="lending-link" className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700">Credit Lending <ArrowUpRight className="h-3 w-3" /></Link>}>
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
      {[
        ["Available now", lending.available, Wallet, "available"],
        ["Lent outstanding", lending.lent_outstanding, ArrowUpRight, "lent"],
        ["Borrowed outstanding", lending.borrowed_outstanding, ArrowDownLeft, "borrowed"],
        ["Net position", lending.net, Scale, "net"],
        ["Pending actions", lending.pending_actions, Clock, "pending"],
      ].map(([label, value, Icon, id]) => (
        <div key={id} data-testid={`lending-${id}`} className="rounded-md border border-border-subtle bg-slate-50/60 p-3.5">
          <div className="flex items-center gap-1.5 text-xs text-slate-500"><Icon className="h-3.5 w-3.5" />{label}</div>
          <div className="num mt-1.5 text-lg font-semibold text-slate-900">{id === "net" && value > 0 ? "+" : ""}{fmt(value)}</div>
        </div>
      ))}
    </div>
    <p data-testid="lending-disclaimer" className="mt-4 flex items-center gap-1.5 text-xs text-slate-500">
      <Info className="h-3.5 w-3.5 shrink-0" /> {lending.simulated_disclaimer}
    </p>
  </Panel>
);

export const PersonalOverview = ({ data, user, days, setDays, loading }) => {
  const top = data.providers.find((p) => p.id === data.top_provider);
  const eyebrow = user.mode === "organisation" ? `${user.organization?.name} · ${user.department?.name || ""}` : "Personal workspace";
  return (
    <div className="space-y-6 sm:space-y-8">
      <DashHeader eyebrow={eyebrow} title={`Hello, ${user.name.split(" ")[0]}`} data={data} days={days} setDays={setDays} loading={loading} />
      <CycleCards cycle={data.cycle} days={days} budgetLabel={user.role === "individual" ? "Personal credits" : "Your allocation"}
        usedLabel="Credits used"
        extra={<StatCard testId="stat-top-provider" label="Top provider" icon={Activity} unit="" value={top?.name || "—"} hint={top && top.credits ? `${fmt(top.credits)} credits · ${top.share}% of usage` : "No usage in this period"} />} />
      {data.lending && <LendingSummary lending={data.lending} />}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Panel testId="personal-trend-panel" title={data.granularity === "week" ? "Your weekly usage" : "Your daily usage"}
          description={`Credits per ${data.granularity}, simulated`} className="lg:col-span-8">
          {data.totals.credits ? <UsageAreaChart data={data.trend} series={TREND} height={240} testId="personal-trend-chart" weekly={data.granularity === "week"} />
            : <EmptyState title="No usage yet" description="Once you start using AI providers, your daily credit usage will appear here." />}
        </Panel>
        <Panel testId="personal-provider-panel" title="By provider" className="lg:col-span-4">
          {data.totals.credits ? <ProviderBreakdown providers={data.providers} /> : <EmptyState title="No provider usage" description="Nothing recorded in this period." />}
        </Panel>
      </div>
    </div>
  );
};
