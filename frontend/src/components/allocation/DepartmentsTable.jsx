import { Pencil } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Meter } from "@/components/common/Meter";
import { fmt } from "@/lib/format";

export const DepartmentsTable = ({ departments, onEdit }) => (
  <div className="overflow-x-auto" data-testid="departments-table">
    <Table className="min-w-[640px]">
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead className="pl-5 text-xs">Department</TableHead>
          <TableHead className="text-right text-xs">Budget / mo</TableHead>
          <TableHead className="text-right text-xs">Allocated</TableHead>
          <TableHead className="text-right text-xs">Unallocated</TableHead>
          <TableHead className="min-w-[140px] text-xs">Used (period)</TableHead>
          <TableHead className="pr-5 text-right text-xs"><span className="sr-only">Actions</span></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {departments.map((d) => (
          <TableRow key={d.id} data-testid={`department-row-${d.id}`}>
            <TableCell className="pl-5">
              <div className="text-sm font-medium text-slate-900">{d.name}</div>
              <div className="text-xs text-slate-500">{d.members} members</div>
            </TableCell>
            <TableCell data-testid={`department-row-${d.id}-budget`} className="num text-right text-sm text-slate-900">{fmt(d.budget)}</TableCell>
            <TableCell data-testid={`department-row-${d.id}-allocated`} className="num text-right text-sm text-slate-600">{fmt(d.allocated)}</TableCell>
            <TableCell data-testid={`department-row-${d.id}-unallocated`} className="num text-right text-sm text-slate-600">{fmt(d.unallocated)}</TableCell>
            <TableCell>
              <div className="flex items-center gap-2"><Meter value={d.utilisation} className="w-20" /><span className="num text-xs text-slate-600">{fmt(d.used)} · {d.utilisation}%</span></div>
            </TableCell>
            <TableCell className="pr-5 text-right">
              {onEdit && (
                <Button size="sm" variant="ghost" aria-label={`Edit ${d.name} budget`} data-testid={`edit-department-${d.id}`} onClick={() => onEdit(d)}>
                  <Pencil className="h-3.5 w-3.5" />
                </Button>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </div>
);
