from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(ORM):
    id: str
    email: str | None
    name: str | None
    role: Literal["mentor", "mentee"] | None
    invite_code: str | None = None


class MeOut(UserOut):
    mentors: list[UserOut] = []


class OnboardIn(BaseModel):
    role: Literal["mentor", "mentee"]
    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)


class JoinIn(BaseModel):
    invite_code: str = Field(min_length=4, max_length=16)


class RoadmapIn(BaseModel):
    source: str = Field(min_length=1, max_length=500_000)
    title: str | None = Field(default=None, max_length=300)


class ProgressOut(BaseModel):
    done: int
    total: int
    percent: int
    completed_at: datetime | None = None


class RoadmapOut(ORM):
    id: str
    title: str
    description: str
    created_at: datetime
    topic_count: int = 0
    mentor: UserOut | None = None
    # Mentee view: own progress. Mentor view: number of mentees with access.
    progress: ProgressOut | None = None
    access_count: int | None = None


class NodeOut(ORM):
    id: str
    title: str
    description: str
    position: int
    child_count: int = 0
    # Present when progress is being viewed for a mentee.
    done: bool | None = None
    leaves_done: int | None = None
    leaves_total: int | None = None
    # Sequential unlocking: a locked topic can't be opened by the mentee yet;
    # "current" marks the topic (or the section containing it) to work on now.
    locked: bool | None = None
    current: bool | None = None


class NodeDetail(BaseModel):
    roadmap: RoadmapOut
    node: NodeOut | None  # None = roadmap root
    ancestors: list[NodeOut]
    children: list[NodeOut]
    subject: UserOut | None = None  # whose progress is shown


class SubmissionImageOut(ORM):
    id: str
    media_type: str


class SubmissionOut(ORM):
    id: str
    node_id: str
    note: str
    status: str
    ai_review: dict | None
    error: str | None
    mentor_comment: str | None
    created_at: datetime
    images: list[SubmissionImageOut]
    mentee: UserOut | None = None
    topic_title: str | None = None
    roadmap_id: str | None = None
    topic_path: list[str] = []


class MentorCommentIn(BaseModel):
    mentor_comment: str = Field(max_length=20_000)


class DoneIn(BaseModel):
    done: bool
    mentee_id: str | None = None  # required when a mentor marks for a mentee


class MenteeCourseOut(BaseModel):
    """One course from the mentor's perspective for one mentee."""

    roadmap: RoadmapOut
    has_access: bool
    progress: ProgressOut | None


class MenteeOut(UserOut):
    joined_at: datetime
    courses: list[MenteeCourseOut] = []


class CourseMemberOut(BaseModel):
    """One of the mentor's mentees from the perspective of a course."""

    mentee: UserOut
    has_access: bool
    progress: ProgressOut | None
