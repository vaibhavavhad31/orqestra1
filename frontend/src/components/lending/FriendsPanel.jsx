import { useState } from "react";
import { Check, Clock, UserPlus, X } from "lucide-react";
import { api } from "@/lib/api";
import { useAction } from "@/hooks/useAction";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { initials } from "@/lib/format";

const Person = ({ user, children, testId }) => (
  <li data-testid={testId} className="flex items-center gap-3 py-2.5">
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[11px] font-semibold text-slate-600">{initials(user?.name)}</span>
    <div className="min-w-0 flex-1">
      <div className="truncate text-sm font-medium text-slate-900">{user?.name}</div>
      <div className="truncate text-xs text-slate-500">{user?.email}</div>
    </div>
    {children}
  </li>
);

const AddFriend = ({ onDone }) => {
  const [email, setEmail] = useState("");
  const { run, busy, fields, error } = useAction();
  const submit = async (e) => {
    e.preventDefault();
    const res = await run(() => api.post("/friends/requests", { email }), "Friend request sent");
    if (res) { setEmail(""); onDone(); }
  };
  const err = fields.email || error;
  return (
    <form onSubmit={submit} className="space-y-1.5" noValidate data-testid="add-friend-form">
      <label htmlFor="friend-email" className="text-xs font-medium text-slate-700">Add a friend by email</label>
      <div className="flex gap-2">
        <Input id="friend-email" data-testid="add-friend-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="friend@example.com" aria-invalid={!!err} className={`h-10 bg-white ${err ? "border-red-400" : ""}`} />
        <Button type="submit" data-testid="add-friend-submit" disabled={busy || !email.trim()} className="h-10 shrink-0" aria-label="Send friend request">
          <UserPlus className="h-4 w-4 sm:mr-1.5" /><span className="hidden sm:inline">Add</span>
        </Button>
      </div>
      {err && <p data-testid="add-friend-error" className="text-xs text-red-600">{err}</p>}
    </form>
  );
};

export const FriendsPanel = ({ data, onChange }) => {
  const { run, busy } = useAction();
  const respond = async (id, verb) => {
    if (await run(() => api.post(`/friends/requests/${id}/${verb}`), verb === "accept" ? "Friend added" : "Request declined")) onChange();
  };
  return (
    <div className="space-y-5" data-testid="friends-panel">
      <AddFriend onDone={onChange} />
      {data.incoming.length > 0 && (
        <div>
          <div className="eyebrow mb-1">Requests for you</div>
          <ul className="divide-y divide-border-subtle">
            {data.incoming.map((f) => (
              <Person key={f.id} user={f.user} testId={`friend-incoming-${f.id}`}>
                <Button size="icon" variant="outline" className="h-9 w-9" disabled={busy} aria-label={`Accept ${f.user?.name}`}
                  data-testid={`friend-accept-${f.id}`} onClick={() => respond(f.id, "accept")}><Check className="h-4 w-4" /></Button>
                <Button size="icon" variant="ghost" className="h-9 w-9" disabled={busy} aria-label={`Decline ${f.user?.name}`}
                  data-testid={`friend-decline-${f.id}`} onClick={() => respond(f.id, "decline")}><X className="h-4 w-4" /></Button>
              </Person>
            ))}
          </ul>
        </div>
      )}
      <div>
        <div className="eyebrow mb-1">Friends · {data.friends.length}</div>
        {data.friends.length === 0
          ? <p className="py-2 text-sm text-slate-500">No friends yet. Add someone by the email of their Individual account.</p>
          : <ul data-testid="friends-list" className="divide-y divide-border-subtle">{data.friends.map((f) => <Person key={f.id} user={f.user} testId={`friend-${f.user?.id}`} />)}</ul>}
      </div>
      {data.outgoing.length > 0 && (
        <div>
          <div className="eyebrow mb-1">Sent</div>
          <ul className="divide-y divide-border-subtle">
            {data.outgoing.map((f) => (
              <Person key={f.id} user={f.user} testId={`friend-outgoing-${f.id}`}>
                <span className="inline-flex items-center gap-1 text-xs text-slate-500"><Clock className="h-3 w-3" />Pending</span>
              </Person>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
