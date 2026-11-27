"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

const MAX_FILES = 6;
const MAX_MB = 10;
const TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];

export function SubmissionForm({ nodeId }: { nodeId: string }) {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string>();
  const [sending, setSending] = useState(false);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const previews = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);
  useEffect(() => () => previews.forEach(URL.revokeObjectURL), [previews]);

  function add(list: FileList | File[] | null) {
    if (!list) return;
    const incoming = Array.from(list);
    const bad = incoming.find((f) => !TYPES.includes(f.type) || f.size > MAX_MB * 1024 * 1024);
    if (bad) {
      setError(`${bad.name || "Image"}: PNG/JPEG/WEBP/GIF up to ${MAX_MB} MB`);
      return;
    }
    setError(undefined);
    setFiles((prev) => [...prev, ...incoming].slice(0, MAX_FILES));
  }

  // Paste screenshots straight from the clipboard.
  useEffect(() => {
    function onPaste(e: ClipboardEvent) {
      const imgs = Array.from(e.clipboardData?.files ?? []).filter((f) => f.type.startsWith("image/"));
      if (imgs.length) add(imgs);
    }
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!files.length) return setError("Attach at least one screenshot");
    setSending(true);
    setError(undefined);
    const form = new FormData();
    form.set("node_id", nodeId);
    form.set("note", note);
    files.forEach((f, i) => form.append("images", f, f.name || `screenshot-${i + 1}.png`));
    try {
      const res = await fetch("/api/backend/submissions", { method: "POST", body: form });
      const body = await res.json();
      if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Upload failed");
      router.push(`/submissions/${body.id}`);
    } catch (err) {
      setError((err as Error).message);
      setSending(false);
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-4 p-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          add(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-8 text-center text-sm transition ${
          dragging ? "border-indigo-400 bg-indigo-50" : "border-stone-300 hover:border-stone-400"
        }`}
      >
        <span className="font-medium">Drop screenshots here, click to choose, or paste (Ctrl+V)</span>
        <span className="mt-1 text-xs text-stone-500">
          Up to {MAX_FILES} images · code, terminal output, the rendered UI
        </span>
        <input
          ref={inputRef}
          type="file"
          accept={TYPES.join(",")}
          multiple
          className="hidden"
          onChange={(e) => {
            add(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {files.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {files.map((f, i) => (
            <div key={i} className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={previews[i]} alt="" className="h-24 w-36 rounded-md border object-cover" />
              <button
                type="button"
                onClick={() => setFiles(files.filter((_, j) => j !== i))}
                className="absolute -right-2 -top-2 h-6 w-6 cursor-pointer rounded-full bg-stone-900 text-xs text-white"
                aria-label="Remove"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      <textarea
        className="input h-20"
        placeholder="Anything the reviewer should know? (optional)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        maxLength={5000}
      />
      <div className="flex items-center gap-3">
        <button className="btn-primary" disabled={sending || !files.length}>
          {sending ? "Uploading…" : "Submit for review"}
        </button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </form>
  );
}
