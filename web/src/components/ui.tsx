import type { SubmissionStatus } from "@/lib/types";

export function PageSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-8 w-64 animate-pulse rounded bg-stone-200" />
      <div className="h-32 animate-pulse rounded-xl bg-stone-200" />
      <div className="h-32 animate-pulse rounded-xl bg-stone-200" />
    </div>
  );
}

export function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-stone-300 p-6 text-center text-sm text-stone-500">
      {children}
    </div>
  );
}

const statusStyles: Record<SubmissionStatus, string> = {
  pending: "bg-stone-100 text-stone-700",
  analyzing: "bg-amber-100 text-amber-800",
  done: "bg-emerald-100 text-emerald-800",
  failed: "bg-red-100 text-red-700",
};

const statusLabels: Record<SubmissionStatus, string> = {
  pending: "Queued",
  analyzing: "Analyzing…",
  done: "Reviewed",
  failed: "Failed",
};

export function StatusBadge({ status }: { status: SubmissionStatus }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusStyles[status]}`}>
      {statusLabels[status]}
    </span>
  );
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
