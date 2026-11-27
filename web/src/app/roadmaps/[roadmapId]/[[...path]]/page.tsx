import Link from "next/link";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { deleteRoadmap } from "@/app/actions";
import { ProgressBar } from "@/components/progress";
import { SubmissionForm } from "@/components/submission-form";
import { SubmissionList } from "@/components/submission-list";
import { AccessSwitch, DoneButton, DoneCheckbox } from "@/components/toggles";
import { EmptyState, PageSkeleton } from "@/components/ui";
import { ApiError, api, apiOr404, requireMe } from "@/lib/api";
import type { CourseMember, NodeDetail, Submission, TopicNode } from "@/lib/types";

type Props = PageProps<"/roadmaps/[roadmapId]/[[...path]]">;

/**
 * /roadmaps/:id                 -> course root with top-level topics
 * /roadmaps/:id/:a/:b/:c        -> topic c (a > b > c), each segment is a node id
 * ?mentee=:menteeId             -> mentor views / edits that mentee's progress
 */
function makeHref(roadmapId: string, menteeId?: string) {
  const qs = menteeId ? `?mentee=${menteeId}` : "";
  return (chain: TopicNode[]) => `/roadmaps/${roadmapId}${chain.map((n) => `/${n.id}`).join("")}${qs}`;
}

/** Read-only topic status for the mentee: done, up next, in progress, or locked. */
function TopicStatus({ node }: { node: TopicNode }) {
  const base = "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px]";
  if (node.done) return <span className={`${base} bg-emerald-500 text-white`} title="Done">✓</span>;
  if (node.locked)
    return (
      <span className={`${base} text-stone-400`} title="Locked">
        <LockIcon />
      </span>
    );
  if (node.current) return <span className={`${base} border-2 border-indigo-500 bg-indigo-50`} title="Up next" />;
  return <span className={`${base} border-2 border-indigo-300 text-indigo-500`} title="In progress">–</span>;
}

function LockIcon({ className = "h-3.5 w-3.5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className={className} aria-hidden>
      <path d="M8 1a3.5 3.5 0 0 0-3.5 3.5V6H4a1.5 1.5 0 0 0-1.5 1.5v6A1.5 1.5 0 0 0 4 15h8a1.5 1.5 0 0 0 1.5-1.5v-6A1.5 1.5 0 0 0 12 6h-.5V4.5A3.5 3.5 0 0 0 8 1Zm2 5V4.5a2 2 0 1 0-4 0V6h4Z" />
    </svg>
  );
}

function LockedTopic({ roadmapId }: { roadmapId: string }) {
  return (
    <div className="card mx-auto mt-10 max-w-md p-8 text-center">
      <LockIcon className="mx-auto h-8 w-8 text-stone-400" />
      <h1 className="mt-4 text-lg font-semibold">This topic is locked</h1>
      <p className="mt-2 text-sm text-stone-600">
        It opens once your mentor marks the previous topics done.
      </p>
      <Link href={`/roadmaps/${roadmapId}`} className="btn-secondary mt-6 inline-flex">
        Back to the course
      </Link>
    </div>
  );
}

