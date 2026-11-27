import type { Progress } from "@/lib/types";

export function ProgressBar({ progress, size = "md" }: { progress: Progress; size?: "sm" | "md" }) {
  const completed = !!progress.completed_at;
  return (
    <div className="w-full">
      <div className={`overflow-hidden rounded-full bg-stone-200 ${size === "sm" ? "h-1.5" : "h-2"}`}>
        <div
          className={`h-full rounded-full transition-all ${completed ? "bg-emerald-500" : "bg-indigo-500"}`}
          style={{ width: `${progress.percent}%` }}
        />
      </div>
      <div className="mt-1 flex items-center justify-between text-xs text-stone-500">
        <span>
          {progress.done}/{progress.total} topics
        </span>
        {completed ? (
          <span className="font-medium text-emerald-700">Course completed</span>
        ) : (
          <span className="tabular-nums">{progress.percent}%</span>
        )}
      </div>
    </div>
  );
}
