import { StatusPill } from "@/components/common/StatusPill";

const STATUS = { pending: "warning", accepted: "accent", completed: "success", rejected: "danger", cancelled: "neutral" };
const PRIORITY = { low: "info", medium: "neutral", high: "warning", urgent: "danger" };

export const HandoverStatus = ({ status, testId }) => <StatusPill tone={STATUS[status]} testId={testId}>{status}</StatusPill>;
export const PriorityPill = ({ priority }) => <StatusPill tone={PRIORITY[priority]}>{priority} priority</StatusPill>;
