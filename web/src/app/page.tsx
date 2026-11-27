import Link from "next/link";

const features = [
  {
    title: "Nested roadmaps",
    body: "Upload a roadmap as Markdown or JSON. Topics nest as deep as you need, and every subtopic gets its own page.",
  },
  {
    title: "Mentor ↔ mentee",
    body: "Mentees join with your invite code and see your roadmaps. You see everything they submit.",
  },
  {
    title: "Screenshot review",
    body: "Mentees attach screenshots of their solution. A vision model transcribes and grades it against the topic before you look.",
  },
];

export default function Home() {
  return (
    <div className="py-10">
      <h1 className="max-w-2xl text-4xl font-semibold tracking-tight sm:text-5xl">
        Guide mentees through your roadmap. Review their work in seconds.
      </h1>
      <p className="mt-4 max-w-xl text-lg text-stone-600">
        Share a structured learning path, collect solutions as screenshots, and get an AI first pass
        on every submission.
      </p>
      <div className="mt-8 flex gap-3">
        <Link href="/dashboard" className="btn-primary">
          Open dashboard
        </Link>
        <Link href="/sign-up" className="btn-secondary">
          Create account
        </Link>
      </div>
      <div className="mt-16 grid gap-4 sm:grid-cols-3">
        {features.map((f) => (
          <div key={f.title} className="card p-5">
            <h2 className="font-medium">{f.title}</h2>
            <p className="mt-2 text-sm text-stone-600">{f.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
