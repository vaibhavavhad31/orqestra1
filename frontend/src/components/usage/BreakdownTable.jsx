import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fmt } from "@/lib/format";

export const BreakdownTable = ({ rows, label, testId, total }) => (
  <div className="overflow-x-auto" data-testid={testId}>
    <Table className="min-w-[520px]">
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead className="pl-5 text-xs">{label}</TableHead>
          <TableHead className="text-right text-xs">Credits</TableHead>
          <TableHead className="text-right text-xs">Requests</TableHead>
          <TableHead className="pr-5 text-right text-xs">Share</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.id} data-testid={`${testId}-row-${r.id}`}>
            <TableCell className="pl-5">
              <span className="flex items-center gap-2 whitespace-nowrap text-sm font-medium text-slate-900">
                {r.color && <span className="h-2.5 w-2.5 rounded-sm" style={{ background: r.color }} />}
                {r.name}
                {r.vendor && <span className="text-xs font-normal text-slate-400">{r.vendor}</span>}
              </span>
            </TableCell>
            <TableCell className="num text-right text-sm text-slate-900">{fmt(r.credits)}</TableCell>
            <TableCell className="num text-right text-sm text-slate-600">{fmt(r.requests)}</TableCell>
            <TableCell className="num pr-5 text-right text-sm text-slate-500">{total ? ((r.credits / total) * 100).toFixed(1) : "0.0"}%</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </div>
);
