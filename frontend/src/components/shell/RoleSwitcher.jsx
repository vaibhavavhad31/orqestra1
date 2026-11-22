import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Check, ChevronsUpDown, Eye } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { moduleByPath } from "@/lib/modules";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export const RoleSwitcher = () => {
  const { user, switchTo } = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    api.get("/demo/accounts", { params: { include_friends: true } }).then(({ data }) => setAccounts(data)).catch(() => setAccounts([]));
  }, []);

  if (!user?.is_demo) return null;

  const onPick = async (acc) => {
    if (acc.user_id === user.id) return;
    setBusy(true);
    try {
      const next = await switchTo(acc.user_id);
      const current = moduleByPath(location.pathname);
      if (!current || !next.allowed_modules.includes(current.id)) navigate("/overview");
      toast.success(`Now viewing as ${acc.role_label}`, { description: acc.name });
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        data-testid="role-switcher-trigger"
        disabled={busy}
        className="focus-ring inline-flex min-h-[40px] items-center gap-2 rounded-md border border-indigo-200 bg-indigo-50 px-2.5 py-1.5 text-xs font-medium text-indigo-700 transition-colors duration-150 hover:bg-indigo-100 sm:min-h-0"
      >
        <Eye className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">View as</span>
        <span data-testid="role-switcher-current">{user.role_label}</span>
        <ChevronsUpDown className="h-3 w-3 opacity-60" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72" data-testid="role-switcher-menu">
        <DropdownMenuLabel className="text-xs font-normal text-slate-500">Switch demo account (demo only)</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {[["primary", null], ["friends", "Individual friends"]].map(([group, heading]) => {
          const items = accounts.filter((a) => (a.group || "primary") === group);
          if (!items.length) return null;
          return (
            <div key={group} data-testid={`role-switcher-group-${group}`}>
              {heading && <><DropdownMenuSeparator /><DropdownMenuLabel className="text-xs font-normal text-slate-500">{heading}</DropdownMenuLabel></>}
              {items.map((acc) => (
                <DropdownMenuItem key={acc.key} data-testid={`role-switch-${acc.key}`} onSelect={() => onPick(acc)} className="cursor-pointer gap-3 py-2">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-slate-900">{group === "friends" ? acc.name : acc.role_label}</div>
                    <div className="truncate text-xs text-slate-500">
                      {group === "friends" ? acc.description : `${acc.name} · ${acc.key === "individual" ? "Personal workspace" : "Organisation demo"}`}
                    </div>
                  </div>
                  {acc.user_id === user.id && <Check className="h-4 w-4 text-indigo-600" />}
                </DropdownMenuItem>
              ))}
            </div>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
