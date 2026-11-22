import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusPill } from "@/components/common/StatusPill";
import { fmt, HEALTH } from "@/lib/format";

export const num = (key) => ({ key, align: "right", render: (r) => fmt(r[key]) });
export const pct = (key) => ({ key, align: "right", render: (r) => `${r[key]}%` });
export const health = (key = "status") => ({ key, render: (r) => <StatusPill tone={HEALTH[r[key]]?.tone}>{HEALTH[r[key]]?.label || r[key]}</StatusPill> });

export const DataTable = ({ columns, rows, testId, rowKey = (r, i) => r.id || i }) => (
  <div className="overflow-x-auto" data-testid={testId}>
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          {columns.map((c, i) => <TableHead key={c.key + i} className={`whitespace-nowrap text-xs ${c.align === "right" ? "text-right" : ""} ${i === 0 ? "pl-5" : ""}`}>{c.label}</TableHead>)}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r, ri) => (
          <TableRow key={rowKey(r, ri)} data-testid={`${testId}-row-${ri}`}>
            {columns.map((c, i) => (
              <TableCell key={c.key + i} className={`whitespace-nowrap text-sm ${c.align === "right" ? "num text-right" : ""} ${i === 0 ? "pl-5 font-medium text-slate-900" : "text-slate-600"}`}>
                {c.render ? c.render(r) : r[c.key] ?? "—"}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </div>
);
