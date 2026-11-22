import { useState } from "react";
import { ArrowLeftRight, Building2, Layers, PiggyBank, Wallet, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/common/Layout";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState } from "@/components/common/States";
import { AllocationMembersTable } from "@/components/allocation/AllocationMembersTable";
import { DepartmentsTable } from "@/components/allocation/DepartmentsTable";
import { SuggestionsPanelBody } from "@/components/allocation/SuggestionsPanel";
import { RequestsList } from "@/components/allocation/RequestsList";
import { CreditsDialog } from "@/components/allocation/CreditsDialog";
import { ReallocateDialog } from "@/components/allocation/ReallocateDialog";
import { DecisionDialog } from "@/components/allocation/RequestDialogs";
import { fmt } from "@/lib/format";

const AdminCards = ({ org, onEdit }) => (
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
    <StatCard testId="alloc-org-budget" label="Org budget / mo" icon={Wallet} value={fmt(org.budget)}>
      <Button size="sm" variant="outline" data-testid="edit-org-budget" onClick={onEdit}><Pencil className="mr-1.5 h-3.5 w-3.5" />Edit budget</Button>
    </StatCard>
    <StatCard testId="alloc-dept-total" label="Department budgets" icon={Building2} value={fmt(org.departments_total)} hint="Sum of all department budgets" />
    <StatCard testId="alloc-org-unallocated" label="Unallocated" icon={PiggyBank} value={fmt(org.unallocated)} hint="Not assigned to a department" />
  </div>
);

const ManagerCards = ({ dept }) => (
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
    <StatCard testId="alloc-dept-budget" label={`${dept.name} budget / mo`} icon={Wallet} value={fmt(dept.budget)} hint="Set by your organisation admin" />
    <StatCard testId="alloc-dept-allocated" label="Allocated to members" icon={Layers} value={fmt(dept.allocated)} hint={`${dept.members} members`} />
    <StatCard testId="alloc-dept-unallocated" label="Unallocated pool" icon={PiggyBank} value={fmt(dept.unallocated)} hint="Available for requests" />
  </div>
);

export const AllocationManage = ({ data, reload }) => {
  const [edit, setEdit] = useState(null);
  const [realloc, setRealloc] = useState(null);
  const [decision, setDecision] = useState(null);
  const admin = data.role === "admin";
  const done = (close) => () => { close(null); reload(); };

  const editMember = (m) => setEdit({ path: `/allocation/members/${m.id}`, value: m.monthly_allocation, title: `Allocation for ${m.name}`,
    description: `Monthly credits for ${m.name}. Member allocations can't exceed the ${m.department} budget.` });
  const editDept = (d) => setEdit({ path: `/allocation/departments/${d.id}`, value: d.budget, title: `${d.name} budget`,
    description: "Department budgets can't exceed the organisation budget, or fall below what is already allocated to members." });
  const editOrg = () => setEdit({ path: "/allocation/org", value: data.org.budget, title: "Organisation budget",
    description: "Monthly credits for the whole organisation. It must cover all department budgets." });

  return (
    <div className="space-y-6 sm:space-y-8">
      {admin ? <AdminCards org={data.org} onEdit={editOrg} /> : data.departments[0] && <ManagerCards dept={data.departments[0]} />}
      {admin && (
        <Panel testId="departments-panel" title="Department budgets" description="Monthly budgets and how much is allocated to members" bodyClassName="p-0">
          {data.departments.length ? <DepartmentsTable departments={data.departments} onEdit={editDept} />
            : <div className="p-5"><EmptyState icon={Building2} title="No departments yet" description="Departments will appear here once they're set up." /></div>}
        </Panel>
      )}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
        <Panel testId="allocation-members-panel" title="Member allocations" description={`Allocation pro-rated to ${data.days} days · Underutilised < 40% · Near limit ≥ 85%`}
          className="lg:col-span-8" bodyClassName="p-0"
          action={<Button size="sm" variant="outline" data-testid="open-reallocate" onClick={() => setRealloc({})} disabled={data.members.length < 2}><ArrowLeftRight className="mr-1.5 h-3.5 w-3.5" />Reallocate</Button>}>
          <AllocationMembersTable members={data.members} showDepartment={admin} onEdit={editMember} />
        </Panel>
        <Panel testId="underutilised-allocations-panel" title="Underutilised allocations" description="Rebalance idle credits towards people near their limit" className="lg:col-span-4">
          <SuggestionsPanelBody members={data.members} suggestions={data.suggestions} onApply={setRealloc} />
        </Panel>
      </div>
      <Panel testId="requests-panel" title="Resource requests" description={admin ? "Requests from across the organisation" : "Requests from your department"} bodyClassName="p-0">
        <RequestsList requests={data.requests} canDecide onDecide={setDecision} onChanged={reload} />
      </Panel>
      <CreditsDialog target={edit} onClose={() => setEdit(null)} onSaved={done(setEdit)} />
      <ReallocateDialog preset={realloc} members={data.members} onClose={() => setRealloc(null)} onSaved={done(setRealloc)} />
      <DecisionDialog decision={decision} onClose={() => setDecision(null)} onSaved={done(setDecision)} />
    </div>
  );
};
