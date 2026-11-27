"""LangGraph pipeline that reviews a mentee's screenshots.

    START -> perceive --(readable)--> assess -> END
                     \\-(unreadable)-> ask_for_resubmit -> END

`perceive`  : VLM transcribes what's on the screenshots (code, UI, errors).
`assess`    : VLM grades the solution against the roadmap topic, with the
              transcription as grounding plus the original images.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from typing import Literal, TypedDict

import anthropic
from langgraph.graph import END, START, StateGraph

from app.analysis.schemas import Perception, Review
from app.config import get_settings


class ImageInput(TypedDict):
    media_type: str
    data: bytes


class ReviewState(TypedDict, total=False):
    # inputs
    topic_path: list[str]  # ancestors + topic titles, root first
    topic_description: str
    mentee_note: str
    images: list[ImageInput]
    # outputs
    perception: dict
    review: dict


PERCEIVE_SYSTEM = """You are the perception step of a code-mentoring tool.
You receive screenshots a student took of their solution (code editor, terminal, browser UI, diagrams).
Report only what is actually visible. Transcribe code and terminal output verbatim, preserving indentation;
mark unreadable fragments as [unreadable]. Do not judge quality yet."""

ASSESS_SYSTEM = """You are an experienced software mentor reviewing a student's solution from screenshots.
Judge the solution against the roadmap topic the student is working on. Be specific and kind but honest:
point to concrete lines or UI elements, separate real bugs from style nits, and give actionable next steps.
If something can't be verified from a static screenshot (e.g. runtime behaviour), list it in questions_for_mentor
instead of guessing. If the work is unrelated to the topic, use verdict "off_topic"."""


@lru_cache
def _client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key)


def _image_blocks(images: list[ImageInput]) -> list[dict]:
    blocks: list[dict] = []
    for i, img in enumerate(images, start=1):
        blocks.append({"type": "text", "text": f"Screenshot {i}:"})
        blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img["media_type"],
                    "data": base64.standard_b64encode(img["data"]).decode(),
                },
            }
        )
    return blocks


def _topic_text(state: ReviewState) -> str:
    path = " > ".join(state.get("topic_path") or [])
    parts = [f"Roadmap topic: {path}"]
    if state.get("topic_description"):
        parts.append(f"Topic description from the mentor:\n{state['topic_description']}")
    if state.get("mentee_note"):
        parts.append(f"Student's note:\n{state['mentee_note']}")
    return "\n\n".join(parts)


async def _parse(system: str, content: list[dict], output_format: type, effort: str):
    settings = get_settings()
    response = await _client().beta.messages.parse(
        model=settings.analysis_model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": content}],
        output_format=output_format,
        output_config={"effort": effort},
        # Re-run on a fallback model if a safety classifier declines.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("The model declined to analyse these screenshots")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise RuntimeError(f"Analysis did not complete (stop_reason={response.stop_reason})")
    return response.parsed_output


async def perceive(state: ReviewState) -> ReviewState:
    content = [
        {"type": "text", "text": _topic_text(state)},
        *_image_blocks(state["images"]),
        {"type": "text", "text": "Describe and transcribe what is visible in these screenshots."},
    ]
    result: Perception = await _parse(PERCEIVE_SYSTEM, content, Perception, effort="low")
    return {"perception": result.model_dump()}


def route_after_perceive(state: ReviewState) -> Literal["assess", "ask_for_resubmit"]:
    return "assess" if state["perception"]["is_readable"] else "ask_for_resubmit"


async def assess(state: ReviewState) -> ReviewState:
    p = state["perception"]
    grounding = (
        f"Perception step output (content type: {p['content_type']}):\n"
        f"<transcription>\n{p['transcription']}\n</transcription>\n"
        f"<ui>\n{p['ui_description']}\n</ui>\n"
        f"Visible errors: {p['visible_errors'] or 'none'}"
    )
    content = [
        {"type": "text", "text": _topic_text(state)},
        *_image_blocks(state["images"]),
        {"type": "text", "text": grounding},
        {"type": "text", "text": "Review this solution for the topic above."},
    ]
    result: Review = await _parse(
        ASSESS_SYSTEM, content, Review, effort=get_settings().analysis_effort
    )
    review = result.model_dump()
    review["score"] = max(0, min(100, review["score"]))
    return {"review": review}


async def ask_for_resubmit(state: ReviewState) -> ReviewState:
    reason = state["perception"].get("unreadable_reason") or "The screenshots could not be read."
    review = Review(
        verdict="unreadable",
        score=0,
        summary=f"Could not review the solution: {reason}",
        strengths=[],
        issues=[],
        suggestions=[
            "Take a sharper screenshot of the whole relevant area (code + output).",
            "Avoid cropping the code; split long files into several screenshots.",
        ],
        questions_for_mentor=[],
    )
    return {"review": review.model_dump()}


def build_graph():
    g = StateGraph(ReviewState)
    g.add_node("perceive", perceive)
    g.add_node("assess", assess)
    g.add_node("ask_for_resubmit", ask_for_resubmit)
    g.add_edge(START, "perceive")
    g.add_conditional_edges("perceive", route_after_perceive)
    g.add_edge("assess", END)
    g.add_edge("ask_for_resubmit", END)
    return g.compile()


review_graph = build_graph()
