import axios from "axios";

export const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
});

const NO_REFRESH = ["/auth/login", "/auth/refresh", "/auth/register", "/auth/logout", "/demo/login"];
let refreshing = null;

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const cfg = error.config || {};
    const skip = NO_REFRESH.some((p) => (cfg.url || "").startsWith(p));
    if (error.response?.status === 401 && !cfg._retry && !skip) {
      cfg._retry = true;
      try {
        refreshing = refreshing || api.post("/auth/refresh");
        await refreshing;
        refreshing = null;
        return api(cfg);
      } catch (e) {
        refreshing = null;
        window.dispatchEvent(new Event("auth:expired"));
      }
    }
    return Promise.reject(error);
  }
);

export function formatApiError(err) {
  const detail = err?.response?.data?.detail;
  if (detail == null) return err?.message === "Network Error" ? "Can't reach the server. Check your connection." : "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => e?.msg || JSON.stringify(e)).join(" ");
  if (typeof detail.message === "string") return detail.message;
  return String(detail);
}

export function fieldErrors(err) {
  const detail = err?.response?.data?.detail;
  return detail && typeof detail === "object" && !Array.isArray(detail) ? detail.fields || {} : {};
}
