import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.analysis.runner import run_review
from app.auth import DB, CurrentUser, Mentee, Mentor
from app.config import get_settings
from app.models import (
    Roadmap,
    Role,
    RoadmapNode,
    Submission,
    SubmissionImage,
    SubmissionStatus,
    User,
)
from app.schemas import MentorCommentIn, SubmissionOut, UserOut
from app.services import get_visible_node, node_ancestors

router = APIRouter(prefix="/submissions", tags=["submissions"])

ALLOWED_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}
MAX_IMAGES = 6


async def _out(session, sub: Submission, with_path: bool = False) -> SubmissionOut:
    out = SubmissionOut.model_validate(sub)
    node = await session.get(RoadmapNode, sub.node_id)
    if node:
        out.topic_title = node.title
        out.roadmap_id = node.roadmap_id
        if with_path:
            out.topic_path = [a.title for a in await node_ancestors(session, node)] + [node.title]
    mentee = await session.get(User, sub.mentee_id)
    out.mentee = UserOut.model_validate(mentee) if mentee else None
    return out


async def _load_visible(session, user: User, submission_id: str) -> Submission:
    sub = await session.scalar(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(selectinload(Submission.images))
    )
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    if user.role == Role.mentee and sub.mentee_id == user.id:
        return sub
    if user.role == Role.mentor:
        owner = await session.scalar(
            select(Roadmap.mentor_id)
            .join(RoadmapNode, RoadmapNode.roadmap_id == Roadmap.id)
            .where(RoadmapNode.id == sub.node_id)
        )
        if owner == user.id:
            return sub
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")


@router.post("", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
async def create_submission(
    background: BackgroundTasks,
    user: Mentee,
    session: DB,
    node_id: Annotated[str, Form()],
    images: Annotated[list[UploadFile], File()],
    note: Annotated[str, Form(max_length=5000)] = "",
):
    await get_visible_node(session, user, node_id)
    if not images or len(images) > MAX_IMAGES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Attach 1-{MAX_IMAGES} screenshots")

    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    sub = Submission(mentee_id=user.id, node_id=node_id, note=note.strip())
    session.add(sub)
    await session.flush()

    target_dir = settings.upload_dir / sub.id
    target_dir.mkdir(parents=True, exist_ok=True)
    for pos, upload in enumerate(images):
        ext = ALLOWED_TYPES.get(upload.content_type or "")
        if ext is None:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"{upload.filename}: PNG, JPEG, WEBP or GIF only")
        data = await upload.read()
        if len(data) > max_bytes:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"{upload.filename} exceeds {settings.max_upload_mb} MB")
        name = f"{uuid.uuid4().hex}.{ext}"
        (target_dir / name).write_bytes(data)
        session.add(
            SubmissionImage(
                submission_id=sub.id, path=f"{sub.id}/{name}", media_type=upload.content_type, position=pos
            )
        )
    await session.commit()
    background.add_task(run_review, sub.id)
    return await _out(session, await _load_visible(session, user, sub.id))


@router.get("", response_model=list[SubmissionOut])
async def list_submissions(
    user: CurrentUser,
    session: DB,
    node_id: str | None = None,
    mentee_id: str | None = None,
    limit: int = 50,
):
    q = select(Submission).options(selectinload(Submission.images))
    if user.role == Role.mentee:
        q = q.where(Submission.mentee_id == user.id)
    elif user.role == Role.mentor:
        q = (
            q.join(RoadmapNode, RoadmapNode.id == Submission.node_id)
            .join(Roadmap, Roadmap.id == RoadmapNode.roadmap_id)
            .where(Roadmap.mentor_id == user.id)
        )
        if mentee_id:
            q = q.where(Submission.mentee_id == mentee_id)
    else:
        return []
    if node_id:
        q = q.where(Submission.node_id == node_id)
    rows = await session.scalars(q.order_by(Submission.created_at.desc()).limit(min(limit, 200)))
    return [await _out(session, s) for s in rows]


@router.get("/{submission_id}", response_model=SubmissionOut)
async def get_submission(submission_id: str, user: CurrentUser, session: DB):
    return await _out(session, await _load_visible(session, user, submission_id), with_path=True)


@router.post("/{submission_id}/reanalyze", response_model=SubmissionOut)
async def reanalyze(submission_id: str, background: BackgroundTasks, user: CurrentUser, session: DB):
    sub = await _load_visible(session, user, submission_id)
    if sub.status in (SubmissionStatus.pending, SubmissionStatus.analyzing):
        raise HTTPException(status.HTTP_409_CONFLICT, "Analysis is already running")
    sub.status = SubmissionStatus.pending
    await session.commit()
    background.add_task(run_review, sub.id)
    return await _out(session, sub)


@router.patch("/{submission_id}/comment", response_model=SubmissionOut)
async def comment(submission_id: str, body: MentorCommentIn, user: Mentor, session: DB):
    sub = await _load_visible(session, user, submission_id)
    sub.mentor_comment = body.mentor_comment.strip() or None
    await session.commit()
    return await _out(session, sub)


@router.get("/{submission_id}/images/{image_id}")
async def get_image(submission_id: str, image_id: str, user: CurrentUser, session: DB):
    sub = await _load_visible(session, user, submission_id)
    img = next((i for i in sub.images if i.id == image_id), None)
    if img is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    return FileResponse(get_settings().upload_dir / img.path, media_type=img.media_type)
