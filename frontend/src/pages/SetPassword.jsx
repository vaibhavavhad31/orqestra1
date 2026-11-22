import { useState } from "react";
import { KeyRound } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useAction } from "@/hooks/useAction";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/auth/Field";

export default function SetPassword() {
  const { user, refresh, logout } = useAuth();
  const [f, setF] = useState({ new_password: "", confirm_password: "" });
  const { run, busy, fields, error } = useAction();
  const submit = async (e) => {
    e.preventDefault();
    if (await run(() => api.post("/auth/set-password", f), "Password set")) await refresh();
  };
  return (
    <div data-testid="set-password-page" className="flex min-h-screen items-center justify-center bg-background px-4">
      <form onSubmit={submit} noValidate className="surface w-full max-w-sm space-y-4 p-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-indigo-50"><KeyRound className="h-5 w-5 text-indigo-600" /></div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Set your new password</h1>
          <p className="mt-1 text-sm text-slate-500">{user.email} was created with a temporary password. Choose your own to continue.</p>
        </div>
        {error && <p role="alert" data-testid="set-password-error" className="text-sm text-red-600">{error}</p>}
        <Field id="set-new-password" label="New password (at least 8 characters)" type="password" autoComplete="new-password"
          value={f.new_password} onChange={(e) => setF({ ...f, new_password: e.target.value })} error={fields.new_password} />
        <Field id="set-confirm-password" label="Confirm new password" type="password" autoComplete="new-password"
          value={f.confirm_password} onChange={(e) => setF({ ...f, confirm_password: e.target.value })} error={fields.confirm_password} />
        <Button type="submit" className="w-full" disabled={busy} data-testid="set-password-submit">{busy ? "Saving…" : "Set password"}</Button>
        <button type="button" data-testid="set-password-logout" onClick={logout} className="focus-ring w-full text-center text-xs text-slate-500 hover:text-slate-700">Log out</button>
      </form>
    </div>
  );
}
