import { SignIn } from "@clerk/nextjs";
import { Suspense } from "react";

export default function SignInPage() {
  return (
    <div className="flex justify-center py-10">
      <Suspense fallback={<div className="h-96 w-96 animate-pulse rounded-xl bg-stone-200" />}>
        <SignIn fallbackRedirectUrl="/dashboard" />
      </Suspense>
    </div>
  );
}
