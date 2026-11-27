"use client";

import { useActionState } from "react";

import { joinMentor } from "@/app/actions";

export function JoinMentorForm() {
  const [state, action, pending] = useActionState(joinMentor, undefined);
  return (
    <form action={action} className="mt-4 flex gap-2">
      <input
        name="invite_code"
        required
        minLength={4}
        placeholder="e.g. K3XQ9A2B"
        className="input font-mono uppercase"
        autoComplete="off"
      />
      <button className="btn-primary" disabled={pending}>
        {pending ? "Joining…" : "Join"}
      </button>
      {state?.error && <p className="self-center text-sm text-red-600">{state.error}</p>}
    </form>
  );
}
