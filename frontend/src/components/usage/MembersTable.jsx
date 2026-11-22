import { Users } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusPill } from "@/components/common/StatusPill";
import { EmptyState } from "@/components/common/States";
import { Meter } from "@/components/common/Meter";
import { fmt, HEALTH } from "@/lib/format";

export const MembersTable = ({ members, showAllocation, showDepartment, providers = [] }) => {
  if (!members.length) return <div className="p-5"><EmptyState icon={Users} title="No members" description="No one is in this scope yet." /></div>;
  const pname = Object.fromEntries(providers.map((p) => [p.id, p.name]));
  return (
    <div className="overflow-x-auto" data-testid="members-table">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-5 text-xs">Member</TableHead>
            {showDepartment && <TableHead className="text-xs">Department</TableHead>}
            <TableHead className="text-right text-xs">Credits</TableHead>
            <TableHead className="text-right text-xs">Requests</TableHead>
            {providers.length > 0 && <TableHead className="text-xs">Top provider</TableHead>}
            {showAllocation && <TableHead className="min-w-[160px] text-xs">Utilisation</TableHead>}
            {showAllocation && <TableHead className="pr-5 text-xs">Status</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {members.map((m) => (
            <TableRow key={m.id} data-testid={`member-row-${m.id}`}>
              <TableCell className="pl-5">
                <div className="whitespace-nowrap text-sm font-medium text-slate-900">{m.name}</div>
                <div className="whitespace-nowrap text-xs text-slate-500">{m.title}</div>
              </TableCell>
              {showDepartment && <TableCell className="text-sm text-slate-600">{m.department}</TableCell>}
              <TableCell className="num text-right text-sm text-slate-900">{fmt(m.credits)}</TableCell>
              <TableCell className="num text-right text-sm text-slate-600">{fmt(m.requests)}</TableCell>
              {providers.length > 0 && <TableCell className="text-sm text-slate-600">{pname[m.top_provider] || "—"}</TableCell>}
              {showAllocation && (
                <TableCell>
                  <div className="flex items-center gap-2.5">
                    <Meter value={m.utilisation} className="w-20" />
                    <span className="num text-xs text-slate-600">{m.utilisation}%</span>
                  </div>
                  <div className="num mt-1 text-[11px] text-slate-400">{fmt(m.credits)} / {fmt(m.allocation)}</div>
                </TableCell>
              )}
              {showAllocation && <TableCell className="pr-5"><StatusPill tone={HEALTH[m.health].tone}>{HEALTH[m.health].label}</StatusPill></TableCell>}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};