async function MembersTable({ roadmapId }: { roadmapId: string }) {
  const members = await api<CourseMember[]>(`/roadmaps/${roadmapId}/members`);
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Access & progress</h2>
      {members.length ? (
        <ul className="card divide-y divide-stone-100">
          {members.map(({ mentee, has_access, progress }) => (
            <li key={mentee.id} className="flex flex-wrap items-center gap-4 px-4 py-3">
              <Link href={`/mentees/${mentee.id}`} className="min-w-40 flex-1 text-sm font-medium hover:text-indigo-700">
                {mentee.name || mentee.email || "Unnamed"}
              </Link>
              <div className="w-full sm:w-56">
                {has_access && progress ? (
                  <ProgressBar progress={progress} size="sm" />
                ) : (
                  <span className="text-xs text-stone-400">—</span>
                )}
              </div>
              <AccessSwitch roadmapId={roadmapId} menteeId={mentee.id} granted={has_access} />
              {has_access && (
                <Link href={`/roadmaps/${roadmapId}?mentee=${mentee.id}`} className="text-sm text-indigo-600 hover:underline">
                  View
                </Link>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState>No mentees yet. Share your invite code from the dashboard.</EmptyState>
      )}
    </section>
  );
}

async function TopicPage({ params, searchParams }: Pick<Props, "params" | "searchParams">) {
  const { roadmapId, path = [] } = await params;
  const query = await searchParams;
  const me = await requireMe();
  const isMentor = me.role === "mentor";
  const menteeParam = isMentor && typeof query.mentee === "string" ? query.mentee : undefined;

  const nodeId = path.at(-1);
  const qs = menteeParam ? `?mentee_id=${menteeParam}` : "";
  let detail: NodeDetail;
  try {
    detail = await apiOr404<NodeDetail>(
      (nodeId ? `/roadmaps/${roadmapId}/nodes/${nodeId}` : `/roadmaps/${roadmapId}`) + qs,
    );
  } catch (e) {
    if (e instanceof ApiError && e.status === 403) return <LockedTopic roadmapId={roadmapId} />;
    throw e;
  }
  const { roadmap, node, ancestors, children, subject } = detail;
  const href = makeHref(roadmapId, menteeParam);

  // Keep URLs canonical: the path must be the node's real ancestry.
  const chain = node ? [...ancestors, node] : [];
  if (chain.map((n) => n.id).join("/") !== path.join("/")) redirect(href(chain));

  // Progress is shown for the mentee themself, or for the mentee a mentor picked.
  // Only the mentor marks topics done; the mentee sees read-only statuses.
  const tracking = !!subject;
  const canMark = isMentor && tracking;
  const subjectId = isMentor ? subject?.id : undefined;

  const submissions = node
    ? await api<Submission[]>(`/submissions?node_id=${node.id}${subjectId ? `&mentee_id=${subjectId}` : ""}`)
    : [];

  return (
    <div className="space-y-8">
      {isMentor && subject && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-indigo-50 px-4 py-2.5 text-sm text-indigo-900">
          <span>
            Viewing progress of <span className="font-semibold">{subject.name || subject.email}</span>. Changes you make are
            saved to their progress.
          </span>
          <Link href={makeHref(roadmapId)(chain)} className="font-medium hover:underline">
            Exit
          </Link>
        </div>
      )}

      <nav className="flex flex-wrap items-center gap-1 text-sm text-stone-500">
        <Link href={isMentor && subject ? `/mentees/${subject.id}` : "/dashboard"} className="hover:text-stone-900">
          {isMentor && subject ? subject.name || "Mentee" : "Dashboard"}
        </Link>
        <span>/</span>
        <Link href={href([])} className="hover:text-stone-900">
          {roadmap.title}
        </Link>
        {ancestors.map((a, i) => (
          <span key={a.id} className="flex items-center gap-1">
            <span>/</span>
            <Link href={href(ancestors.slice(0, i + 1))} className="hover:text-stone-900">
              {a.title}
            </Link>
          </span>
        ))}
      </nav>

      <header className="space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{node?.title ?? roadmap.title}</h1>
            {(node ? node.description : roadmap.description) && (
              <p className="mt-2 max-w-2xl whitespace-pre-line text-stone-600">
                {node ? node.description : roadmap.description}
              </p>
            )}
          </div>
          {isMentor && !node && !subject && (
            <form action={deleteRoadmap.bind(null, roadmapId)}>
              <button className="btn-danger">Delete course</button>
            </form>
          )}
        </div>

        {tracking && !node && roadmap.progress && (
          <div className="card flex flex-wrap items-center gap-4 p-4">
            <div className="min-w-56 flex-1">
              <ProgressBar progress={roadmap.progress} />
            </div>
            {canMark ? (
              <DoneButton
                roadmapId={roadmapId}
                nodeId={null}
                done={!!roadmap.progress.completed_at}
                menteeId={subjectId}
                labels={["Mark course completed", "Course completed — undo"]}
              />
            ) : (
              !roadmap.progress.completed_at && (
                <p className="text-sm text-stone-500">Your mentor marks topics done after reviewing your work.</p>
              )
            )}
          </div>
        )}

        {tracking && node && (
          <div className="flex flex-wrap items-center gap-4">
            {canMark ? (
              <DoneButton
                roadmapId={roadmapId}
                nodeId={node.id}
                done={!!node.done}
                menteeId={subjectId}
                labels={node.child_count ? ["Mark section done", "Section done — undo"] : undefined}
              />
            ) : node.done ? (
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-800">
                ✓ Done — confirmed by your mentor
              </span>
            ) : (
              <span className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-800">
                In progress — your mentor marks it done after reviewing your solution
              </span>
            )}
            {node.child_count > 0 && (
              <span className="text-sm text-stone-500">
                {node.leaves_done}/{node.leaves_total} topics in this section done
              </span>
            )}
          </div>
        )}
      </header>

      {children.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-stone-500">
            {node ? "Subtopics" : "Topics"}
          </h2>
          <ol className="card divide-y divide-stone-100">
            {children.map((c, i) => {
              const body = (
                <>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`font-medium ${c.locked ? "" : "group-hover:text-indigo-700"} ${c.done ? "text-stone-500" : ""}`}>
                        {c.title}
                      </span>
                      {c.current && (
                        <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">Up next</span>
                      )}
                      {c.locked && isMentor && (
                        <span className="text-stone-400" title="Locked for the mentee">
                          <LockIcon className="h-3 w-3" />
                        </span>
                      )}
                    </div>
                    {c.description && <p className="truncate text-sm text-stone-500">{c.description}</p>}
                  </div>
                  {c.child_count > 0 && (
                    <span className="shrink-0 rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
                      {tracking ? `${c.leaves_done}/${c.leaves_total}` : `${c.child_count} subtopic${c.child_count === 1 ? "" : "s"}`}
                    </span>
                  )}
                </>
              );
              // Mentees can't open topics they haven't reached; mentors can open everything.
              const blocked = !isMentor && !!c.locked;
              return (
                <li key={c.id} className={`flex items-center gap-3 pl-4 ${blocked ? "bg-stone-50/60" : ""}`}>
                  {canMark ? (
                    <DoneCheckbox
                      roadmapId={roadmapId}
                      nodeId={c.id}
                      done={!!c.done}
                      partial={!!c.leaves_done && !c.done}
                      menteeId={subjectId}
                    />
                  ) : tracking ? (
                    <TopicStatus node={c} />
                  ) : (
                    <span className="w-5 text-right font-mono text-xs text-stone-400">{i + 1}</span>
                  )}
                  {blocked ? (
                    <div className="flex min-w-0 flex-1 cursor-not-allowed items-center gap-4 py-3 pr-4 text-stone-400" title="Locked until your mentor marks the previous topics done">
                      {body}
                    </div>
                  ) : (
                    <Link href={href([...chain, c])} className="group flex min-w-0 flex-1 items-center gap-4 py-3 pr-4">
                      {body}
                      <span className="text-stone-400 group-hover:text-indigo-600">→</span>
                    </Link>
                  )}
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {!node && children.length === 0 && <EmptyState>This course has no topics.</EmptyState>}

      {isMentor && !node && !subject && (
        <Suspense fallback={<div className="h-24 animate-pulse rounded-xl bg-stone-200" />}>
          <MembersTable roadmapId={roadmapId} />
        </Suspense>
      )}

      {node && (
        <section className="space-y-4">
          <h2 className="text-lg font-semibold">
            {isMentor ? (subject ? `${subject.name || "Mentee"}'s submissions` : "Mentee submissions") : "Your solutions"}
          </h2>
          {!isMentor && <SubmissionForm nodeId={node.id} />}
          <SubmissionList
            submissions={submissions}
            showMentee={isMentor && !subject}
            showTopic={false}
            empty={isMentor ? "No submissions for this topic yet." : "You haven't submitted a solution for this topic."}
          />
        </section>
      )}
    </div>
  );
}

export default function Page(props: Props) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <TopicPage params={props.params} searchParams={props.searchParams} />
    </Suspense>
  );
}
