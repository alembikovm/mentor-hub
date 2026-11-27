"use server";

import { currentUser } from "@clerk/nextjs/server";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { api, ApiError } from "@/lib/api";
import type { Roadmap, Role } from "@/lib/types";

export type ActionState = { error?: string; ok?: boolean } | undefined;

function errorMessage(e: unknown): string {
  return e instanceof ApiError ? e.message : "Something went wrong. Try again.";
}

export async function onboard(role: Role): Promise<ActionState> {
  const user = await currentUser();
  try {
    await api("/me/onboard", {
      method: "POST",
      body: JSON.stringify({
        role,
        name: user?.fullName || user?.username || null,
        email: user?.primaryEmailAddress?.emailAddress ?? null,
      }),
    });
  } catch (e) {
    return { error: errorMessage(e) };
  }
  redirect("/dashboard");
}

export async function joinMentor(_: ActionState, form: FormData): Promise<ActionState> {
  try {
    await api("/me/join", {
      method: "POST",
      body: JSON.stringify({ invite_code: String(form.get("invite_code") ?? "") }),
    });
  } catch (e) {
    return { error: errorMessage(e) };
  }
  revalidatePath("/dashboard");
  return { ok: true };
}

export async function rotateInviteCode(): Promise<void> {
  await api("/me/invite-code/rotate", { method: "POST" });
  revalidatePath("/dashboard");
}

export async function createRoadmap(source: string, title: string): Promise<ActionState> {
  let roadmap: Roadmap;
  try {
    roadmap = await api<Roadmap>("/roadmaps", {
      method: "POST",
      body: JSON.stringify({ source, title: title.trim() || null }),
    });
  } catch (e) {
    return { error: errorMessage(e) };
  }
  redirect(`/roadmaps/${roadmap.id}`);
}

export async function deleteRoadmap(roadmapId: string): Promise<void> {
  await api(`/roadmaps/${roadmapId}`, { method: "DELETE" });
  redirect("/dashboard");
}

export async function saveMentorComment(
  submissionId: string,
  _: ActionState,
  form: FormData,
): Promise<ActionState> {
  try {
    await api(`/submissions/${submissionId}/comment`, {
      method: "PATCH",
      body: JSON.stringify({ mentor_comment: String(form.get("mentor_comment") ?? "") }),
    });
  } catch (e) {
    return { error: errorMessage(e) };
  }
  revalidatePath(`/submissions/${submissionId}`);
  return { ok: true };
}

export async function reanalyze(submissionId: string): Promise<void> {
  await api(`/submissions/${submissionId}/reanalyze`, { method: "POST" });
  revalidatePath(`/submissions/${submissionId}`);
}

// ------------------------------------------------------------ access & progress

function refreshAll() {
  revalidatePath("/", "layout");
}

export async function setCourseAccess(roadmapId: string, menteeId: string, granted: boolean): Promise<ActionState> {
  try {
    await api(`/roadmaps/${roadmapId}/access/${menteeId}`, { method: granted ? "PUT" : "DELETE" });
  } catch (e) {
    return { error: errorMessage(e) };
  }
  refreshAll();
  return { ok: true };
}

/** nodeId = null marks the whole course. menteeId is required when a mentor marks for a mentee. */
export async function setDone(
  roadmapId: string,
  nodeId: string | null,
  done: boolean,
  menteeId?: string,
): Promise<ActionState> {
  const path = nodeId ? `/roadmaps/${roadmapId}/nodes/${nodeId}/done` : `/roadmaps/${roadmapId}/done`;
  try {
    await api(path, { method: "PUT", body: JSON.stringify({ done, mentee_id: menteeId ?? null }) });
  } catch (e) {
    return { error: errorMessage(e) };
  }
  refreshAll();
  return { ok: true };
}

export async function removeMentee(menteeId: string): Promise<void> {
  await api(`/mentees/${menteeId}`, { method: "DELETE" });
  refreshAll();
  redirect("/dashboard");
}
