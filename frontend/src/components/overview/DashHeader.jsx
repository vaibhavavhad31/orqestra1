import { SimulatedBadge } from "@/components/common/SimulatedBadge";
import { RangeFilter } from "@/components/common/RangeFilter";
import { PageHeader } from "@/components/common/Layout";
import { fmtRange } from "@/lib/format";

export const DashHeader = ({ eyebrow, title, data, days, setDays, loading }) => (
  <PageHeader
    eyebrow={eyebrow}
    title={title}
    description={`${fmtRange(data.start, data.end)} · figures in credits`}
    actions={<><SimulatedBadge /><RangeFilter value={days} onChange={setDays} loading={loading} /></>}
  />
);
