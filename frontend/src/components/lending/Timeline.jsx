import { fmt } from "@/lib/format";

const LABELS = {
  created: "created the handover", edited: "edited the handover", rejected: "rejected", completed: "marked it completed",
  attachment_added: "attached a file",
  requested: "requested", offered: "offered to lend", accepted: "accepted", declined: "declined", cancelled: "cancelled",
  repayment_recorded: "recorded a repayment of", repayment_confirmed: "confirmed a repayment of",
  repayment_disputed: "disputed a repayment of", repaid: "marked the loan as fully repaid",
  submitted: "submitted a request for", approved: "approved", rejected: "rejected",
  created: "created this", edited: "edited this", completed: "marked it completed", attachment_added: "attached",
  suggested: "suggested a new time", suggestion_accepted: "accepted the suggested time", suggestion_dismissed: "dismissed the suggested time",
};

const when = (iso) => new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

export const Timeline = ({ items, testId = "entry-timeline" }) => (
  <ol data-testid={testId} className="relative space-y-4 border-l border-border pl-5">
    {[...items].reverse().map((h, i) => (
      <li key={`${h.at}-${i}`} data-testid={`${testId}-item-${h.action}`} className="relative">
        <span className="absolute -left-[25px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-indigo-500 ring-1 ring-indigo-200" />
        <p className="text-sm text-slate-700">
          <span className="font-medium text-slate-900">{h.actor_name || "Someone"}</span> {LABELS[h.action] || h.action}
          {h.amount != null && <span className="num font-medium text-slate-900"> {fmt(h.amount)} credits</span>}
          {h.note && <span className="block text-xs text-slate-500">“{h.note}”</span>}
        </p>
        <p className="text-xs text-slate-400">{when(h.at)}</p>
      </li>
    ))}
  </ol>
);
