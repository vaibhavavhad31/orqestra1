import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import { ModuleRoute, PublicOnly, RequireAuth } from "@/components/shell/Guards";
import AppShell from "@/components/shell/AppShell";
import { MODULES } from "@/lib/modules";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import ChooseMode from "@/pages/ChooseMode";
import AuthCallback from "@/pages/AuthCallback";
import Overview from "@/pages/Overview";
import Tasks from "@/pages/Tasks";
import Usage from "@/pages/Usage";
import CreditLending from "@/pages/CreditLending";
import Allocation from "@/pages/Allocation";
import Handover from "@/pages/Handover";
import Planner from "@/pages/Planner";
import Notifications from "@/pages/Notifications";
import Reports from "@/pages/Reports";
import Team from "@/pages/Team";
import Integrations from "@/pages/Integrations";
import Settings from "@/pages/Settings";
import Placeholder from "@/pages/Placeholder";
import NotFound from "@/pages/NotFound";

const PAGES = { overview: <Overview />, tasks: <Tasks />, usage: <Usage />, lending: <CreditLending />, allocation: <Allocation />, handover: <Handover />, planner: <Planner />,
  notifications: <Notifications />, reports: <Reports />, team: <Team />, integrations: <Integrations />, settings: <Settings /> };

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/overview" replace />} />
      <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/signup" element={<PublicOnly><Signup /></PublicOnly>} />
      <Route path="/auth/choose-mode" element={<ChooseMode />} />
      <Route element={<RequireAuth><AppShell /></RequireAuth>}>
        {MODULES.map((m) => (
          <Route key={m.id} path={m.path} element={<ModuleRoute id={m.id}>{PAGES[m.id] || <Placeholder id={m.id} />}</ModuleRoute>} />
        ))}
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRouter />
        <Toaster position="bottom-right" />
      </AuthProvider>
    </BrowserRouter>
  );
}
