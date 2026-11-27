"use client";

import { useState, useTransition } from "react";

import { onboard } from "@/app/actions";
import type { Role } from "@/lib/types";

const options: { role: Role; title: string; body: string }[] = [
  {
    role: "mentor",
    title: "I'm a mentor",
    body: "Upload roadmaps, invite mentees, review their solutions with AI help.",
  },
  {
    role: "mentee",
    title: "I'm a mentee",
    body: "Join your mentor, follow their roadmap, submit screenshots of your solutions.",
  },
];

export function RolePicker() {
  const [pending, start] = useTransition();
  const [chosen, setChosen] = useState<Role | null>(null);
  const [error, setError] = useState<string>();

  return (
    <>
      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {options.map((o) => (
          <button
            key={o.role}
            disabled={pending}
            onClick={() => {
              setChosen(o.role);
              start(async () => setError((await onboard(o.role))?.error));
            }}
            className="card cursor-pointer p-6 text-left transition hover:border-indigo-400 hover:shadow-sm disabled:opacity-60"
          >
            <div className="font-medium">{o.title}</div>
            <p className="mt-2 text-sm text-stone-600">{o.body}</p>
            {pending && chosen === o.role && <p className="mt-3 text-sm text-indigo-600">Setting up…</p>}
          </button>
        ))}
      </div>
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
    </>
  );
}
