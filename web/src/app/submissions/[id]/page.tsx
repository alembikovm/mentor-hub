import Link from "next/link";
import { Suspense } from "react";

import { reanalyze } from "@/app/actions";
import { PageSkeleton, StatusBadge, formatDate } from "@/components/ui";
import { apiOr404, requireMe } from "@/lib/api";
import type { Submission } from "@/lib/types";

import { MentorCommentForm } from "./comment-form";
import { ReviewView } from "./review-view";
import { StatusPoller } from "./status-poller";

async function SubmissionDetail({ params }: { params: PageProps<"/submissions/[id]">["params"] }) {
  const { id } = await params;
  const me = await requireMe();
  const sub = await apiOr404<Submission>(`/submissions/${id}`);
  const running = sub.status === "pending" || sub.status === "analyzing";
  const isMentor = me.role === "mentor";

  return (
    <div className="space-y-8">
      {running && <StatusPoller />}
      <div>
        <div className="text-sm text-stone-500">
          {sub.roadmap_id ? (
            <Link href={`/roadmaps/${sub.roadmap_id}`} className="hover:text-stone-900">
              {sub.topic_path.slice(0, -1).join(" / ") || "Roadmap"}
            </Link>
          ) : null}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{sub.topic_title}</h1>
          <StatusBadge status={sub.status} />
        </div>
        <div className="mt-1 text-sm text-stone-500">
          {isMentor && <>{sub.mentee?.name || sub.mentee?.email || "Mentee"} · </>}
          Submitted {formatDate(sub.created_at)}
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <section className="space-y-4">
          {sub.note && (
            <div className="card p-4 text-sm">
              <div className="mb-1 font-medium">Note from mentee</div>
              <p className="whitespace-pre-line text-stone-700">{sub.note}</p>
            </div>
          )}
          {sub.images.map((img, i) => (
            <a
              key={img.id}
              href={`/api/backend/submissions/${sub.id}/images/${img.id}`}
              target="_blank"
              className="block overflow-hidden rounded-lg border border-stone-200 bg-white"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/api/backend/submissions/${sub.id}/images/${img.id}`}
                alt={`Screenshot ${i + 1}`}
                className="w-full"
              />
            </a>
          ))}
        </section>

        <section className="space-y-6">
          {running && (
            <div className="card flex items-center gap-3 p-5 text-sm text-stone-600">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
              The AI reviewer is reading the screenshots…
            </div>
          )}
          {sub.status === "failed" && (
            <div className="card space-y-3 border-red-200 p-5 text-sm">
              <div className="font-medium text-red-700">Analysis failed</div>
              <p className="text-stone-600">{sub.error}</p>
              <form action={reanalyze.bind(null, sub.id)}>
                <button className="btn-secondary">Retry analysis</button>
              </form>
            </div>
          )}
          {sub.status === "done" && sub.ai_review && (
            <>
              <ReviewView review={sub.ai_review} audience={isMentor ? "mentor" : "mentee"} />
              <form action={reanalyze.bind(null, sub.id)}>
                <button className="text-sm text-stone-500 hover:text-stone-900 hover:underline">
                  Re-run AI review
                </button>
              </form>
            </>
          )}

          <div className="card p-5">
            <div className="mb-2 font-medium">Mentor feedback</div>
            {isMentor ? (
              <MentorCommentForm submissionId={sub.id} initial={sub.mentor_comment ?? ""} />
            ) : sub.mentor_comment ? (
              <p className="whitespace-pre-line text-sm text-stone-700">{sub.mentor_comment}</p>
            ) : (
              <p className="text-sm text-stone-500">Your mentor hasn&apos;t replied yet.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export default function Page(props: PageProps<"/submissions/[id]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <SubmissionDetail params={props.params} />
    </Suspense>
  );
}
