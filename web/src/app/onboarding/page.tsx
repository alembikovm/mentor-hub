import { redirect } from "next/navigation";
import { Suspense } from "react";

import { api } from "@/lib/api";
import type { Me } from "@/lib/types";

import { RolePicker } from "./role-picker";

async function Onboarding() {
  const me = await api<Me>("/me");
  if (me.role) redirect("/dashboard");
  return <RolePicker />;
}

export default function OnboardingPage() {
  return (
    <div className="mx-auto max-w-2xl py-6">
      <h1 className="text-2xl font-semibold tracking-tight">How will you use Mentor Hub?</h1>
      <p className="mt-2 text-stone-600">You can&apos;t change this later, so pick the one that fits.</p>
      <Suspense fallback={<div className="mt-8 h-40 animate-pulse rounded-xl bg-stone-200" />}>
        <Onboarding />
      </Suspense>
    </div>
  );
}
