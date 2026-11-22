import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { FullPageLoader } from "@/components/common/States";
import AccessDenied from "@/pages/AccessDenied";
import SetPassword from "@/pages/SetPassword";

export const RequireAuth = ({ children }) => {
  const { user } = useAuth();
  const location = useLocation();
  if (user === null) return <FullPageLoader />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (user.must_change_password) return <SetPassword />;
  return children;
};

export const PublicOnly = ({ children }) => {
  const { user } = useAuth();
  if (user === null) return <FullPageLoader />;
  if (user) return <Navigate to="/overview" replace />;
  return children;
};

export const ModuleRoute = ({ id, children }) => {
  const { user } = useAuth();
  if (!user.allowed_modules.includes(id)) return <AccessDenied moduleId={id} />;
  return children;
};
