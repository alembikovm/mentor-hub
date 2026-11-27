"use client";

import { useEffect, useState, useTransition } from "react";

import { createRoadmap } from "@/app/actions";
import type { PreviewNode, RoadmapPreview } from "@/lib/types";

const EXAMPLE = `# Frontend Developer
A path from the basics to a first production app.

## HTML & CSS
- Semantic HTML
  - Forms and validation
  - Accessibility basics
- Layout
  - Flexbox
  - Grid

## JavaScript
### Language core
- Closures
  Explain and build a counter factory.
- Promises and async/await
### DOM
- Events and delegation

## React
- Components and props
- State and effects
`;

function Tree({ nodes, depth = 0 }: { nodes: PreviewNode[]; depth?: number }) {
  return (
    <ul className={depth ? "ml-4 border-l border-stone-200 pl-3" : ""}>
      {nodes.map((n, i) => (
        <li key={i} className="py-0.5">
          <span className="text-sm">{n.title}</span>
          {n.children.length > 0 && <Tree nodes={n.children} depth={depth + 1} />}
        </li>
      ))}
    </ul>
  );
}

export function RoadmapUploader() {
  const [source, setSource] = useState(EXAMPLE);
  const [title, setTitle] = useState("");
  const [preview, setPreview] = useState<RoadmapPreview | null>(null);
  const [previewError, setPreviewError] = useState<string>();
  const [saveError, setSaveError] = useState<string>();
  const [saving, startSave] = useTransition();

  useEffect(() => {
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      try {
        const res = await fetch("/api/backend/roadmaps/preview", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ source, title: title || null }),
          signal: ctrl.signal,
        });
        const body = await res.json();
        if (!res.ok) {
          setPreview(null);
          setPreviewError(typeof body.detail === "string" ? body.detail : "Can't parse roadmap");
        } else {
          setPreview(body);
          setPreviewError(undefined);
        }
      } catch (e) {
        if ((e as Error).name !== "AbortError") setPreviewError("Preview unavailable");
      }
    }, 400);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [source, title]);

  async function onFile(file: File | undefined) {
    if (file) setSource(await file.text());
  }

  return (
    <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <div>
          <label className="label" htmlFor="title">
            Title <span className="font-normal text-stone-500">(optional — defaults to the first # heading)</span>
          </label>
          <input id="title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <label className="label mb-0" htmlFor="source">
              Roadmap
            </label>
            <label className="cursor-pointer text-sm text-indigo-600 hover:underline">
              Load file…
              <input
                type="file"
                accept=".md,.markdown,.txt,.json"
                className="hidden"
                onChange={(e) => onFile(e.target.files?.[0])}
              />
            </label>
          </div>
          <textarea
            id="source"
            className="input h-[28rem] font-mono text-xs leading-relaxed"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            spellCheck={false}
          />
        </div>
        <div className="flex items-center gap-3">
          <button
            className="btn-primary"
            disabled={saving || !preview}
            onClick={() => startSave(async () => setSaveError((await createRoadmap(source, title))?.error))}
          >
            {saving ? "Saving…" : "Create course"}
          </button>
          {saveError && <p className="text-sm text-red-600">{saveError}</p>}
        </div>
      </div>

      <aside className="card h-fit p-4 lg:sticky lg:top-6">
        <div className="mb-3 text-sm font-medium">Preview</div>
        {previewError && <p className="text-sm text-red-600">{previewError}</p>}
        {preview && (
          <>
            <div className="font-semibold">{preview.title}</div>
            <div className="mb-3 text-xs text-stone-500">{preview.topic_count} topics</div>
            <div className="max-h-[28rem] overflow-auto">
              <Tree nodes={preview.children} />
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
