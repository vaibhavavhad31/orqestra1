import {
  LayoutDashboard, ListTree, Activity, PieChart, ArrowLeftRight, GitPullRequestArrow, CalendarRange,
  Bell, FileBarChart, Users, Blocks, Settings,
} from "lucide-react";

export const MODULES = [
  { id: "overview", label: "Overview", path: "/overview", icon: LayoutDashboard, phase: 1,
    purpose: "Your credit position at a glance." },
  { id: "tasks", label: "Tasks", path: "/tasks", icon: ListTree, phase: 5, live: true,
    purpose: "Break goals into sub-tasks, match them to people and AI tools, and plan when they run." },
  { id: "usage", label: "AI Usage", path: "/usage", icon: Activity, phase: 1,
    purpose: "Credits consumed by provider and over time." },
  { id: "allocation", label: "Resource Allocation", path: "/allocation", icon: PieChart, phase: 2, live: true,
    purpose: "Plan budgets, rebalance allocations and handle resource requests.",
    planned: ["Org, department and employee allocations", "Underutilised capacity detection", "Request and approve extra credits"] },
  { id: "lending", label: "Credit Lending", path: "/lending", icon: ArrowLeftRight, phase: 2, live: true,
    purpose: "Lend to and borrow from friends, tracked as obligations only.",
    planned: ["Request, lend, accept or decline", "Outstanding balances and repayments", "No provider credits ever move"] },
  { id: "handover", label: "Task Handover", path: "/handover", icon: GitPullRequestArrow, phase: 3, live: true,
    purpose: "Pass work on with context so it keeps moving when credits run out.",
    planned: ["Task context, completed and pending work", "Attach supporting documents", "Status flow without exposing chat history"] },
  { id: "planner", label: "Session Planner", path: "/planner", icon: CalendarRange, phase: 3, live: true,
    purpose: "Plan AI-heavy work sessions around the capacity you have.",
    planned: ["Personal session planning", "Estimated credits per session", "Team coordination view for managers"] },
  { id: "notifications", label: "Notifications", path: "/notifications", icon: Bell, phase: 4, live: true,
    purpose: "Updates on lending, requests, handovers and sessions.",
    planned: ["In-app inbox", "Triggered by requests and handovers", "Read and unread states"] },
  { id: "reports", label: "Reports", path: "/reports", icon: FileBarChart, phase: 4, live: true,
    purpose: "Usage, expenditure and utilisation reports.",
    planned: ["Expenditure in credits", "Utilisation trends", "CSV export"] },
  { id: "team", label: "Team", path: "/team", icon: Users, phase: 4, live: true,
    purpose: "Manage people, roles and departments.",
    planned: ["Invite and edit users", "Assign roles and departments", "Team view for managers"] },
  { id: "integrations", label: "Integrations", path: "/integrations", icon: Blocks, phase: 4, live: true,
    purpose: "The provider registry and future connectors.",
    planned: ["Provider registry", "Simulated / not connected status", "Extensible connector structure"] },
  { id: "settings", label: "Settings", path: "/settings", icon: Settings, phase: 4, live: true,
    purpose: "Profile, organisation settings and preferences.",
    planned: ["Profile details", "Organisation settings (Admin)", "Preferences"],
    individual: { purpose: "Profile and personal preferences.", planned: ["Profile details", "Personal credit settings", "Preferences"] } },
];

export const moduleById = (id) => MODULES.find((m) => m.id === id);
export const moduleByPath = (path) => MODULES.find((m) => path.startsWith(m.path));
