from typing import Literal

from pydantic import BaseModel, Field


class Perception(BaseModel):
    """What the vision model literally sees in the screenshots."""

    is_readable: bool = Field(description="False if screenshots are too blurry, cropped or unrelated to judge")
    unreadable_reason: str = Field(description="Why it can't be judged; empty string if readable")
    content_type: Literal["code", "ui", "terminal", "diagram", "text", "mixed", "other"]
    transcription: str = Field(description="Verbatim transcription of code / terminal / text visible in the screenshots")
    ui_description: str = Field(description="Description of rendered UI, layout, visible state; empty if none")
    visible_errors: list[str] = Field(description="Error messages, failing tests, linter warnings visible on screen")


class Issue(BaseModel):
    severity: Literal["critical", "major", "minor"]
    title: str
    detail: str
    location: str = Field(description="Where in the screenshot/code, e.g. 'line 12' or 'header'; empty if general")


class Review(BaseModel):
    verdict: Literal["correct", "partially_correct", "incorrect", "off_topic", "unreadable"]
    score: int = Field(description="0-100 quality score for this topic")
    summary: str = Field(description="2-4 sentence overview for the mentor")
    strengths: list[str]
    issues: list[Issue]
    suggestions: list[str] = Field(description="Concrete next steps for the mentee")
    questions_for_mentor: list[str] = Field(
        description="Things the model couldn't decide from the screenshot and the mentor should check"
    )
