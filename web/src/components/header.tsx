import { Show, SignInButton, SignUpButton, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { Suspense } from "react";

export function Header() {
  return (
    <header className="border-b border-stone-200 bg-white">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="font-semibold tracking-tight">
          Mentor<span className="text-indigo-600">Hub</span>
        </Link>
        <Suspense fallback={<div className="h-8 w-32" />}>
          <nav className="flex items-center gap-3 text-sm">
          <Show when="signed-in">
            <Link href="/dashboard" className="text-stone-600 hover:text-stone-900">
              Dashboard
            </Link>
            <UserButton />
          </Show>
          <Show when="signed-out">
            <SignInButton>
              <button className="btn-secondary">Sign in</button>
            </SignInButton>
            <SignUpButton>
              <button className="btn-primary">Get started</button>
            </SignUpButton>
          </Show>
          </nav>
        </Suspense>
      </div>
    </header>
  );
}
