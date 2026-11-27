import Link from "next/link";
import { Suspense } from "react";

import { removeMentee } from "@/app/actions";
import { ProgressBar } from "@/components/progress";
import { SubmissionList } from "@/components/submission-list";
import { AccessSwitch } from "@/components/toggles";
import { EmptyState, PageSkeleton, formatDate } from "@/components/ui";
import { api, apiOr404, requireMe } from "@/lib/api";
import type { Mentee, Submission } from "@/lib/types";

async function MenteeDetail({ params }: { params: PageProps<"/mentees/[id]">["params"] }) {
  const { id } = await params;
  await requireMe("mentor");
  const [mentee, submissions] = await Promise.all([
    apiOr404<Mentee>(`/mentees/${id}`),
    api<Submission[]>(`/submissions?mentee_id=${id}&limit=20`),
  ]);

  return (
    <div className="space-y-10">
      <div>
        <Link href="/dashboard" className="text-sm text-stone-500 hover:text-stone-900">
          ← Dashboard
        </Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{mentee.name || "Unnamed mentee"}</h1>
            <p className="mt-1 text-sm text-stone-500">
              {mentee.email && <>{mentee.email} · </>}joined {formatDate(mentee.joined_at)}
            </p>
          </div>
          <form action={removeMentee.bind(null, mentee.id)}>
            <button className="btn-danger">Remove mentee</button>
          </form>
        </div>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Course access & progress</h2>
        {mentee.courses.length ? (
          <ul className="card divide-y divide-stone-100">
            {mentee.courses.map(({ roadmap, has_access, progress }) => (
              <li key={roadmap.id} className="flex flex-wrap items-center gap-4 px-4 py-4">
                <div className="min-w-48 flex-1">
                  <div className="font-medium">{roadmap.title}</div>
                  <div className="text-xs text-stone-500">{roadmap.topic_count} topics</div>
                </div>
                <div className="w-full sm:w-56">
                  {has_access && progress ? (
                    <ProgressBar progress={progress} />
                  ) : (
                    <span className="text-xs text-stone-400">Progress appears once access is granted</span>
                  )}
                </div>
                <AccessSwitch roadmapId={roadmap.id} menteeId={mentee.id} granted={has_access} />
                {has_access && (
                  <Link href={`/roadmaps/${roadmap.id}?mentee=${mentee.id}`} className="btn-secondary">
                    Open progress
                  </Link>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>You have no courses yet.</EmptyState>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Submissions</h2>
        <SubmissionList submissions={submissions} empty="No submissions yet." />
      </section>
    </div>
  );
}

export default function Page(props: PageProps<"/mentees/[id]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <MenteeDetail params={props.params} />
    </Suspense>
  );
}
