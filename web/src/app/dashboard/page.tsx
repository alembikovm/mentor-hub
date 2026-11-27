import Link from "next/link";
import { Suspense } from "react";

import { rotateInviteCode } from "@/app/actions";
import { ProgressBar } from "@/components/progress";
import { SubmissionList } from "@/components/submission-list";
import { EmptyState, PageSkeleton } from "@/components/ui";
import { api, requireMe } from "@/lib/api";
import type { Me, Mentee, Roadmap, Submission } from "@/lib/types";

import { JoinMentorForm } from "./join-form";

function Section({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function CourseCard({ course, footer }: { course: Roadmap; footer: React.ReactNode }) {
  return (
    <Link href={`/roadmaps/${course.id}`} className="card flex flex-col p-4 transition hover:border-indigo-400">
      <div className="font-medium">{course.title}</div>
      {course.description && <p className="mt-1 line-clamp-2 text-sm text-stone-600">{course.description}</p>}
      <div className="mt-auto pt-4">{footer}</div>
    </Link>
  );
}

async function MentorDashboard({ me }: { me: Me }) {
  const [courses, mentees, submissions] = await Promise.all([
    api<Roadmap[]>("/roadmaps"),
    api<Mentee[]>("/mentees"),
    api<Submission[]>("/submissions?limit=10"),
  ]);
  return (
    <div className="space-y-10">
      <div className="card flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <div className="text-sm text-stone-600">Invite code — mentees join you with it, then you choose which courses they see</div>
          <div className="mt-1 font-mono text-2xl tracking-widest">{me.invite_code}</div>
        </div>
        <form action={rotateInviteCode}>
          <button className="btn-secondary">Generate new code</button>
        </form>
      </div>

      <Section
        title={`Courses (${courses.length})`}
        action={
          <Link href="/roadmaps/new" className="btn-primary">
            New course
          </Link>
        }
      >
        {courses.length ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {courses.map((c) => (
              <CourseCard
                key={c.id}
                course={c}
                footer={
                  <div className="text-xs text-stone-500">
                    {c.topic_count} topics · {c.access_count ?? 0} mentee{c.access_count === 1 ? "" : "s"} with access
                  </div>
                }
              />
            ))}
          </div>
        ) : (
          <EmptyState>Upload your first course roadmap to get started.</EmptyState>
        )}
      </Section>

      <Section title={`Mentees (${mentees.length})`}>
        {mentees.length ? (
          <ul className="card divide-y divide-stone-100">
            {mentees.map((m) => {
              const granted = m.courses.filter((c) => c.has_access);
              return (
                <li key={m.id}>
                  <Link href={`/mentees/${m.id}`} className="flex flex-wrap items-center gap-4 px-4 py-3 hover:bg-stone-50">
                    <div className="min-w-40 flex-1">
                      <div className="text-sm font-medium">{m.name || "Unnamed"}</div>
                      <div className="text-xs text-stone-500">{m.email}</div>
                    </div>
                    <div className="flex w-full flex-col gap-2 sm:w-72">
                      {granted.length ? (
                        granted.map((c) => (
                          <div key={c.roadmap.id}>
                            <div className="truncate text-xs text-stone-600">{c.roadmap.title}</div>
                            {c.progress && <ProgressBar progress={c.progress} size="sm" />}
                          </div>
                        ))
                      ) : (
                        <span className="text-xs text-amber-700">No course access yet — open to grant</span>
                      )}
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        ) : (
          <EmptyState>No mentees yet. Share your invite code.</EmptyState>
        )}
      </Section>

      <Section title="Latest submissions">
        <SubmissionList submissions={submissions} showMentee empty="Your mentees haven't submitted anything yet." />
      </Section>
    </div>
  );
}

async function MenteeDashboard({ me }: { me: Me }) {
  const [courses, submissions] = await Promise.all([
    api<Roadmap[]>("/roadmaps"),
    api<Submission[]>("/submissions?limit=10"),
  ]);
  return (
    <div className="space-y-10">
      <Section title="My courses">
        {courses.length ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {courses.map((c) => (
              <CourseCard
                key={c.id}
                course={c}
                footer={
                  <div className="space-y-2">
                    {c.progress && <ProgressBar progress={c.progress} />}
                    {c.mentor && <div className="text-xs text-stone-500">Mentor: {c.mentor.name || c.mentor.email}</div>}
                  </div>
                }
              />
            ))}
          </div>
        ) : (
          <EmptyState>
            {me.mentors.length
              ? "Your mentor hasn't given you access to a course yet."
              : "Join a mentor with their invite code to get courses."}
          </EmptyState>
        )}
      </Section>

      <Section title="My submissions">
        <SubmissionList submissions={submissions} empty="Open a topic in a course and submit your solution." />
      </Section>

      <Section title="Mentors">
        <div className="card p-5">
          {me.mentors.length > 0 && (
            <ul className="mb-4 space-y-1 text-sm">
              {me.mentors.map((m) => (
                <li key={m.id}>
                  <span className="font-medium">{m.name || "Unnamed"}</span>
                  {m.email && <span className="ml-2 text-stone-500">{m.email}</span>}
                </li>
              ))}
            </ul>
          )}
          <div className="text-sm text-stone-600">
            {me.mentors.length ? "Join another mentor:" : "Ask your mentor for their invite code."}
          </div>
          <JoinMentorForm />
        </div>
      </Section>
    </div>
  );
}

async function Dashboard() {
  const me = await requireMe();
  return (
    <>
      <h1 className="mb-8 text-2xl font-semibold tracking-tight">
        {me.role === "mentor" ? "Mentor dashboard" : "My learning"}
      </h1>
      {me.role === "mentor" ? <MentorDashboard me={me} /> : <MenteeDashboard me={me} />}
    </>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Dashboard />
    </Suspense>
  );
}
