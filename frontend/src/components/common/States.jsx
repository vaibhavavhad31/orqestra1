import { AlertTriangle, Inbox, RotateCw } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

export const DashboardSkeleton = () => (
  <div data-testid="loading-skeleton" className="space-y-6">
    <div className="space-y-2">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-64" />
    </div>
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[118px] rounded-lg" />)}
    </div>
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      <Skeleton className="h-[340px] rounded-lg lg:col-span-8" />
      <Skeleton className="h-[340px] rounded-lg lg:col-span-4" />
    </div>
  </div>
);

export const EmptyState = ({ icon: Icon = Inbox, title, description, action, testId = "empty-state" }) => (
  <div data-testid={testId} className="flex flex-col items-start gap-3 rounded-lg border border-dashed border-slate-300 bg-white/60 px-6 py-10 sm:items-center sm:text-center">
    <div className="flex h-10 w-10 items-center justify-center rounded-md border border-border bg-white">
      <Icon className="h-5 w-5 text-slate-400" strokeWidth={1.75} />
    </div>
    <div>
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      {description && <p className="mt-1 max-w-md text-sm text-slate-500">{description}</p>}
    </div>
    {action}
  </div>
);

export const ErrorState = ({ message, onRetry }) => (
  <div data-testid="error-state" className="surface flex flex-col items-start gap-4 p-6 sm:flex-row sm:items-center">
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-red-50">
      <AlertTriangle className="h-5 w-5 text-red-600" strokeWidth={1.75} />
    </div>
    <div className="flex-1">
      <p className="text-sm font-semibold text-slate-900">We couldn't load this data</p>
      <p data-testid="error-state-message" className="mt-0.5 text-sm text-slate-500">{message}</p>
    </div>
    {onRetry && (
      <Button data-testid="error-retry-button" variant="outline" size="sm" onClick={onRetry}>
        <RotateCw className="mr-1.5 h-3.5 w-3.5" /> Try again
      </Button>
    )}
  </div>
);

export const FullPageLoader = () => (
  <div data-testid="app-loading" className="flex min-h-screen items-center justify-center bg-background">
    <div className="flex items-center gap-3 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600" />
      Loading workspace
    </div>
  </div>
);
