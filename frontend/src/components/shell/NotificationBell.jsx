import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, CheckCheck } from "lucide-react";
import { api } from "@/lib/api";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { timeAgo } from "@/lib/format";

export const NOTIFY_EVENT = "notifications:changed";
export const announce = () => window.dispatchEvent(new Event(NOTIFY_EVENT));

export const NotificationItem = ({ n, onOpen, testId }) => (
  <button type="button" data-testid={testId} onClick={() => onOpen(n)}
    className={`focus-ring flex w-full items-start gap-2.5 rounded-md px-3 py-2.5 text-left transition-colors duration-150 hover:bg-slate-50 ${n.read ? "" : "bg-indigo-50/40"}`}>
    <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read ? "bg-transparent" : "bg-indigo-500"}`} aria-label={n.read ? "Read" : "Unread"} />
    <span className="min-w-0 flex-1">
      <span className={`block text-sm leading-snug ${n.read ? "text-slate-600" : "font-medium text-slate-900"}`}>{n.title}</span>
      <span className="mt-0.5 block text-[11px] text-slate-400">{timeAgo(n.created_at)}</span>
    </span>
  </button>
);

export const useOpenNotification = () => {
  const navigate = useNavigate();
  return async (n) => {
    if (!n.read) { await api.post(`/notifications/${n.id}/read`).catch(() => {}); announce(); }
    if (n.link) navigate(n.link);
  };
};

export const NotificationBell = () => {
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState(null);
  const openItem = useOpenNotification();
  const navigate = useNavigate();

  const refresh = useCallback(() => api.get("/notifications/unread-count").then(({ data }) => setUnread(data.unread)).catch(() => {}), []);
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30000);
    window.addEventListener(NOTIFY_EVENT, refresh);
    return () => { clearInterval(t); window.removeEventListener(NOTIFY_EVENT, refresh); };
  }, [refresh]);
  useEffect(() => {
    if (!open) return;
    setItems(null);
    api.get("/notifications", { params: { limit: 8 } }).then(({ data }) => { setItems(data.items); setUnread(data.unread); }).catch(() => setItems([]));
  }, [open, unread]);

  const readAll = async () => { await api.post("/notifications/read-all"); setUnread(0); setItems((xs) => xs?.map((n) => ({ ...n, read: true }))); announce(); };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger data-testid="notification-bell" aria-label={`Notifications, ${unread} unread`}
        className="focus-ring relative flex h-10 w-10 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100">
        <Bell className="h-[18px] w-[18px]" />
        {unread > 0 && (
          <span data-testid="notification-unread-count" className="num absolute right-1 top-1 flex h-[17px] min-w-[17px] items-center justify-center rounded-full bg-indigo-600 px-1 text-[10px] font-semibold text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[min(360px,calc(100vw-1.5rem))] p-0" data-testid="notification-dropdown">
        <div className="flex items-center justify-between border-b border-border-subtle px-3 py-2.5">
          <span className="text-sm font-semibold text-slate-900">Notifications</span>
          <Button size="sm" variant="ghost" className="h-8 px-2 text-xs" disabled={!unread} onClick={readAll} data-testid="bell-mark-all-read">
            <CheckCheck className="mr-1 h-3.5 w-3.5" />Mark all as read
          </Button>
        </div>
        <div className="max-h-[360px] overflow-y-auto p-1">
          {items === null ? <p className="px-3 py-6 text-center text-xs text-slate-400">Loading…</p>
            : items.length === 0 ? <p data-testid="bell-empty" className="px-3 py-6 text-center text-sm text-slate-500">You're all caught up.</p>
              : items.map((n) => <NotificationItem key={n.id} n={n} testId={`bell-item-${n.id}`} onOpen={(x) => { setOpen(false); openItem(x); }} />)}
        </div>
        <button type="button" data-testid="bell-view-all" onClick={() => { setOpen(false); navigate("/notifications"); }}
          className="focus-ring w-full border-t border-border-subtle py-2.5 text-center text-xs font-medium text-indigo-600 hover:bg-slate-50">View all notifications</button>
      </PopoverContent>
    </Popover>
  );
};
