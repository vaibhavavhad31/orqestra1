import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { fieldErrors, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/auth/Field";
import { ModeSelector } from "@/components/auth/ModeSelector";
import { Brand } from "@/components/auth/AuthBits";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { PENDING_KEY } from "@/pages/AuthCallback";

export default function ChooseMode() {
  const { completeGoogle } = useAuth();
  const navigate = useNavigate();
  const pending = JSON.parse(sessionStorage.getItem(PENDING_KEY) || "null");
  const [mode, setMode] = useState("");
  const [orgName, setOrgName] = useState("");
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!pending) return <Navigate to="/login" replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!mode) return setErrors({ mode: "Choose Individual or Organisation" });
    if (mode === "organisation" && !orgName.trim()) return setErrors({ org_name: "Enter your organisation name" });
    setLoading(true);
    try {
      await completeGoogle({ pending_token: pending.pending_token, mode, org_name: orgName });
      sessionStorage.removeItem(PENDING_KEY);
      navigate("/overview", { replace: true });
    } catch (err) {
      setErrors(fieldErrors(err));
      setError(formatApiError(err));
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <Brand />
      <div data-testid="choose-mode-page">
        <h1 className="mt-10 text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">One last step</h1>
        <p className="mt-1.5 text-sm text-slate-500">
          Signed in with Google as <span data-testid="choose-mode-email" className="font-medium text-slate-700">{pending.email}</span>. How will you use AI Resource Manager?
        </p>
        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          {error && <p data-testid="choose-mode-error" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
          <ModeSelector value={mode} onChange={setMode} error={errors.mode} />
          {mode === "organisation" && (
            <Field id="org_name" label="Organisation name" value={orgName} onChange={(e) => setOrgName(e.target.value)} error={errors.org_name} />
          )}
          <Button type="submit" data-testid="choose-mode-submit-button" disabled={loading} className="h-10 w-full">
            {loading ? "Setting up…" : "Continue"}
          </Button>
        </form>
        <Link to="/login" onClick={() => sessionStorage.removeItem(PENDING_KEY)} className="mt-6 inline-block text-sm text-slate-500 hover:text-slate-700">Cancel</Link>
      </div>
    </AuthLayout>
  );
}
