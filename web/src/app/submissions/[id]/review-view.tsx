import type { AiReview } from "@/lib/types";

const verdicts: Record<AiReview["verdict"], { label: string; cls: string }> = {
  correct: { label: "Correct", cls: "bg-emerald-100 text-emerald-800" },
  partially_correct: { label: "Partially correct", cls: "bg-amber-100 text-amber-800" },
  incorrect: { label: "Incorrect", cls: "bg-red-100 text-red-700" },
  off_topic: { label: "Off topic", cls: "bg-stone-200 text-stone-700" },
  unreadable: { label: "Screenshot unreadable", cls: "bg-stone-200 text-stone-700" },
};

const severity: Record<string, string> = {
  critical: "bg-red-600",
  major: "bg-amber-500",
  minor: "bg-stone-400",
};

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <div className="mb-1.5 text-sm font-medium">{title}</div>
      <ul className="list-disc space-y-1 pl-5 text-sm text-stone-700">
        {items.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
    </div>
  );
}

export function ReviewView({ review, audience }: { review: AiReview; audience: "mentor" | "mentee" }) {
  const v = verdicts[review.verdict];
  return (
    <div className="card space-y-5 p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium uppercase tracking-wide text-stone-500">AI review</span>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${v.cls}`}>{v.label}</span>
        </div>
        {review.verdict !== "unreadable" && (
          <div className="text-right">
            <span className="text-2xl font-semibold tabular-nums">{review.score}</span>
            <span className="text-sm text-stone-500">/100</span>
          </div>
        )}
      </div>

      <p className="text-sm leading-relaxed text-stone-800">{review.summary}</p>

      <List title="What's good" items={review.strengths} />

      {review.issues.length > 0 && (
        <div>
          <div className="mb-1.5 text-sm font-medium">Issues</div>
          <ul className="space-y-2">
            {review.issues.map((iss, i) => (
              <li key={i} className="rounded-lg bg-stone-50 p-3 text-sm">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${severity[iss.severity]}`} />
                  <span className="font-medium">{iss.title}</span>
                  {iss.location && <span className="font-mono text-xs text-stone-500">{iss.location}</span>}
                </div>
                <p className="mt-1 text-stone-700">{iss.detail}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <List title="Next steps" items={review.suggestions} />
      {audience === "mentor" && <List title="Worth checking yourself" items={review.questions_for_mentor} />}

      {audience === "mentor" && review.perception?.transcription && (
        <details className="text-sm">
          <summary className="cursor-pointer text-stone-500 hover:text-stone-900">
            What the model read from the screenshots
          </summary>
          <pre className="mt-2 max-h-80 overflow-auto rounded-lg bg-stone-900 p-3 font-mono text-xs text-stone-100">
            {review.perception.transcription}
          </pre>
        </details>
      )}
    </div>
  );
}
