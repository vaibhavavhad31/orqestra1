import { fmt, fmtDay } from "@/lib/format";

const formatLabel = (label, weekly) => {
  if (!/^\d{4}-/.test(label)) return label;
  return weekly ? `Week of ${fmtDay(label)}` : fmtDay(label);
};

export const ChartTooltip = ({ active, payload, label, colors = {}, names = {}, weekly }) => {
  if (!active || !payload?.length) return null;
  const items = payload.filter((p) => p.value > 0 || payload.length === 1);
  const total = items.reduce((s, p) => s + (p.value || 0), 0);
  return (
    <div className="min-w-[160px] rounded-md border border-border bg-white px-3 py-2 text-xs shadow-md">
      {label && <div className="mb-1.5 font-medium text-slate-900">{formatLabel(label, weekly)}</div>}
      <div className="space-y-1">
        {items.map((p) => (
          <div key={p.dataKey} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-slate-600">
              <span className="h-2 w-2 rounded-sm" style={{ background: colors[p.dataKey] || p.color || p.fill }} />
              {names[p.dataKey] || p.name}
            </span>
            <span className="num text-slate-900">{fmt(p.value)}</span>
          </div>
        ))}
      </div>
      {items.length > 1 && (
        <div className="mt-1.5 flex justify-between border-t border-border-subtle pt-1.5 text-slate-500">
          <span>Total</span><span className="num text-slate-900">{fmt(total)}</span>
        </div>
      )}
    </div>
  );
};
