from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select, update

from app.auth import DB, CurrentUser, Mentor
from app.models import (
    CourseAccess,
    CourseCompletion,
    MentorMentee,
    Roadmap,
    RoadmapNode,
    Role,
    Submission,
    SubmissionImage,
    TopicCompletion,
    User,
)
from app.roadmap_parser import RoadmapParseError, parse_roadmap
from app.schemas import (
    CourseMemberOut,
    DoneIn,
    NodeDetail,
    NodeOut,
    ProgressOut,
    RoadmapIn,
    RoadmapOut,
    UserOut,
)
from app.services import (
    Tree,
    build_nodes,
    completed_leaves,
    course_progress,
    get_my_mentee,
    get_visible_node,
    get_visible_roadmap,
    load_tree,
    node_ancestors,
    resolve_progress_subject,
    set_course_done,
    set_topic_done,
    visible_roadmap_ids,
)

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


def _progress_out(p) -> ProgressOut:
    return ProgressOut(done=p.done, total=p.total, percent=p.percent, completed_at=p.completed_at)


async def roadmap_out(session, roadmap: Roadmap, viewer: User | None = None) -> RoadmapOut:
    count = await session.scalar(
        select(func.count()).select_from(RoadmapNode).where(RoadmapNode.roadmap_id == roadmap.id)
    )
    out = RoadmapOut.model_validate(roadmap)
    out.topic_count = count or 0
    if viewer is None:
        return out
    if viewer.role == Role.mentee:
        mentor = await session.get(User, roadmap.mentor_id)
        out.mentor = UserOut.model_validate(mentor).model_copy(update={"invite_code": None})
        out.progress = _progress_out(await course_progress(session, viewer.id, roadmap.id))
    else:
        out.access_count = await session.scalar(
            select(func.count())
            .select_from(CourseAccess)
            .join(
                MentorMentee,
                (MentorMentee.mentee_id == CourseAccess.mentee_id)
                & (MentorMentee.mentor_id == roadmap.mentor_id),
            )
            .where(CourseAccess.roadmap_id == roadmap.id)
        )
    return out


async def _nodes_out(
    session, nodes: list[RoadmapNode], tree: Tree, done_leaves: set[str] | None
) -> list[NodeOut]:
    result = []
    for n in nodes:
        o = NodeOut.model_validate(n)
        o.child_count = len(tree.children.get(n.id, []))
        if done_leaves is not None:
            leaves = tree.leaves_under(n.id)
            o.leaves_total = len(leaves)
            o.leaves_done = len(leaves & done_leaves)
            o.done = o.leaves_done == o.leaves_total
        result.append(o)
    return result


async def _children(session, roadmap_id: str, parent_id: str | None) -> list[RoadmapNode]:
    q = select(RoadmapNode).where(RoadmapNode.roadmap_id == roadmap_id)
    q = q.where(RoadmapNode.parent_id.is_(None) if parent_id is None else RoadmapNode.parent_id == parent_id)
    return list(await session.scalars(q.order_by(RoadmapNode.position)))


async def _detail(session, user: User, roadmap: Roadmap, node: RoadmapNode | None, mentee_id: str | None) -> NodeDetail:
    subject_id = await resolve_progress_subject(session, user, roadmap, mentee_id)
    tree = await load_tree(session, roadmap.id)
    done = await completed_leaves(session, subject_id, roadmap.id) if subject_id else None

    out_roadmap = await roadmap_out(session, roadmap, user)
    if subject_id and user.role == Role.mentor:
        out_roadmap.progress = _progress_out(await course_progress(session, subject_id, roadmap.id, tree))

    ancestors = await node_ancestors(session, node) if node else []
    children = await _children(session, roadmap.id, node.id if node else None)
    subject = await session.get(User, subject_id) if subject_id else None
    return NodeDetail(
        roadmap=out_roadmap,
        node=(await _nodes_out(session, [node], tree, done))[0] if node else None,
        ancestors=await _nodes_out(session, ancestors, tree, done),
        children=await _nodes_out(session, children, tree, done),
        subject=UserOut.model_validate(subject) if subject else None,
    )


