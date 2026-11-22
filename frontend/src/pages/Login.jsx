import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/auth/Field";
import { Brand, Divider, GoogleButton, GOOGLE_AUTH_ENABLED } from "@/components/auth/AuthBits";
import { DemoLogins } from "@/components/auth/DemoLogins";
import { AuthLayout } from "@/components/auth/AuthLayout";

const LoginForm = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState(location.state?.error || "");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(form.email, form.password);
      navigate(location.state?.from || "/overview", { replace: true });
    } catch (err) {
      setError(formatApiError(err));
      setLoading(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-4" data-testid="login-form" noValidate>
      {error && (
        <div data-testid="login-error" role="alert" className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" /> {error}
        </div>
      )}
      <Field id="email" label="Email" type="email" autoComplete="email" value={form.email}
        onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@company.com" />
      <Field id="password" label="Password" type="password" autoComplete="current-password" value={form.password}
        onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="••••••••" />
      <Button type="submit" data-testid="login-submit-button" disabled={loading} className="h-10 w-full">
        {loading ? "Signing in…" : "Sign in"}
      </Button>
    </form>
  );
};

export default function Login() {
  return (
    <AuthLayout
      aside={
        <div>
          <div className="eyebrow mb-2">Explore instantly</div>
          <h2 className="text-base md:text-lg font-semibold text-slate-900">One-click demo accounts</h2>
          <p className="mt-1 mb-5 text-sm text-slate-500">Sign in as any role in Nexora Technologies, or as an individual user. All usage data is simulated.</p>
          <DemoLogins />
        </div>
      }
    >
      <Brand />
      <h1 className="mt-10 text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">Sign in</h1>
      <p className="mt-1.5 text-sm text-slate-500">See, plan and share AI capacity before anyone runs out.</p>
      <div className="mt-8 space-y-5">
        <GoogleButton />
        {GOOGLE_AUTH_ENABLED && <Divider label="or sign in with email" />}
        <LoginForm />
      </div>
      <p className="mt-6 text-sm text-slate-500">
        New here? <Link to="/signup" data-testid="go-to-signup-link" className="font-medium text-indigo-600 hover:text-indigo-700">Create an account</Link>
      </p>
    </AuthLayout>
  );
}
