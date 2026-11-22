import { ShieldCheck } from "lucide-react";

export const LENDING_DISCLAIMER = "Obligation tracking only. No provider credits are transferred.";

export const LendingDisclaimer = ({ testId = "lending-disclaimer", compact }) => (
  <p
    data-testid={testId}
    className={compact
      ? "flex items-center gap-1.5 text-xs text-slate-500"
      : "flex items-start gap-2 rounded-md border border-border bg-slate-50 px-3.5 py-2.5 text-sm text-slate-600"}
  >
    <ShieldCheck className={`${compact ? "h-3.5 w-3.5" : "mt-0.5 h-4 w-4"} shrink-0 text-slate-400`} />
    {LENDING_DISCLAIMER}
  </p>
);
