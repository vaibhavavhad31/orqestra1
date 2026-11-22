import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Building2, User, UserRound, Users } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Skeleton } from "@/components/ui/skeleton";

const ICONS = { admin: Building2, manager: Users, employee: UserRound, individual: User };

const DemoTile = ({ acc, busy, onClick }) => {
  const Icon = ICONS[acc.key];
  return (
    <button
      type="button"
      data-testid={`demo-login-${acc.key}`}
      disabled={!!busy}
      onClick={() => onClick(acc)}
      className="focus-ring group flex w-full items-center gap-3.5 rounded-lg border border-border bg-white p-3.5 text-left transition-[border-color,box-shadow] duration-150 hover:border-slate-300 hover:shadow-sm disabled:opacity-60"
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-slate-50">
        <Icon className="h-4 w-4 text-slate-600" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium text-slate-900">{acc.role_label}</div>
        <div className="truncate text-xs text-slate-500">{acc.name} · {acc.workspace}</div>
        <div className="mt-0.5 truncate text-xs text-slate-400">{acc.description}</div>
      </div>
      {busy === acc.key
        ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600" />
        : <ArrowRight className="h-4 w-4 text-slate-300 transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-slate-500" />}
    </button>
  );
};

export const DemoLogins = () => {
  const { demoLogin } = useAuth();
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState(null);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    api.get("/demo/accounts").then(({ data }) => setAccounts(data)).catch(() => setAccounts([]));
  }, []);

  const onClick = async (acc) => {
    setBusy(acc.key);
    try {
      await demoLogin(acc.key);
      navigate("/overview", { replace: true });
    } catch (e) {
      toast.error(formatApiError(e));
      setBusy(null);
    }
  };

  return (
    <div data-testid="demo-logins" className="space-y-2.5">
      {accounts === null
        ? [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[74px] rounded-lg" />)
        : accounts.map((acc) => <DemoTile key={acc.key} acc={acc} busy={busy} onClick={onClick} />)}
    </div>
  );
};
