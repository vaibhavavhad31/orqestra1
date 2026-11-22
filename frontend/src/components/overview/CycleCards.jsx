import { Gauge, PiggyBank, Wallet, Zap } from "lucide-react";
import { StatCard } from "@/components/common/StatCard";
import { Meter } from "@/components/common/Meter";
import { fmt } from "@/lib/format";

export const CycleCards = ({ cycle, days, budgetLabel = "Budget", usedLabel = "Used", extra }) => {
  const over = cycle.remaining < 0;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard testId="stat-budget" label={budgetLabel} icon={Wallet} value={fmt(cycle.budget)}
        hint={days === 30 ? "Monthly allocation" : `Pro-rated for ${days} days`} />
      <StatCard testId="stat-used" label={usedLabel} icon={Zap} value={fmt(cycle.used)} hint={`Last ${days} days`} />
      <StatCard testId="stat-remaining" label={over ? "Over budget" : "Remaining"} icon={PiggyBank}
        value={fmt(Math.abs(cycle.remaining))} hint={over ? "Exceeded for this period" : "Available for this period"} />
      {extra || (
        <StatCard testId="stat-utilisation" label="Utilisation" icon={Gauge} value={`${cycle.utilisation}%`} unit="">
          <Meter value={cycle.utilisation} />
        </StatCard>
      )}
    </div>
  );
};
