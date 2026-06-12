import { CheckCircle2, Loader2, Clock, XCircle } from "lucide-react";

const MAP = {
  completed: { cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", icon: CheckCircle2, label: "Completed" },
  processing: { cls: "text-blue-400 bg-blue-400/10 border-blue-400/20", icon: Loader2, label: "Processing" },
  queued: { cls: "text-amber-400 bg-amber-500/10 border-amber-500/20", icon: Clock, label: "Queued" },
  failed: { cls: "text-red-400 bg-red-500/10 border-red-500/20", icon: XCircle, label: "Failed" },
  ready: { cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", icon: CheckCircle2, label: "Ready" },
};

export const StatusBadge = ({ status }) => {
  const c = MAP[status] || MAP.queued;
  const Icon = c.icon;
  const spin = status === "processing";
  return (
    <span
      data-testid={`status-badge-${status}`}
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${c.cls}`}
    >
      <Icon size={12} className={spin ? "animate-spin" : ""} />
      {c.label}
    </span>
  );
};

export default StatusBadge;
