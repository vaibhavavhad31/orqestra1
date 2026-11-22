import { useEffect, useState } from "react";
import { Copy, KeyRound } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Field } from "@/components/auth/Field";
import { FormDialog } from "@/components/common/FormDialog";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const ROLES = [{ id: "employee", name: "Employee" }, { id: "manager", name: "Manager" }, { id: "admin", name: "Admin" }];

export const Pick = ({ id, label, value, onChange, options, error, disabled }) => (
  <div className="space-y-1.5">
    <span className="text-xs font-medium text-slate-700">{label}</span>
    <Select value={value || undefined} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger data-testid={`select-${id}`} aria-label={label} className={`h-10 bg-white ${error ? "border-red-400" : ""}`}><SelectValue placeholder="Choose" /></SelectTrigger>
      <SelectContent>{options.map((o) => <SelectItem key={o.id} value={o.id} data-testid={`select-${id}-${o.id}`}>{o.name}</SelectItem>)}</SelectContent>
    </Select>
    {error && <p data-testid={`field-error-${id}`} className="text-xs text-red-600">{error}</p>}
  </div>
);

export const MemberDialog = ({ open, member, departments, onClose, onSaved }) => {
  const [f, setF] = useState({});
  const { run, busy, fields, error, reset } = useAction();
  useEffect(() => {
    setF(member ? { role: member.role, department_id: member.department_id, title: member.title || "" } : { name: "", email: "", role: "employee", department_id: "", title: "" });
    reset();
  }, [open, member]); // eslint-disable-line react-hooks/exhaustive-deps
  const set = (k) => (e) => setF({ ...f, [k]: e?.target ? e.target.value : e });
  const submit = async () => {
    const res = await run(() => (member ? api.patch(`/team/members/${member.id}`, f) : api.post("/team/members", f)), member ? "Member updated" : null);
    if (res) onSaved(res);
  };
  const protectedAcc = member?.is_demo;
  return (
    <FormDialog open={open} onOpenChange={(o) => !o && onClose()} testId="member-dialog" busy={busy} error={error} onSubmit={submit}
      title={member ? `Edit ${member.name}` : "Add a member"} submitLabel={member ? "Save" : "Add member"}
      description={member ? (protectedAcc ? "Demo accounts are protected: role and department can't change." : member.email) : "A one-time temporary password is shown after you add them."}>
      {!member && <>
        <Field id="member-name" label="Name" value={f.name || ""} onChange={set("name")} error={fields.name} />
        <Field id="member-email" label="Email" type="email" value={f.email || ""} onChange={set("email")} error={fields.email} />
      </>}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Pick id="member-role" label="Role" value={f.role} onChange={set("role")} options={ROLES} error={fields.role} disabled={protectedAcc} />
        <Pick id="member-department" label="Department" value={f.department_id} onChange={set("department_id")} options={departments} error={fields.department_id} disabled={protectedAcc} />
      </div>
      <Field id="member-title" label="Job title" value={f.title || ""} onChange={set("title")} error={fields.title} />
    </FormDialog>
  );
};

export const TempPasswordDialog = ({ info, onClose }) => (
  <Dialog open={!!info} onOpenChange={(o) => !o && onClose()}>
    <DialogContent data-testid="temp-password-dialog" className="w-[calc(100vw-2rem)] max-w-md rounded-lg">
      <DialogHeader className="text-left">
        <DialogTitle className="flex items-center gap-2 text-base"><KeyRound className="h-4 w-4 text-indigo-600" />{info?.member.name} was added</DialogTitle>
        <DialogDescription>Share this temporary password with them. It is shown only once and can't be retrieved later.</DialogDescription>
      </DialogHeader>
      <div className="space-y-1 rounded-md border border-border bg-slate-50 p-3">
        <div className="text-xs text-slate-500">{info?.member.email}</div>
        <div className="flex items-center justify-between gap-2">
          <code data-testid="temp-password-value" className="num break-all text-base font-semibold text-slate-900">{info?.temporary_password}</code>
          <Button size="sm" variant="outline" data-testid="temp-password-copy" onClick={() => navigator.clipboard?.writeText(info.temporary_password).then(() => toast.success("Copied"))}><Copy className="h-3.5 w-3.5" /></Button>
        </div>
      </div>
      <DialogFooter><Button data-testid="temp-password-done" onClick={onClose}>Done</Button></DialogFooter>
    </DialogContent>
  </Dialog>
);

export const DeptDialog = ({ dept, onClose, onSaved }) => {
  const [name, setName] = useState("");
  const { run, busy, fields, error, reset } = useAction();
  useEffect(() => { setName(dept?.name || ""); reset(); }, [dept]); // eslint-disable-line react-hooks/exhaustive-deps
  const submit = async () => {
    const res = await run(() => (dept.id ? api.patch(`/org/departments/${dept.id}`, { name }) : api.post("/org/departments", { name })), dept.id ? "Department renamed" : "Department created");
    if (res) onSaved();
  };
  return (
    <FormDialog open={!!dept} onOpenChange={(o) => !o && onClose()} testId="department-dialog" busy={busy} error={error} onSubmit={submit}
      title={dept?.id ? "Rename department" : "New department"} submitLabel={dept?.id ? "Rename" : "Create"}>
      <Field id="department-name" label="Department name" value={name} onChange={(e) => setName(e.target.value)} error={fields.name} />
    </FormDialog>
  );
};
