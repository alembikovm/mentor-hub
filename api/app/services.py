"""Access rules and progress computation shared by the routers.

Visibility:
  * a mentor sees their own courses (roadmaps);
  * a mentee sees a course only if they are linked to its mentor AND the mentor
    granted access to that course.

Progress is tracked on leaf topics. A parent topic is done when every leaf
below it is done; marking a parent marks all leaves in its subtree. Only the
mentor marks topics done.

Topics unlock in order: a mentee can open the leaves already done plus the
first leaf that isn't (the "current" topic). A section is open when anything
inside it is open.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CourseAccess,
    CourseCompletion,
    MentorMentee,
    Roadmap,
    RoadmapNode,
    Role,
    TopicCompletion,
    User,
    _uuid,
)
from app.roadmap_parser import ParsedNode


def not_found(what: str = "Course") -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found")


# ---------------------------------------------------------------- relations


async def is_linked(session: AsyncSession, mentor_id: str, mentee_id: str) -> bool:
    return (
        await session.scalar(
            select(MentorMentee.id).where(
                MentorMentee.mentor_id == mentor_id, MentorMentee.mentee_id == mentee_id
            )
        )
    ) is not None


async def has_access(session: AsyncSession, roadmap: Roadmap, mentee_id: str) -> bool:
    granted = await session.scalar(
        select(CourseAccess.id).where(
            CourseAccess.roadmap_id == roadmap.id, CourseAccess.mentee_id == mentee_id
        )
    )
    return granted is not None and await is_linked(session, roadmap.mentor_id, mentee_id)


async def get_my_mentee(session: AsyncSession, mentor: User, mentee_id: str) -> User:
    mentee = await session.get(User, mentee_id)
    if mentee is None or not await is_linked(session, mentor.id, mentee_id):
        raise not_found("Mentee")
    return mentee


async def visible_roadmap_ids(session: AsyncSession, user: User) -> list[str]:
    if user.role == Role.mentor:
        q = select(Roadmap.id).where(Roadmap.mentor_id == user.id)
    elif user.role == Role.mentee:
        q = (
            select(Roadmap.id)
            .join(CourseAccess, CourseAccess.roadmap_id == Roadmap.id)
            .join(
                MentorMentee,
                (MentorMentee.mentor_id == Roadmap.mentor_id)
                & (MentorMentee.mentee_id == CourseAccess.mentee_id),
            )
            .where(CourseAccess.mentee_id == user.id)
        )
    else:
        return []
    return list(await session.scalars(q))


async def get_visible_roadmap(session: AsyncSession, user: User, roadmap_id: str) -> Roadmap:
    roadmap = await session.get(Roadmap, roadmap_id)
    if roadmap is None:
        raise not_found()
    if user.role == Role.mentor and roadmap.mentor_id == user.id:
        return roadmap
    if user.role == Role.mentee and await has_access(session, roadmap, user.id):
        return roadmap
    raise not_found()


async def get_visible_node(session: AsyncSession, user: User, node_id: str) -> RoadmapNode:
    node = await session.get(RoadmapNode, node_id)
    if node is None:
        raise not_found("Topic")
    await get_visible_roadmap(session, user, node.roadmap_id)
    return node


async def resolve_progress_subject(
    session: AsyncSession, user: User, roadmap: Roadmap, mentee_id: str | None
) -> str | None:
    """Whose progress the viewer is looking at / editing.

    Mentees always act on themselves. Mentors must name a mentee who has
    access to this course; without one there is no progress to show.
    """
    if user.role == Role.mentee:
        return user.id
    if mentee_id is None:
        return None
    if not await has_access(session, roadmap, mentee_id):
        raise not_found("Mentee")
    return mentee_id


# ---------------------------------------------------------------- tree


async def node_ancestors(session: AsyncSession, node: RoadmapNode) -> list[RoadmapNode]:
    """Ancestors of a node, root first."""
    chain: list[RoadmapNode] = []
    parent_id = node.parent_id
    while parent_id:
        parent = await session.get(RoadmapNode, parent_id)
        if parent is None:
            break
        chain.append(parent)
        parent_id = parent.parent_id
    return list(reversed(chain))


@dataclass
class Tree:
    children: dict[str | None, list[str]]  # ordered by position

    def ordered_leaves(self) -> list[str]:
        out: list[str] = []
        stack = list(reversed(self.children.get(None, [])))
        while stack:
            nid = stack.pop()
            sub = self.children.get(nid, [])
            if sub:
                stack.extend(reversed(sub))
            else:
                out.append(nid)
        return out

    def current_leaf(self, done: set[str]) -> str | None:
        """First leaf in course order that isn't done (None when all are)."""
        return next((leaf for leaf in self.ordered_leaves() if leaf not in done), None)

    def unlocked_leaves(self, done: set[str]) -> set[str]:
        current = self.current_leaf(done)
        return done | ({current} if current else set())

    def is_unlocked(self, node_id: str, done: set[str]) -> bool:
        return bool(self.leaves_under(node_id) & self.unlocked_leaves(done))

    def leaves_under(self, node_id: str | None) -> set[str]:
        """Leaf ids in the subtree of node_id (a leaf is its own subtree). None = whole course."""
        kids = self.children.get(node_id, [])
        if node_id is not None and not kids:
            return {node_id}
        out: set[str] = set()
        stack = list(kids)
        while stack:
            nid = stack.pop()
            sub = self.children.get(nid, [])
            if sub:
                stack.extend(sub)
            else:
                out.add(nid)
        return out


