import { FlaskConical } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export const SimulatedBadge = ({ testId = "simulated-data-badge", label = "Simulated data" }) => (
  <TooltipProvider delayDuration={150}>
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          data-testid={testId}
          className="inline-flex items-center gap-1.5 rounded-full border border-slate-300/80 bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600"
        >
          <FlaskConical className="h-3 w-3" strokeWidth={2} />
          {label}
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">
        All usage in this workspace is simulated. No live provider data is read and no real credits move.
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
);
