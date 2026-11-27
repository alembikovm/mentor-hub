from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.auth import DB, CurrentUser, Mentee, Mentor
from app.models import MentorMentee, Role, User, new_invite_code
from app.schemas import JoinIn, MeOut, OnboardIn, UserOut

router = APIRouter(tags=["users"])


async def _me_out(session, user: User) -> MeOut:
    out = MeOut.model_validate(user)
    if user.role == Role.mentee:
        mentors = await session.scalars(
            select(User)
            .join(MentorMentee, MentorMentee.mentor_id == User.id)
            .where(MentorMentee.mentee_id == user.id)
            .order_by(MentorMentee.created_at)
        )
        out.mentors = [UserOut.model_validate(m).model_copy(update={"invite_code": None}) for m in mentors]
    return out


@router.get("/me", response_model=MeOut)
async def get_me(user: CurrentUser, session: DB):
    return await _me_out(session, user)


@router.post("/me/onboard", response_model=MeOut)
async def onboard(body: OnboardIn, user: CurrentUser, session: DB):
    if user.role and user.role != body.role:
        raise HTTPException(status.HTTP_409_CONFLICT, "Role is already set")
    user.role = body.role
    user.name = body.name or user.name
    user.email = body.email or user.email
    if body.role == Role.mentor and not user.invite_code:
        user.invite_code = new_invite_code()
    await session.commit()
    return await _me_out(session, user)


@router.post("/me/invite-code/rotate", response_model=MeOut)
async def rotate_invite(user: Mentor, session: DB):
    user.invite_code = new_invite_code()
    await session.commit()
    return await _me_out(session, user)


@router.post("/me/join", response_model=MeOut)
async def join_mentor(body: JoinIn, user: Mentee, session: DB):
    mentor = await session.scalar(
        select(User).where(
            func.upper(User.invite_code) == body.invite_code.strip().upper(),
            User.role == Role.mentor,
        )
    )
    if mentor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite code not found")
    exists = await session.scalar(
        select(MentorMentee.id).where(
            MentorMentee.mentor_id == mentor.id, MentorMentee.mentee_id == user.id
        )
    )
    if exists is None:
        session.add(MentorMentee(mentor_id=mentor.id, mentee_id=user.id))
        await session.commit()
    return await _me_out(session, user)
