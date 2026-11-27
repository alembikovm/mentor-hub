"use client";

import { useActionState } from "react";

import { saveMentorComment } from "@/app/actions";

export function MentorCommentForm({ submissionId, initial }: { submissionId: string; initial: string }) {
  const [state, action, pending] = useActionState(saveMentorComment.bind(null, submissionId), undefined);
  return (
    <form action={action} className="space-y-3">
      <textarea
        name="mentor_comment"
        defaultValue={initial}
        className="input h-32"
        placeholder="Your feedback for the mentee. Use the AI review as a starting point."
      />
      <div className="flex items-center gap-3">
        <button className="btn-primary" disabled={pending}>
          {pending ? "Saving…" : "Save feedback"}
        </button>
        {state?.ok && <span className="text-sm text-emerald-700">Saved</span>}
        {state?.error && <span className="text-sm text-red-600">{state.error}</span>}
      </div>
    </form>
  );
}
