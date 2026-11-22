import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
import { fmtCompact } from "@/lib/format";

const axis = { stroke: "#94A3B8", fontSize: 11, tickLine: false, axisLine: false };
const COLORS = { used: "#4F46E5", allocation: "#E0E7FF" };
const NAMES = { used: "Used", allocation: "Allocation" };

export const AllocationBars = ({ data, height = 280, testId = "allocation-bar-chart" }) => (
  <div data-testid={testId} style={{ height }} className="w-full min-w-0 overflow-hidden">
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 4, left: -12, bottom: 0 }} barGap={4} barCategoryGap="28%">
        <CartesianGrid stroke="#EEF0F3" vertical={false} />
        <XAxis dataKey="name" {...axis} dy={6} interval={0} tickFormatter={(v) => v.split(" ")[0]} />
        <YAxis tickFormatter={fmtCompact} width={44} {...axis} />
        <Tooltip content={<ChartTooltip colors={COLORS} names={NAMES} />} cursor={{ fill: "#F6F7F9" }} />
        <Bar dataKey="allocation" fill={COLORS.allocation} radius={[3, 3, 0, 0]} isAnimationActive={false} />
        <Bar dataKey="used" fill={COLORS.used} radius={[3, 3, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  </div>
);

export const ChartLegend = ({ items }) => (
  <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
    {items.map((i) => (
      <span key={i.name} className="flex items-center gap-1.5 text-xs text-slate-500">
        <span className="h-2 w-2 rounded-sm" style={{ background: i.color }} />
        {i.name}
      </span>
    ))}
  </div>
);

export const ALLOCATION_LEGEND = [
  { name: "Allocation", color: COLORS.allocation },
  { name: "Used", color: COLORS.used },
];