# ---------------------------------------------------------------- CRUD


@router.get("", response_model=list[RoadmapOut])
async def list_roadmaps(user: CurrentUser, session: DB):
    ids = await visible_roadmap_ids(session, user)
    if not ids:
        return []
    rows = await session.scalars(
        select(Roadmap).where(Roadmap.id.in_(ids)).order_by(Roadmap.created_at.desc())
    )
    return [await roadmap_out(session, r, user) for r in rows]


@router.post("/preview")
async def preview_roadmap(body: RoadmapIn, user: Mentor):
    """Parse without saving, so the upload form can show the resulting tree."""
    try:
        parsed = parse_roadmap(body.source, body.title or "Untitled roadmap")
    except RoadmapParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    def dump(nodes):
        return [{"title": n.title, "description": n.description, "children": dump(n.children)} for n in nodes]

    return {
        "title": body.title or parsed.title,
        "description": parsed.description,
        "topic_count": parsed.count(),
        "children": dump(parsed.children),
    }


@router.post("", response_model=RoadmapOut, status_code=status.HTTP_201_CREATED)
async def create_roadmap(body: RoadmapIn, user: Mentor, session: DB):
    try:
        parsed = parse_roadmap(body.source, body.title or "Untitled roadmap")
    except RoadmapParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    roadmap = Roadmap(
        mentor_id=user.id,
        title=(body.title or parsed.title)[:300],
        description=parsed.description,
        source=body.source,
    )
    session.add(roadmap)
    await session.flush()
    session.add_all(build_nodes(roadmap.id, parsed.children))
    await session.commit()
    return await roadmap_out(session, roadmap, user)


