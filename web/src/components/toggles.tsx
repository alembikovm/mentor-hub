"use client";

import { useOptimistic, useState, useTransition } from "react";

import { setCourseAccess, setDone } from "@/app/actions";

export function DoneButton({
  roadmapId,
  nodeId,
  done,
  menteeId,
  labels = ["Mark as done", "Done — undo"],
}: {
  roadmapId: string;
  nodeId: string | null;
  done: boolean;
  menteeId?: string;
  labels?: [string, string];
}) {
  const [pending, start] = useTransition();
  const [optimistic, setOptimistic] = useOptimistic(done);
  const [error, setError] = useState<string>();

  return (
    <div className="flex items-center gap-2">
      <button
        disabled={pending}
        onClick={() =>
          start(async () => {
            setOptimistic(!done);
            setError((await setDone(roadmapId, nodeId, !done, menteeId))?.error);
          })
        }
        className={optimistic ? "btn border border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100" : "btn-primary"}
      >
        {optimistic ? `✓ ${labels[1]}` : labels[0]}
      </button>
      {error && <span className="text-sm text-red-600">{error}</span>}
    </div>
  );
}

/** Compact checkbox used in topic lists. */
export function DoneCheckbox({
  roadmapId,
  nodeId,
  done,
  partial,
  menteeId,
}: {
  roadmapId: string;
  nodeId: string;
  done: boolean;
  partial: boolean;
  menteeId?: string;
}) {
  const [pending, start] = useTransition();
  const [optimistic, setOptimistic] = useOptimistic(done);
  return (
    <button
      aria-label={optimistic ? "Mark as not done" : "Mark as done"}
      title={optimistic ? "Mark as not done" : "Mark as done (with all subtopics)"}
      disabled={pending}
      onClick={() =>
        start(async () => {
          setOptimistic(!done);
          await setDone(roadmapId, nodeId, !done, menteeId);
        })
      }
      className={`flex h-5 w-5 shrink-0 cursor-pointer items-center justify-center rounded border-2 text-[11px] transition ${
        optimistic
          ? "border-emerald-500 bg-emerald-500 text-white"
          : partial
            ? "border-indigo-400 bg-indigo-50 text-indigo-500"
            : "border-stone-300 hover:border-stone-500"
      }`}
    >
      {optimistic ? "✓" : partial ? "–" : ""}
    </button>
  );
}

export function AccessSwitch({
  roadmapId,
  menteeId,
  granted,
}: {
  roadmapId: string;
  menteeId: string;
  granted: boolean;
}) {
  const [pending, start] = useTransition();
  const [optimistic, setOptimistic] = useOptimistic(granted);
  const [error, setError] = useState<string>();
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm select-none">
      <button
        role="switch"
        aria-checked={optimistic}
        disabled={pending}
        onClick={() =>
          start(async () => {
            setOptimistic(!granted);
            setError((await setCourseAccess(roadmapId, menteeId, !granted))?.error);
          })
        }
        className={`relative h-5 w-9 cursor-pointer rounded-full transition ${optimistic ? "bg-indigo-600" : "bg-stone-300"}`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${optimistic ? "left-[18px]" : "left-0.5"}`}
        />
      </button>
      <span className={optimistic ? "text-stone-800" : "text-stone-500"}>{optimistic ? "Has access" : "No access"}</span>
      {error && <span className="text-red-600">{error}</span>}
    </label>
  );
}
