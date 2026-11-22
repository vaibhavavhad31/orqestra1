import { cn } from "@/lib/utils";

const TONES = {
  neutral: "bg-slate-100 text-slate-600 border-slate-200",
  success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  danger: "bg-red-50 text-red-700 border-red-200",
  info: "bg-sky-50 text-sky-700 border-sky-200",
  accent: "bg-indigo-50 text-indigo-700 border-indigo-200",
};

export const StatusPill = ({ tone = "neutral", children, className, testId }) => (
  <span
    data-testid={testId}
    className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap", TONES[tone], className)}
  >
    {children}
  </span>
);
