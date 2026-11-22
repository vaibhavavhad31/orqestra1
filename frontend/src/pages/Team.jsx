import { useState } from "react";
import { Pencil, Plus, Search, UserMinus, UserPlus, Users } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useAction } from "@/hooks/useAction";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader, Panel } from "@/components/common/Layout";
import { EmptyState, ErrorState } from "@/components/common/States";
import { StatusPill } from "@/components/common/StatusPill";
import { DataTable } from "@/components/common/DataTable";
import { DeptDialog, MemberDialog, TempPasswordDialog } from "@/components/team/TeamDialogs";
import { fmt } from "@/lib/format";

const ROLE = { admin: "Admin", manager: "Manager", employee: "Employee" };

const Actions = ({ m, me, onEdit, onChanged }) => {
  const { run, busy } = useAction();
  const active = m.status !== "deactivated";
  const blocked = m.id === me || m.is_demo;
  const toggle = async () => { if (await run(() => api.post(`/team/members/${m.id}/${active ? "deactivate" : "reactivate"}`), active ? "Member deactivated" : "Member reactivated")) onChanged(); };
  return (
    <div className="flex justify-end gap-1">
      <Button size="sm" variant="ghost" className="h-8 px-2" data-testid={`member-${m.id}-edit`} aria-label={`Edit ${m.name}`} onClick={() => onEdit(m)}><Pencil className="h-3.5 w-3.5" /></Button>
      <Button size="sm" variant="ghost" className={`h-8 px-2 text-xs ${active ? "text-red-600" : ""}`} disabled={busy} data-testid={`member-${m.id}-${active ? "deactivate" : "reactivate"}`}
        title={blocked && active ? (m.is_demo ? "Demo accounts are protected" : "You can't deactivate yourself") : undefined} onClick={toggle}>
        {active ? <><UserMinus className="mr-1 h-3.5 w-3.5" />Deactivate</> : <><UserPlus className="mr-1 h-3.5 w-3.5" />Reactivate</>}
      </Button>
    </div>
  );
};

export default function Team() {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [dept, setDept] = useState("all");
  const [dialog, setDialog] = useState({ open: false, member: null });
  const [temp, setTemp] = useState(null);
  const [deptDialog, setDeptDialog] = useState(null);
  const { data, error, reload } = useApi("/team/members", { q: q || undefined, department_id: dept !== "all" ? dept : undefined });
  const manage = data?.can_manage;

  const columns = [
    { key: "name", label: "Member", render: (m) => <div><div className="font-medium text-slate-900">{m.name}{m.is_demo && <span className="ml-1.5 text-[10px] font-normal text-slate-400">demo</span>}</div><div className="text-xs font-normal text-slate-500">{m.email}</div></div> },
    { key: "role", label: "Role", render: (m) => ROLE[m.role] },
    { key: "department", label: "Department" },
    { key: "title", label: "Title" },
    { key: "status", label: "Status", render: (m) => <StatusPill tone={m.status === "active" ? "success" : "neutral"} testId={`member-${m.id}-status`}>{m.status === "active" ? "Active" : "Deactivated"}</StatusPill> },
    { key: "monthly_allocation", label: "Allocation", align: "right", render: (m) => fmt(m.monthly_allocation) },
    ...(manage ? [{ key: "actions", label: "", render: (m) => <Actions m={m} me={user.id} onEdit={(x) => setDialog({ open: true, member: x })} onChanged={reload} /> }] : []),
  ];

  return (
    <div data-testid="team-page" className="space-y-6 sm:space-y-8">
      <PageHeader eyebrow={manage ? "Organisation" : "Your department · read-only"} title="Team" description={manage ? "People, roles and departments" : "Members of your department"}
        actions={manage && <Button data-testid="add-member" onClick={() => setDialog({ open: true, member: null })}><Plus className="mr-1.5 h-4 w-4" />Add member</Button>} />
      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="relative sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input data-testid="team-search" aria-label="Search members" placeholder="Search name, email or title" value={q} onChange={(e) => setQ(e.target.value)} className="h-10 bg-white pl-9" />
        </div>
        {manage && (
          <Select value={dept} onValueChange={setDept}>
            <SelectTrigger data-testid="team-department-filter" aria-label="Filter by department" className="h-10 bg-white sm:w-52"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all" data-testid="team-department-all">All departments</SelectItem>
              {data?.departments.map((d) => <SelectItem key={d.id} value={d.id} data-testid={`team-department-${d.id}`}>{d.name}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </div>
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12 xl:items-start">
        <Panel testId="team-members-panel" title={data ? `${data.members.length} members` : "Members"} className={manage ? "xl:col-span-9" : "xl:col-span-12"} bodyClassName="p-0">
          {error ? <div className="p-5"><ErrorState message={error} onRetry={reload} /></div> : !data ? <div className="space-y-2 p-5">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-10" />)}</div>
            : data.members.length === 0 ? <div className="p-5"><EmptyState icon={Users} title="No members match" description="Try a different search or department." /></div>
              : <DataTable testId="team-table" rows={data.members} columns={columns} />}
        </Panel>
        {manage && (
          <Panel testId="departments-panel" title="Departments" className="xl:col-span-3"
            action={<Button size="sm" variant="outline" className="h-8" data-testid="add-department" onClick={() => setDeptDialog({})}><Plus className="mr-1 h-3.5 w-3.5" />New</Button>}>
            <ul className="space-y-1">
              {data?.departments.map((d) => (
                <li key={d.id} className="flex items-center justify-between gap-2 rounded-md px-1 py-1.5">
                  <span data-testid={`department-${d.id}-name`} className="truncate text-sm text-slate-700">{d.name}</span>
                  <Button size="sm" variant="ghost" className="h-8 px-2 text-xs" data-testid={`department-${d.id}-rename`} onClick={() => setDeptDialog(d)}>Rename</Button>
                </li>
              ))}
            </ul>
          </Panel>
        )}
      </div>
      <MemberDialog open={dialog.open} member={dialog.member} departments={data?.departments || []} onClose={() => setDialog({ open: false, member: null })}
        onSaved={(res) => { setDialog({ open: false, member: null }); if (res.temporary_password) setTemp(res); reload(); }} />
      <TempPasswordDialog info={temp} onClose={() => setTemp(null)} />
      <DeptDialog dept={deptDialog} onClose={() => setDeptDialog(null)} onSaved={() => { setDeptDialog(null); reload(); }} />
    </div>
  );
}
