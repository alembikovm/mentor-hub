import secrets
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


def new_invite_code() -> str:
    return secrets.token_urlsafe(6).replace("-", "x").replace("_", "y").upper()


class Role(StrEnum):
    mentor = "mentor"
    mentee = "mentee"


class SubmissionStatus(StrEnum):
    pending = "pending"
    analyzing = "analyzing"
    done = "done"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Clerk user id
    email: Mapped[str | None] = mapped_column(String(320))
    name: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str | None] = mapped_column(String(16))
    invite_code: Mapped[str | None] = mapped_column(String(16), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    mentor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(Text, default="")  # original upload
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    nodes: Mapped[list["RoadmapNode"]] = relationship(
        back_populates="roadmap", cascade="all, delete-orphan"
    )


class RoadmapNode(Base):
    __tablename__ = "roadmap_nodes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    roadmap_id: Mapped[str] = mapped_column(ForeignKey("roadmaps.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("roadmap_nodes.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(Integer, default=0)

    roadmap: Mapped[Roadmap] = relationship(back_populates="nodes")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    mentee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("roadmap_nodes.id"), index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default=SubmissionStatus.pending)
    ai_review: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    mentor_comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    images: Mapped[list["SubmissionImage"]] = relationship(
        cascade="all, delete-orphan", order_by="SubmissionImage.position"
    )


class SubmissionImage(Base):
    __tablename__ = "submission_images"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), index=True)
    path: Mapped[str] = mapped_column(String(500))
    media_type: Mapped[str] = mapped_column(String(50))
    position: Mapped[int] = mapped_column(Integer, default=0)


class MentorMentee(Base):
    """A mentee joined a mentor via invite code."""

    __tablename__ = "mentor_mentees"
    __table_args__ = (UniqueConstraint("mentor_id", "mentee_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    mentor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    mentee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CourseAccess(Base):
    """Mentor granted a mentee access to one course (roadmap)."""

    __tablename__ = "course_access"
    __table_args__ = (UniqueConstraint("roadmap_id", "mentee_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    roadmap_id: Mapped[str] = mapped_column(ForeignKey("roadmaps.id"), index=True)
    mentee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TopicCompletion(Base):
    """A leaf topic marked done for a mentee (by the mentee or their mentor)."""

    __tablename__ = "topic_completions"
    __table_args__ = (UniqueConstraint("mentee_id", "node_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    mentee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    roadmap_id: Mapped[str] = mapped_column(ForeignKey("roadmaps.id"), index=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("roadmap_nodes.id"), index=True)
    marked_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CourseCompletion(Base):
    __tablename__ = "course_completions"
    __table_args__ = (UniqueConstraint("mentee_id", "roadmap_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    mentee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    roadmap_id: Mapped[str] = mapped_column(ForeignKey("roadmaps.id"), index=True)
    marked_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
