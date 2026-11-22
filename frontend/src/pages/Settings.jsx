import { useEffect, useState } from "react";
import { Lock } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useAction } from "@/hooks/useAction";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Field } from "@/components/auth/Field";
import { PageHeader, Panel } from "@/components/common/Layout";
import { ErrorState } from "@/components/common/States";

const Form = ({ onSubmit, busy, error, label, testId, children }) => (
  <form noValidate className="space-y-3" onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
    {error && <p role="alert" data-testid={`${testId}-error`} className="text-sm text-red-600">{error}</p>}
    {children}
    <Button type="submit" disabled={busy} data-testid={`${testId}-submit`}>{busy ? "Saving…" : label}</Button>
  </form>
);

const Profile = ({ s, onSaved }) => {
  const [f, setF] = useState({ name: s.profile.name, title: s.profile.title || "" });
  const { run, busy, fields, error } = useAction();
  return (
    <Form testId="profile" label="Save profile" busy={busy} error={error} onSubmit={async () => { if (await run(() => api.patch("/settings/profile", f), "Profile saved")) onSaved(); }}>
      <Field id="profile-name" label="Name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} error={fields.name} />
      <Field id="profile-title" label="Job title" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} error={fields.title} />
      <p className="text-xs text-slate-500">Email: {s.profile.email}</p>
    </Form>
  );
};

const DEMO_COPY = "Password changes are disabled for demo accounts";

const Password = ({ s }) => {
  const blank = { current_password: "", new_password: "", confirm_password: "" };
  const [f, setF] = useState(blank);
  const { run, busy, fields, error } = useAction();
  if (!s.has_password) {
    return <p data-testid="google-signin-note" className="flex items-center gap-2 text-sm text-slate-600"><Lock className="h-4 w-4 text-slate-400" />Signed in with Google</p>;
  }
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <fieldset disabled={s.is_demo} className="space-y-3">
      {s.is_demo && <p data-testid="password-demo-note" className="flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600"><Lock className="h-4 w-4 text-slate-400" />{DEMO_COPY}</p>}
      <Form testId="password" label="Change password" busy={busy} error={error} onSubmit={async () => { if (await run(() => api.post("/settings/password", f), "Password changed")) setF(blank); }}>
        <Field id="current-password" label="Current password" type="password" autoComplete="current-password" value={f.current_password} onChange={set("current_password")} error={fields.current_password} />
        <Field id="new-password" label="New password" type="password" autoComplete="new-password" value={f.new_password} onChange={set("new_password")} error={fields.new_password} />
        <Field id="confirm-password" label="Confirm new password" type="password" autoComplete="new-password" value={f.confirm_password} onChange={set("confirm_password")} error={fields.confirm_password} />
      </Form>
    </fieldset>
  );
};

const CATS = [["lending", "Lending", "Requests, offers and repayments"], ["allocation", "Allocation", "Budgets, allocations and resource requests"],
  ["handover", "Task handover", "Handovers sent to you and their updates"], ["sessions", "Sessions", "Reminders and suggested times"]];

const Prefs = ({ s }) => {
  const [p, setP] = useState(s.notification_prefs);
  useEffect(() => setP(s.notification_prefs), [s]);
  const toggle = async (k, v) => {
    const next = { ...p, [k]: v };
    setP(next);
    try { await api.put("/settings/notifications", next); toast.success("Preferences saved"); } catch (e) { setP(p); toast.error(formatApiError(e)); }
  };
  return (
    <ul className="divide-y divide-border-subtle">
      {CATS.map(([k, label, hint]) => (
        <li key={k} className="flex items-center justify-between gap-4 py-3">
          <div><div className="text-sm font-medium text-slate-900">{label}</div><div className="text-xs text-slate-500">{hint}</div></div>
          <Switch data-testid={`pref-${k}`} checked={p[k]} onCheckedChange={(v) => toggle(k, v)} aria-label={`${label} notifications`} />
        </li>
      ))}
    </ul>
  );
};

const Org = ({ org, onSaved }) => {
  const [name, setName] = useState(org.name);
  const { run, busy, fields, error } = useAction();
  return (
    <Form testId="org" label="Save name" busy={busy} error={error} onSubmit={async () => { if (await run(() => api.patch("/org", { name }), "Organisation renamed")) onSaved(); }}>
      <Field id="org-name" label="Organisation name" value={name} onChange={(e) => setName(e.target.value)} error={fields.name} />
    </Form>
  );
};

export default function Settings() {
  const { refresh } = useAuth();
  const { data, error, reload } = useApi("/settings");
  const saved = () => { reload(); refresh(); };
  return (
    <div data-testid="settings-page" className="space-y-6 sm:space-y-8">
      <PageHeader eyebrow="Account" title="Settings" description="Profile, security and preferences" />
      {error ? <ErrorState message={error} onRetry={reload} /> : !data ? <div className="grid gap-6 lg:grid-cols-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-48" />)}</div> : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:items-start">
          <Panel testId="settings-profile" title="Profile"><Profile s={data} onSaved={saved} /></Panel>
          <Panel testId="settings-password" title="Password"><Password s={data} /></Panel>
          <Panel testId="settings-notifications" title="Notification preferences" description="Turned-off categories create no new notifications"><Prefs s={data} /></Panel>
          {data.organization && <Panel testId="settings-organisation" title="Organisation"><Org org={data.organization} onSaved={saved} /></Panel>}
        </div>
      )}
    </div>
  );
}
