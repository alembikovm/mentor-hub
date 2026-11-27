"""Mentor's cabinet: their mentees, per-course access and progress."""

from fastapi import APIRouter, status
from sqlalchemy import delete, select

from app.auth import DB, Mentor
from app.models import CourseAccess, MentorMentee, Roadmap, User
from app.schemas import MenteeCourseOut, MenteeOut, ProgressOut, UserOut
from app.routers.roadmaps import roadmap_out
from app.services import course_progress, get_my_mentee, load_tree

router = APIRouter(prefix="/mentees", tags=["mentees"])


async def _mentee_out(session, mentee: User, joined_at, roadmaps: list[Roadmap]) -> MenteeOut:
    granted = set(
        await session.scalars(
            select(CourseAccess.roadmap_id).where(
                CourseAccess.mentee_id == mentee.id,
                CourseAccess.roadmap_id.in_([r.id for r in roadmaps]),
            )
        )
    )
    courses = []
    for r in roadmaps:
        progress = None
        if r.id in granted:
            p = await course_progress(session, mentee.id, r.id, await load_tree(session, r.id))
            progress = ProgressOut(done=p.done, total=p.total, percent=p.percent, completed_at=p.completed_at)
        courses.append(
            MenteeCourseOut(
                roadmap=await roadmap_out(session, r), has_access=r.id in granted, progress=progress
            )
        )
    return MenteeOut(**UserOut.model_validate(mentee).model_dump(), joined_at=joined_at, courses=courses)


async def _mentor_roadmaps(session, mentor: User) -> list[Roadmap]:
    return list(
        await session.scalars(
            select(Roadmap).where(Roadmap.mentor_id == mentor.id).order_by(Roadmap.created_at.desc())
        )
    )


@router.get("", response_model=list[MenteeOut])
async def list_mentees(user: Mentor, session: DB):
    rows = await session.execute(
        select(User, MentorMentee.created_at)
        .join(MentorMentee, MentorMentee.mentee_id == User.id)
        .where(MentorMentee.mentor_id == user.id)
        .order_by(MentorMentee.created_at)
    )
    roadmaps = await _mentor_roadmaps(session, user)
    return [await _mentee_out(session, m, joined, roadmaps) for m, joined in rows]


@router.get("/{mentee_id}", response_model=MenteeOut)
async def get_mentee(mentee_id: str, user: Mentor, session: DB):
    mentee = await get_my_mentee(session, user, mentee_id)
    joined = await session.scalar(
        select(MentorMentee.created_at).where(
            MentorMentee.mentor_id == user.id, MentorMentee.mentee_id == mentee_id
        )
    )
    return await _mentee_out(session, mentee, joined, await _mentor_roadmaps(session, user))


@router.delete("/{mentee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_mentee(mentee_id: str, user: Mentor, session: DB):
    """Unlink a mentee and revoke their access to all of this mentor's courses."""
    await get_my_mentee(session, user, mentee_id)
    my_courses = select(Roadmap.id).where(Roadmap.mentor_id == user.id)
    await session.execute(
        delete(CourseAccess).where(
            CourseAccess.mentee_id == mentee_id, CourseAccess.roadmap_id.in_(my_courses)
        )
    )
    await session.execute(
        delete(MentorMentee).where(
            MentorMentee.mentor_id == user.id, MentorMentee.mentee_id == mentee_id
        )
    )
    await session.commit()
