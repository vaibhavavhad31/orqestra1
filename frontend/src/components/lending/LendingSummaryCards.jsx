import { ArrowDownLeft, ArrowUpRight, BellDot, Scale, Wallet } from "lucide-react";
import { StatCard } from "@/components/common/StatCard";
import { fmt } from "@/lib/format";

export const LendingSummaryCards = ({ s }) => (
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
    <StatCard testId="lending-available" label="Available" icon={Wallet} value={fmt(s.available)}
      hint={`${fmt(s.capacity)} capacity − ${fmt(s.used)} used (30d) − lent + borrowed`} className="sm:col-span-2 lg:col-span-1" />
    <StatCard testId="lending-lent" label="Lent outstanding" icon={ArrowUpRight} value={fmt(s.lent_outstanding)} hint="Owed to you" />
    <StatCard testId="lending-borrowed" label="Borrowed outstanding" icon={ArrowDownLeft} value={fmt(s.borrowed_outstanding)} hint="You owe" />
    <StatCard testId="lending-net" label="Net position" icon={Scale} value={`${s.net > 0 ? "+" : ""}${fmt(s.net)}`} hint={`${s.active_loans} active · ${s.overdue} overdue`} />
    <StatCard testId="lending-pending-actions" label="Pending actions" icon={BellDot} unit="" value={fmt(s.pending_actions)} hint="Waiting on you" />
  </div>
);
