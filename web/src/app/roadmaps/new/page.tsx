import { Suspense } from "react";

import { requireMe } from "@/lib/api";

import { RoadmapUploader } from "./uploader";

async function Guard() {
  await requireMe("mentor");
  return <RoadmapUploader />;
}

export default function NewRoadmapPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">New course</h1>
      <p className="mt-2 max-w-2xl text-sm text-stone-600">
        Upload the course roadmap: paste Markdown or JSON, or pick a <code>.md</code> / <code>.json</code> file. Headings and nested
        bullet lists become topics and subtopics; text under an item becomes its description.
      </p>
      <Suspense fallback={null}>
        <Guard />
      </Suspense>
    </div>
  );
}
