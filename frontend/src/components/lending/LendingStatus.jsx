import { AlarmClock } from "lucide-react";
import { StatusPill } from "@/components/common/StatusPill";

const STATUS = {
  pending: ["Pending", "warning"], active: ["Active", "accent"], repaid: ["Repaid", "success"],
  declined: ["Declined", "neutral"], cancelled: ["Cancelled", "neutral"],
  awaiting_confirmation: ["Awaiting confirmation", "warning"], confirmed: ["Confirmed", "success"], disputed: ["Disputed", "danger"],
};

export const LendingStatus = ({ status, testId }) => {
  const [label, tone] = STATUS[status] || [status, "neutral"];
  return <StatusPill tone={tone} testId={testId}>{label}</StatusPill>;
};

export const OverdueBadge = ({ testId }) => (
  <StatusPill tone="danger" testId={testId}><AlarmClock className="mr-1 h-3 w-3" />Overdue</StatusPill>
);