@router.delete("/{roadmap_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_roadmap(roadmap_id: str, user: Mentor, session: DB):
    roadmap = await get_visible_roadmap(session, user, roadmap_id)
    rid = roadmap.id
    node_ids = select(RoadmapNode.id).where(RoadmapNode.roadmap_id == rid)
    sub_ids = select(Submission.id).where(Submission.node_id.in_(node_ids))
    await session.execute(delete(SubmissionImage).where(SubmissionImage.submission_id.in_(sub_ids)))
    await session.execute(delete(Submission).where(Submission.node_id.in_(node_ids)))
    await session.execute(delete(TopicCompletion).where(TopicCompletion.roadmap_id == rid))
    await session.execute(delete(CourseCompletion).where(CourseCompletion.roadmap_id == rid))
    await session.execute(delete(CourseAccess).where(CourseAccess.roadmap_id == rid))
    await session.execute(update(RoadmapNode).where(RoadmapNode.roadmap_id == rid).values(parent_id=None))
    await session.execute(delete(RoadmapNode).where(RoadmapNode.roadmap_id == rid))
    await session.execute(delete(Roadmap).where(Roadmap.id == rid))
    await session.commit()


# ---------------------------------------------------------------- browsing


@router.get("/{roadmap_id}", response_model=NodeDetail)
async def get_roadmap_root(roadmap_id: str, user: CurrentUser, session: DB, mentee_id: str | None = None):
    roadmap = await get_visible_roadmap(session, user, roadmap_id)
    return await _detail(session, user, roadmap, None, mentee_id)


@router.get("/{roadmap_id}/nodes/{node_id}", response_model=NodeDetail)
async def get_node(
    roadmap_id: str, node_id: str, user: CurrentUser, session: DB, mentee_id: str | None = None
):
    node = await get_visible_node(session, user, node_id)
    if node.roadmap_id != roadmap_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found")
    roadmap = await session.get(Roadmap, roadmap_id)
    return await _detail(session, user, roadmap, node, mentee_id)


# ---------------------------------------------------------------- access (mentor)


@router.get("/{roadmap_id}/members", response_model=list[CourseMemberOut])
async def list_members(roadmap_id: str, user: Mentor, session: DB):
    """All of the mentor's mentees with their access flag and progress in this course."""
    roadmap = await get_visible_roadmap(session, user, roadmap_id)
    mentees = await session.scalars(
        select(User)
        .join(MentorMentee, MentorMentee.mentee_id == User.id)
        .where(MentorMentee.mentor_id == user.id)
        .order_by(MentorMentee.created_at)
    )
    granted = set(
        await session.scalars(select(CourseAccess.mentee_id).where(CourseAccess.roadmap_id == roadmap.id))
    )
    tree = await load_tree(session, roadmap.id)
    out = []
    for m in mentees:
        has = m.id in granted
        progress = _progress_out(await course_progress(session, m.id, roadmap.id, tree)) if has else None
        out.append(CourseMemberOut(mentee=UserOut.model_validate(m), has_access=has, progress=progress))
    return out


@router.put("/{roadmap_id}/access/{mentee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def grant_access(roadmap_id: str, mentee_id: str, user: Mentor, session: DB):
    roadmap = await get_visible_roadmap(session, user, roadmap_id)
    await get_my_mentee(session, user, mentee_id)
    exists = await session.scalar(
        select(CourseAccess.id).where(
            CourseAccess.roadmap_id == roadmap.id, CourseAccess.mentee_id == mentee_id
        )
    )
    if exists is None:
        session.add(CourseAccess(roadmap_id=roadmap.id, mentee_id=mentee_id))
        await session.commit()


@router.delete("/{roadmap_id}/access/{mentee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_access(roadmap_id: str, mentee_id: str, user: Mentor, session: DB):
    """Progress and submissions are kept, so re-granting restores them."""
    roadmap = await get_visible_roadmap(session, user, roadmap_id)
    await session.execute(
        delete(CourseAccess).where(
            CourseAccess.roadmap_id == roadmap.id, CourseAccess.mentee_id == mentee_id
        )
    )
    await session.commit()


# ---------------------------------------------------------------- progress


async def _subject_or_400(session, user: User, roadmap: Roadmap, mentee_id: str | None) -> str:
    subject = await resolve_progress_subject(session, user, roadmap, mentee_id)
    if subject is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "mentee_id is required")
    return subject


@router.put("/{roadmap_id}/nodes/{node_id}/done", response_model=NodeDetail)
async def mark_topic(roadmap_id: str, node_id: str, body: DoneIn, user: CurrentUser, session: DB):
    """Mark a topic (and every subtopic under it) done or not done."""
    node = await get_visible_node(session, user, node_id)
    if node.roadmap_id != roadmap_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found")
    roadmap = await session.get(Roadmap, roadmap_id)
    subject = await _subject_or_400(session, user, roadmap, body.mentee_id)
    await set_topic_done(
        session, roadmap_id=roadmap_id, node_id=node.id, mentee_id=subject, by=user.id, done=body.done
    )
    await session.commit()
    return await _detail(session, user, roadmap, node, body.mentee_id)


@router.put("/{roadmap_id}/done", response_model=NodeDetail)
async def mark_course(roadmap_id: str, body: DoneIn, user: CurrentUser, session: DB):
    """Completing a course also marks all of its remaining topics done."""
    roadmap = await get_visible_roadmap(session, user, roadmap_id)
    subject = await _subject_or_400(session, user, roadmap, body.mentee_id)
    if body.done:
        await set_topic_done(
            session, roadmap_id=roadmap.id, node_id=None, mentee_id=subject, by=user.id, done=True
        )
    await set_course_done(session, roadmap_id=roadmap.id, mentee_id=subject, by=user.id, done=body.done)
    await session.commit()
    return await _detail(session, user, roadmap, None, body.mentee_id)
