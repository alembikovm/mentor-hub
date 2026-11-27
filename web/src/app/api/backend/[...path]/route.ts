import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

/**
 * Same-origin proxy to the FastAPI backend for browser requests
 * (screenshot uploads, image downloads, roadmap preview). Adds the Clerk token.
 */
async function forward(req: NextRequest, ctx: RouteContext<"/api/backend/[...path]">) {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return Response.json({ detail: "Unauthorized" }, { status: 401 });

  const { path } = await ctx.params;
  const url = `${API_URL}/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`;

  const headers = new Headers({ Authorization: `Bearer ${token}` });
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  const hasBody = !["GET", "HEAD"].includes(req.method);
  const res = await fetch(url, {
    method: req.method,
    headers,
    body: hasBody ? await req.arrayBuffer() : undefined,
    cache: "no-store",
  });

  const out = new Headers();
  for (const h of ["content-type", "content-length", "cache-control"]) {
    const v = res.headers.get(h);
    if (v) out.set(h, v);
  }
  return new Response(res.body, { status: res.status, headers: out });
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;
