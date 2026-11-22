import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { fieldErrors, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/auth/Field";
import { ModeSelector } from "@/components/auth/ModeSelector";
import { Brand, Divider, GoogleButton, GOOGLE_AUTH_ENABLED } from "@/components/auth/AuthBits";
import { AuthLayout } from "@/components/auth/AuthLayout";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/;

const validate = (f) => {
  const e = {};
  if (!f.name.trim()) e.name = "Enter your full name";
  if (!EMAIL_RE.test(f.email.trim())) e.email = "Enter a valid email address";
  if (f.password.length < 8) e.password = "Password must be at least 8 characters";
  if (!f.mode) e.mode = "Choose Individual or Organisation";
  else if (f.mode === "organisation" && !f.org_name.trim()) e.org_name = "Enter your organisation name";
  return e;
};

export default function Signup() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", mode: "", org_name: "" });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target ? e.target.value : e });

  const onSubmit = async (e) => {
    e.preventDefault();
    const local = validate(form);
    setErrors(local);
    setFormError("");
    if (Object.keys(local).length) return;
    setLoading(true);
    try {
      await register({ ...form, email: form.email.trim() });
      navigate("/overview", { replace: true });
    } catch (err) {
      const fields = fieldErrors(err);
      setErrors(fields);
      if (!Object.keys(fields).length) setFormError(formatApiError(err));
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <Brand />
      <h1 className="mt-10 text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">Create your account</h1>
      <p className="mt-1.5 text-sm text-slate-500">Start tracking AI capacity in credits.</p>
      <div className="mt-8 space-y-5">
        <GoogleButton label="Sign up with Google" />
        {GOOGLE_AUTH_ENABLED && <Divider label="or use email" />}
        <form onSubmit={onSubmit} className="space-y-4" data-testid="signup-form" noValidate>
          {formError && <p data-testid="signup-error" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{formError}</p>}
          <Field id="name" label="Full name" value={form.name} onChange={set("name")} error={errors.name} autoComplete="name" />
          <Field id="email" label="Work or personal email" type="email" value={form.email} onChange={set("email")} error={errors.email} autoComplete="email" />
          <Field id="password" label="Password" type="password" value={form.password} onChange={set("password")} error={errors.password}
            autoComplete="new-password" placeholder="At least 8 characters" />
          <div className="space-y-1.5">
            <span className="text-xs font-medium text-slate-700">Account mode</span>
            <ModeSelector value={form.mode} onChange={set("mode")} error={errors.mode} />
          </div>
          {form.mode === "organisation" && (
            <Field id="org_name" label="Organisation name" value={form.org_name} onChange={set("org_name")} error={errors.org_name} />
          )}
          <Button type="submit" data-testid="signup-submit-button" disabled={loading} className="h-10 w-full">
            {loading ? "Creating account…" : "Create account"}
          </Button>
        </form>
      </div>
      <p className="mt-6 text-sm text-slate-500">
        Already have an account? <Link to="/login" data-testid="go-to-login-link" className="font-medium text-indigo-600 hover:text-indigo-700">Sign in</Link>
      </p>
    </AuthLayout>
  );
}
