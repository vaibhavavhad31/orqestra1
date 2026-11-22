import { Link } from "react-router-dom";
import { ShieldOff } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { moduleById } from "@/lib/modules";
import { Button } from "@/components/ui/button";

export default function AccessDenied({ moduleId }) {
  const { user } = useAuth();
  const module = moduleById(moduleId);
  return (
    <div data-testid="access-denied" className="flex min-h-[60vh] items-center">
      <div className="surface w-full max-w-xl p-8 animate-fade-up">
        <div className="flex h-11 w-11 items-center justify-center rounded-md border border-border bg-slate-50">
          <ShieldOff className="h-5 w-5 text-slate-500" strokeWidth={1.75} />
        </div>
        <h1 data-testid="access-denied-title" className="mt-5 text-xl font-semibold tracking-tight text-slate-900">
          You don't have access to this page
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          {module?.label || "This module"} isn't available for {user.role_label} accounts
          {user.mode === "organisation" ? " in your organisation" : ""}. Access is enforced by the server, not just hidden in the menu.
        </p>
        {user.is_demo && (
          <p className="mt-2 text-sm text-slate-500">Use "View as" in the top bar to try another demo role.</p>
        )}
        <Button asChild className="mt-6" data-testid="access-denied-back-button">
          <Link to="/overview">Back to Overview</Link>
        </Button>
      </div>
    </div>
  );
}
