import Link from "next/link";

import type { Submission } from "@/lib/types";

import { EmptyState, StatusBadge, formatDate } from "./ui";

const verdictLabels: Record<string, string> = {
  correct: "Correct",
  partially_correct: "Partially correct",
  incorrect: "Incorrect",
  off_topic: "Off topic",
  unreadable: "Unreadable",
};

export function SubmissionList({
  submissions,
  showMentee = false,
  showTopic = true,
  empty = "No submissions yet.",
}: {
  submissions: Submission[];
  showMentee?: boolean;
  showTopic?: boolean;
  empty?: string;
}) {
  if (!submissions.length) return <EmptyState>{empty}</EmptyState>;
  return (
    <ul className="card divide-y divide-stone-100">
      {submissions.map((s) => (
        <li key={s.id}>
          <Link href={`/submissions/${s.id}`} className="flex items-center gap-4 px-4 py-3 hover:bg-stone-50">
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">
                {showTopic ? s.topic_title : s.note || "Submission"}
              </div>
              <div className="mt-0.5 text-xs text-stone-500">
                {showMentee && <>{s.mentee?.name || s.mentee?.email || "Mentee"} · </>}
                {formatDate(s.created_at)} · {s.images.length} screenshot{s.images.length === 1 ? "" : "s"}
              </div>
            </div>
            {s.ai_review && s.status === "done" && (
              <span className="hidden text-xs text-stone-600 sm:inline">
                {verdictLabels[s.ai_review.verdict]} · {s.ai_review.score}/100
              </span>
            )}
            {s.mentor_comment && <span className="text-xs text-indigo-600">Mentor replied</span>}
            <StatusBadge status={s.status} />
          </Link>
        </li>
      ))}
    </ul>
  );
}
