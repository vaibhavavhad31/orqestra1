import { useLocation, useNavigate } from "react-router-dom";
import { LogOut, Menu } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { moduleByPath } from "@/lib/modules";
import { initials } from "@/lib/format";
import { RoleSwitcher } from "@/components/shell/RoleSwitcher";
import { NotificationBell } from "@/components/shell/NotificationBell";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const UserMenu = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };
  return (
    <DropdownMenu>
      <DropdownMenuTrigger data-testid="user-menu-trigger" aria-label={`Account menu for ${user.name}`} className="focus-ring flex h-10 w-10 items-center justify-center rounded-full bg-slate-900 text-[11px] font-semibold text-white">
        {user.picture ? <img src={user.picture} alt="" className="h-8 w-8 rounded-full object-cover" /> : initials(user.name)}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="font-normal">
          <div data-testid="user-menu-name" className="text-sm font-medium text-slate-900">{user.name}</div>
          <div className="truncate text-xs text-slate-500">{user.email}</div>
          <div className="mt-1 text-xs text-slate-500">{user.title || user.role_label}{user.department ? ` · ${user.department.name}` : ""}</div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem data-testid="logout-button" onSelect={onLogout} className="cursor-pointer text-slate-700">
          <LogOut className="mr-2 h-4 w-4" /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export const Topbar = ({ onMenu }) => {
  const { pathname } = useLocation();
  const current = moduleByPath(pathname);
  return (
    <header data-testid="topbar" className="sticky top-0 z-30 flex h-[60px] items-center gap-3 border-b border-border bg-white/85 px-4 backdrop-blur-md sm:px-6">
      <button data-testid="mobile-menu-button" onClick={onMenu} aria-label="Open navigation" className="focus-ring -ml-1.5 flex h-10 w-10 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100 md:hidden">
        <Menu className="h-5 w-5" />
      </button>
      <div className="min-w-0 flex-1 truncate text-sm">
        <span className="hidden text-slate-400 sm:inline">Workspace / </span>
        <span data-testid="topbar-title" className="font-medium text-slate-900">{current?.label || "Page"}</span>
      </div>
      <RoleSwitcher />
      <NotificationBell />
      <UserMenu />
    </header>
  );
};
