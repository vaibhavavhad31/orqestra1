const nf = new Intl.NumberFormat("en-US");

export const fmt = (n) => nf.format(Math.round(n || 0));

export const fmtCompact = (n) =>
  new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(n || 0);

export const fmtDay = (iso) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });

export const fmtRange = (start, end) => `${fmtDay(start)} – ${fmtDay(end)}`;

export const timeAgo = (iso) => {
  const s = Math.max(0, (Date.now() - new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  if (s < 86400 * 7) return `${Math.floor(s / 86400)} d ago`;
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

export const initials = (name = "") =>
  name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");

export const HEALTH = {
  near_limit: { label: "Near limit", tone: "warning" },
  underutilised: { label: "Underutilised", tone: "info" },
  healthy: { label: "Healthy", tone: "success" },
  unallocated: { label: "No allocation", tone: "neutral" },
};
