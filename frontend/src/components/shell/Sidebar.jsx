import { NavLink } from "react-router-dom";
import { Layers } from "lucide-react";
import { MODULES } from "@/lib/modules";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

const NavItem = ({ module, onNavigate }) => {
  const Icon = module.icon;
  return (
    <NavLink
      to={module.path}
      onClick={onNavigate}
      data-testid={`nav-${module.id}`}
      className={({ isActive }) =>
        cn(
          "focus-ring group flex min-h-[44px] items-center gap-2.5 rounded-md px-2.5 py-[7px] text-sm transition-colors duration-150 md:min-h-0 md:text-[13px]",
          isActive ? "bg-white text-slate-900 font-medium shadow-[0_1px_2px_rgba(16,24,40,0.06)] ring-1 ring-border" : "text-slate-600 hover:bg-slate-200/50 hover:text-slate-900"
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon className={cn("h-4 w-4 shrink-0", isActive ? "text-indigo-600" : "text-slate-400 group-hover:text-slate-600")} strokeWidth={1.75} />
          <span className="flex-1 truncate">{module.label}</span>
          {module.phase > 1 && !module.live && <span className="text-[10px] font-medium text-slate-400">Soon</span>}
        </>
      )}
    </NavLink>
  );
};

export const Sidebar = ({ onNavigate }) => {
  const { user } = useAuth();
  const allowed = new Set(user.allowed_modules);
  const modules = MODULES.filter((m) => allowed.has(m.id));
  const workspace = user.organization?.name || "Personal workspace";
  return (
    <div data-testid="sidebar" className="flex h-full flex-col bg-sidebar">
      <div className="flex items-center gap-2.5 px-4 pb-4 pt-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-900 text-white">
          <Layers className="h-4 w-4" strokeWidth={2} />
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-900">Orqestra</div>
          <div data-testid="sidebar-workspace" className="truncate text-xs text-slate-500">{workspace}</div>
        </div>
      </div>
      <div className="px-4 pb-3">
        <span data-testid="sidebar-mode-pill" className="inline-flex items-center gap-1.5 rounded-full border border-border bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
          {user.mode === "organisation" ? `Organisation · ${user.role_label.replace("Organisation ", "")}` : "Individual"}
        </span>
      </div>
      <nav data-testid="sidebar-nav" aria-label="Main navigation" className="flex-1 space-y-0.5 overflow-y-auto px-2.5 py-1">
        {modules.map((m) => <NavItem key={m.id} module={m} onNavigate={onNavigate} />)}
      </nav>
      <div className="border-t border-border px-4 py-3 text-[11px] leading-relaxed text-slate-400">
        Tracks allocations and obligations in credits. Provider data is simulated.
      </div>
    </div>
  );
};
