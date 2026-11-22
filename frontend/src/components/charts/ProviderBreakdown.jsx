import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
import { fmt } from "@/lib/format";

export const ProviderBreakdown = ({ providers, testId = "provider-breakdown" }) => {
  const data = providers.filter((p) => p.credits > 0);
  const total = data.reduce((s, p) => s + p.credits, 0);
  return (
    <div data-testid={testId} className="flex flex-col gap-5">
      <div className="relative mx-auto h-[150px] w-[150px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="credits" nameKey="name" innerRadius={52} outerRadius={72} paddingAngle={2} stroke="none" isAnimationActive={false}>
              {data.map((p) => <Cell key={p.id} fill={p.color} />)}
            </Pie>
            <Tooltip content={<ChartTooltip />} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="num text-lg font-semibold text-slate-900">{fmt(total)}</span>
          <span className="text-[11px] text-slate-500">credits</span>
        </div>
      </div>
      <ul className="space-y-2.5">
        {providers.map((p) => (
          <li key={p.id} data-testid={`provider-row-${p.id}`} className="flex items-center gap-3 text-sm">
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: p.color }} />
            <span className="flex-1 truncate text-slate-700">{p.name}</span>
            <span className="num text-slate-900">{fmt(p.credits)}</span>
            <span className="num w-12 text-right text-xs text-slate-500">{p.share}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
};
