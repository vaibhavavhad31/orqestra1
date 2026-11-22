import { Pencil, Users } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { StatusPill } from "@/components/common/StatusPill";
import { Meter } from "@/components/common/Meter";
import { EmptyState } from "@/components/common/States";
import { fmt, HEALTH } from "@/lib/format";

export const AllocationMembersTable = ({ members, showDepartment, onEdit }) => {
  if (!members.length) return <div className="p-5"><EmptyState icon={Users} title="No members" description="No one is in this scope yet." /></div>;
  return (
    <div className="overflow-x-auto" data-testid="allocation-members-table">
      <Table className="min-w-[760px]">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-5 text-xs">Member</TableHead>
            {showDepartment && <TableHead className="text-xs">Department</TableHead>}
            <TableHead className="text-right text-xs">Allocation</TableHead>
            <TableHead className="text-right text-xs">Used</TableHead>
            <TableHead className="text-right text-xs">Remaining</TableHead>
            <TableHead className="min-w-[140px] text-xs">Utilisation</TableHead>
            <TableHead className="text-xs">Status</TableHead>
            <TableHead className="pr-5 text-right text-xs"><span className="sr-only">Actions</span></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {members.map((m) => (
            <TableRow key={m.id} data-testid={`allocation-row-${m.id}`}>
              <TableCell className="pl-5">
                <div className="whitespace-nowrap text-sm font-medium text-slate-900">{m.name}</div>
                <div className="whitespace-nowrap text-xs text-slate-500">{m.title}</div>
              </TableCell>
              {showDepartment && <TableCell className="text-sm text-slate-600">{m.department}</TableCell>}
              <TableCell className="text-right">
                <div data-testid={`allocation-row-${m.id}-allocation`} className="num text-sm text-slate-900">{fmt(m.allocation)}</div>
                <div data-testid={`allocation-row-${m.id}-monthly`} className="num whitespace-nowrap text-[11px] text-slate-400">{fmt(m.monthly_allocation)} / mo</div>
              </TableCell>
              <TableCell data-testid={`allocation-row-${m.id}-used`} className="num text-right text-sm text-slate-900">{fmt(m.credits)}</TableCell>
              <TableCell data-testid={`allocation-row-${m.id}-remaining`} className={`num text-right text-sm ${m.remaining < 0 ? "text-red-600" : "text-slate-600"}`}>{fmt(m.remaining)}</TableCell>
              <TableCell>
                <div className="flex items-center gap-2"><Meter value={m.utilisation} className="w-20" /><span data-testid={`allocation-row-${m.id}-utilisation`} className="num text-xs text-slate-600">{m.utilisation}%</span></div>
              </TableCell>
              <TableCell><StatusPill tone={HEALTH[m.health].tone} testId={`allocation-row-${m.id}-health`}>{HEALTH[m.health].label}</StatusPill></TableCell>
              <TableCell className="pr-5 text-right">
                <Button size="sm" variant="ghost" aria-label={`Edit allocation for ${m.name}`} data-testid={`edit-allocation-${m.id}`} onClick={() => onEdit(m)}>
                  <Pencil className="h-3.5 w-3.5" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};
