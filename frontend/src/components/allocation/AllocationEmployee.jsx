import { useState } from "react";
import { Gauge, PiggyBank, Plus, Wallet, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/common/Layout";
import { StatCard } from "@/components/common/StatCard";
import { StatusPill } from "@/components/common/StatusPill";
import { Meter } from "@/components/common/Meter";
import { RequestsList } from "@/components/allocation/RequestsList";
import { RequestDialog } from "@/components/allocation/RequestDialogs";
import { fmt, HEALTH } from "@/lib/format";

export const AllocationEmployee = ({ data, reload }) => {
  const [open, setOpen] = useState(false);
  const me = data.me;
  return (
    <div className="space-y-6 sm:space-y-8" data-testid="allocation-employee">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard testId="my-allocation" label="Your allocation" icon={Wallet} value={fmt(me.allocation)} hint={`${fmt(me.monthly_allocation)} / month`} />
        <StatCard testId="my-used" label="Used" icon={Zap} value={fmt(me.credits)} hint={`Last ${data.days} days`} />
        <StatCard testId="my-remaining" label="Remaining" icon={PiggyBank} value={fmt(me.remaining)} hint="For this period" />
        <StatCard testId="my-utilisation" label="Utilisation" icon={Gauge} unit="" value={`${me.utilisation}%`}>
          <div className="flex items-center gap-2"><Meter value={me.utilisation} /><StatusPill tone={HEALTH[me.health].tone} testId="my-health">{HEALTH[me.health].label}</StatusPill></div>
        </StatCard>
      </div>
      <Panel testId="my-requests-panel" title="Your resource requests" description="Ask for more credits when your allocation isn't enough"
        action={<Button size="sm" data-testid="open-resource-request" onClick={() => setOpen(true)}><Plus className="mr-1.5 h-3.5 w-3.5" />Request credits</Button>}
        bodyClassName="p-0">
        <RequestsList requests={data.requests} canDecide={false} onChanged={reload} />
      </Panel>
      <RequestDialog open={open} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); reload(); }} />
    </div>
  );
};
