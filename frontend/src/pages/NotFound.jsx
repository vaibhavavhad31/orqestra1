import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div data-testid="not-found" className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="max-w-md">
        <div className="eyebrow mb-2">404</div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">This page doesn't exist</h1>
        <p className="mt-2 text-sm text-slate-500">Check the address, or head back to your workspace.</p>
        <Button asChild className="mt-6"><Link to="/overview">Go to Overview</Link></Button>
      </div>
    </div>
  );
}
