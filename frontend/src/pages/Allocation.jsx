import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { PageHeader } from "@/components/common/Layout";
import { SimulatedBadge } from "@/components/common/SimulatedBadge";
import { RangeFilter } from "@/components/common/RangeFilter";
import { DashboardSkeleton, ErrorState } from "@/components/common/States";
import { AllocationManage } from "@/components/allocation/AllocationManage";
import { AllocationEmployee } from "@/components/allocation/AllocationEmployee";

const EYEBROW = { admin: "Scope · Organisation", manager: "Scope · Your department", employee: "Scope · Only you" };

export default function Allocation() {
  const { user } = useAuth();
  const [days, setDays] = useState(30);
  const { data, loading, error, reload } = useApi("/allocation", { days });

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <DashboardSkeleton />;
  const subtitle = user.role === "employee" ? "Your allocation, usage and requests"
    : user.role === "manager" ? `${user.department?.name} allocations and requests` : `${user.organization?.name} budgets, allocations and requests`;
  return (
    <div data-testid={`allocation-page-${data.role}`} className="space-y-6 sm:space-y-8">
      <PageHeader eyebrow={EYEBROW[data.role]} title="Resource Allocation" description={subtitle}
        actions={<><SimulatedBadge /><RangeFilter value={days} onChange={setDays} loading={loading} /></>} />
      {data.role === "employee" ? <AllocationEmployee data={data} reload={reload} /> : <AllocationManage data={data} reload={reload} />}
    </div>
  );
}
