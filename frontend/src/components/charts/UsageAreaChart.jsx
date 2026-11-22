import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
import { fmtCompact, fmtDay } from "@/lib/format";

const axis = { stroke: "#94A3B8", fontSize: 11, tickLine: false, axisLine: false };

export const UsageAreaChart = ({ data, series, height = 280, testId = "usage-area-chart", weekly = false }) => {
  const colors = Object.fromEntries(series.map((s) => [s.key, s.color]));
  const names = Object.fromEntries(series.map((s) => [s.key, s.name]));
  const interval = Math.max(0, Math.ceil(data.length / 7) - 1);
  return (
    <div data-testid={testId} data-granularity={weekly ? "week" : "day"} style={{ height }} className="w-full min-w-0 overflow-hidden">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 4, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="#EEF0F3" vertical={false} />
          <XAxis dataKey="date" tickFormatter={fmtDay} interval={interval} {...axis} dy={6} />
          <YAxis tickFormatter={fmtCompact} width={44} {...axis} />
          <Tooltip content={<ChartTooltip colors={colors} names={names} weekly={weekly} />} cursor={{ stroke: "#CBD5E1" }} />
          {series.map((s) => (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stackId={series.length > 1 ? "1" : undefined}
              stroke={s.color}
              strokeWidth={1.5}
              fill={s.color}
              fillOpacity={series.length > 1 ? 0.14 : 0.08}
              isAnimationActive={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
