import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { FullPageLoader } from "@/components/common/States";

export const PENDING_KEY = "arm_google_pending";

export default function AuthCallback() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const sessionId = new URLSearchParams(window.location.hash.slice(1)).get("session_id");
    window.history.replaceState(null, "", window.location.pathname);
    api.post("/auth/google/session", { session_id: sessionId })
      .then(({ data }) => {
        if (data.status === "needs_mode") {
          sessionStorage.setItem(PENDING_KEY, JSON.stringify(data));
          setUser(false);
          navigate("/auth/choose-mode", { replace: true });
        } else {
          setUser(data.user);
          navigate("/overview", { replace: true });
        }
      })
      .catch((e) => {
        setUser(false);
        navigate("/login", { replace: true, state: { error: formatApiError(e) } });
      });
  }, [navigate, setUser]);

  return <FullPageLoader />;
}
