import { cn } from "@/lib/utils";

export const PageHeader = ({ eyebrow, title, description, actions, testId = "page-header" }) => (
  <div data-testid={testId} className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
    <div className="min-w-0">
      {eyebrow && <div className="eyebrow mb-2">{eyebrow}</div>}
      <h1 data-testid="page-title" className="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900 leading-tight">
        {title}
      </h1>
      {description && <p className="mt-1.5 text-sm text-slate-500">{description}</p>}
    </div>
    {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
  </div>
);

export const Panel = ({ title, description, action, children, className, testId, bodyClassName }) => (
  <section data-testid={testId} className={cn("surface min-w-0 animate-fade-up", className)}>
    {(title || action) && (
      <header className="flex items-start justify-between gap-3 border-b border-border-subtle px-5 py-4">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
        </div>
        {action}
      </header>
    )}
    <div className={cn("min-w-0 p-5", bodyClassName)}>{children}</div>
  </section>
);
