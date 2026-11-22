import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { DashboardSkeleton, ErrorState } from "@/components/common/States";
import { AdminOverview } from "@/components/overview/AdminOverview";
import { ManagerOverview } from "@/components/overview/ManagerOverview";
import { PersonalOverview } from "@/components/overview/PersonalOverview";

const VIEWS = { admin: AdminOverview, manager: ManagerOverview, employee: PersonalOverview, individual: PersonalOverview };

export default function Overview() {
  const { user } = useAuth();
  const [days, setDays] = useState(30);
  const { data, loading, error, reload } = useApi("/overview", { days, uid: user.id });

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data || data.role !== user.role) return <DashboardSkeleton />;
  const View = VIEWS[data.role];
  return (
    <div data-testid={`overview-${data.role}`}>
      <View data={data} user={user} days={days} setDays={setDays} loading={loading} />
    </div>
  );
}
