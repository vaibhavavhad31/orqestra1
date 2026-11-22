import { useSearchParams } from "react-router-dom";
import { useCallback, useState } from "react";
import { HandCoins, Send } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel } from "@/components/common/Layout";
import { SimulatedBadge } from "@/components/common/SimulatedBadge";
import { DashboardSkeleton, ErrorState } from "@/components/common/States";
import { LendingDisclaimer } from "@/components/lending/LendingDisclaimer";
import { LendingSummaryCards } from "@/components/lending/LendingSummaryCards";
import { EntryList } from "@/components/lending/EntryList";
import { FriendsPanel } from "@/components/lending/FriendsPanel";
import { NewEntryDialog } from "@/components/lending/NewEntryDialog";
import { EntrySheet } from "@/components/lending/EntrySheet";

export default function CreditLending() {
  const [tab, setTab] = useState("all");
  const [dialog, setDialog] = useState(null);
  const [params] = useSearchParams();
  const [openId, setOpenId] = useState(params.get("open"));
  const summary = useApi("/lending/summary");
  const entries = useApi("/lending/entries", { tab });
  const friends = useApi("/friends");
  const { reload: r1 } = summary;
  const { reload: r2 } = entries;
  const { reload: r3 } = friends;
  const refresh = useCallback(() => { r1(); r2(); r3(); }, [r1, r2, r3]);

  const error = summary.error || friends.error;
  if (error) return <ErrorState message={error} onRetry={refresh} />;
  if (!summary.data || !friends.data) return <DashboardSkeleton />;

  return (
    <div data-testid="credit-lending-page" className="space-y-6 sm:space-y-8">
      <PageHeader eyebrow="Personal workspace" title="Credit Lending" description="Lend to and borrow from friends, tracked as obligations"
        actions={<>
          <SimulatedBadge label="Simulated · obligations only" />
          <Button variant="outline" data-testid="open-request-dialog" onClick={() => setDialog("request")}><HandCoins className="mr-1.5 h-4 w-4" />Request credits</Button>
          <Button data-testid="open-lend-dialog" onClick={() => setDialog("offer")}><Send className="mr-1.5 h-4 w-4" />Lend credits</Button>
        </>} />
      <LendingDisclaimer testId="lending-page-disclaimer" />
      <LendingSummaryCards s={summary.data} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
        <Panel testId="lending-entries-panel" title="Lending entries" description="Tap an entry for details, actions and history" className="lg:col-span-8" bodyClassName="p-0">
          <EntryList tab={tab} setTab={setTab} entries={entries.data?.entries ?? null} onOpen={setOpenId} />
        </Panel>
        <Panel testId="friends-panel-wrapper" title="Friends" description="Only friends can lend to each other" className="lg:col-span-4">
          <FriendsPanel data={friends.data} onChange={refresh} />
        </Panel>
      </div>
      <NewEntryDialog mode={dialog} onClose={() => setDialog(null)} friends={friends.data.friends}
        onCreated={(e) => { setDialog(null); refresh(); setOpenId(e.id); }} />
      <EntrySheet entryId={openId} onClose={() => setOpenId(null)} onChanged={refresh} />
    </div>
  );
}