async def load_tree(session: AsyncSession, roadmap_id: str) -> Tree:
    rows = await session.execute(
        select(RoadmapNode.id, RoadmapNode.parent_id)
        .where(RoadmapNode.roadmap_id == roadmap_id)
        .order_by(RoadmapNode.position)
    )
    children: dict[str | None, list[str]] = {}
    for nid, pid in rows:
        children.setdefault(pid, []).append(nid)
    return Tree(children)


def build_nodes(roadmap_id: str, nodes: list[ParsedNode]) -> list[RoadmapNode]:
    out: list[RoadmapNode] = []

    def walk(items: list[ParsedNode], parent: RoadmapNode | None) -> None:
        for pos, item in enumerate(items):
            # ids are assigned up front so children can link before flush
            row = RoadmapNode(
                id=_uuid(),
                roadmap_id=roadmap_id,
                parent_id=parent.id if parent else None,
                title=item.title[:300],
                description=item.description,
                position=pos,
            )
            out.append(row)
            walk(item.children, row)

    walk(nodes, None)
    return out


# ---------------------------------------------------------------- progress


def locked_error() -> HTTPException:
    return HTTPException(
        status.HTTP_403_FORBIDDEN, "This topic is locked until your mentor marks the previous ones done"
    )


async def ensure_unlocked(session: AsyncSession, user: User, node: RoadmapNode) -> None:
    """Mentees can't open or submit to topics they haven't reached yet."""
    if user.role != Role.mentee:
        return
    tree = await load_tree(session, node.roadmap_id)
    done = await completed_leaves(session, user.id, node.roadmap_id)
    if not tree.is_unlocked(node.id, done):
        raise locked_error()


async def completed_leaves(session: AsyncSession, mentee_id: str, roadmap_id: str) -> set[str]:
    rows = await session.scalars(
        select(TopicCompletion.node_id).where(
            TopicCompletion.mentee_id == mentee_id, TopicCompletion.roadmap_id == roadmap_id
        )
    )
    return set(rows)


async def course_completed_at(session: AsyncSession, mentee_id: str, roadmap_id: str) -> datetime | None:
    return await session.scalar(
        select(CourseCompletion.completed_at).where(
            CourseCompletion.mentee_id == mentee_id, CourseCompletion.roadmap_id == roadmap_id
        )
    )


@dataclass
class Progress:
    done: int
    total: int
    completed_at: datetime | None = None

    @property
    def percent(self) -> int:
        return round(100 * self.done / self.total) if self.total else 0


async def course_progress(
    session: AsyncSession, mentee_id: str, roadmap_id: str, tree: Tree | None = None
) -> Progress:
    tree = tree or await load_tree(session, roadmap_id)
    leaves = tree.leaves_under(None)
    done = await completed_leaves(session, mentee_id, roadmap_id)
    return Progress(
        done=len(leaves & done),
        total=len(leaves),
        completed_at=await course_completed_at(session, mentee_id, roadmap_id),
    )


async def set_topic_done(
    session: AsyncSession, *, roadmap_id: str, node_id: str | None, mentee_id: str, by: str, done: bool
) -> None:
    """Mark/unmark all leaves under node_id (None = whole course)."""
    tree = await load_tree(session, roadmap_id)
    leaves = tree.leaves_under(node_id)
    existing = await completed_leaves(session, mentee_id, roadmap_id)
    if done:
        for leaf in leaves - existing:
            session.add(
                TopicCompletion(mentee_id=mentee_id, roadmap_id=roadmap_id, node_id=leaf, marked_by=by)
            )
    else:
        rows = await session.scalars(
            select(TopicCompletion).where(
                TopicCompletion.mentee_id == mentee_id, TopicCompletion.node_id.in_(leaves)
            )
        )
        for row in rows:
            await session.delete(row)
        # A course can't stay "completed" once a topic is reopened.
        await set_course_done(session, roadmap_id=roadmap_id, mentee_id=mentee_id, by=by, done=False)


async def set_course_done(
    session: AsyncSession, *, roadmap_id: str, mentee_id: str, by: str, done: bool
) -> None:
    row = await session.scalar(
        select(CourseCompletion).where(
            CourseCompletion.mentee_id == mentee_id, CourseCompletion.roadmap_id == roadmap_id
        )
    )
    if done and row is None:
        session.add(CourseCompletion(mentee_id=mentee_id, roadmap_id=roadmap_id, marked_by=by))
    elif not done and row is not None:
        await session.delete(row)
