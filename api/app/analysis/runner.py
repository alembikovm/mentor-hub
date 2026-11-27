import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.analysis.graph import review_graph
from app.config import get_settings
from app.db import SessionLocal
from app.models import RoadmapNode, Submission, SubmissionStatus
from app.services import node_ancestors

log = logging.getLogger(__name__)


async def run_review(submission_id: str) -> None:
    async with SessionLocal() as session:
        sub = await session.scalar(
            select(Submission)
            .where(Submission.id == submission_id)
            .options(selectinload(Submission.images))
        )
        if sub is None:
            return
        node = await session.get(RoadmapNode, sub.node_id)
        ancestors = await node_ancestors(session, node)
        sub.status = SubmissionStatus.analyzing
        sub.error = None
        await session.commit()

        upload_dir = get_settings().upload_dir
        try:
            images = [
                {"media_type": img.media_type, "data": (upload_dir / img.path).read_bytes()}
                for img in sub.images
            ]
            result = await review_graph.ainvoke(
                {
                    "topic_path": [a.title for a in ancestors] + [node.title],
                    "topic_description": node.description,
                    "mentee_note": sub.note,
                    "images": images,
                }
            )
            sub.ai_review = {"perception": result["perception"], **result["review"]}
            sub.status = SubmissionStatus.done
        except Exception as exc:  # surface any failure to the UI
            log.exception("Review failed for submission %s", submission_id)
            sub.status = SubmissionStatus.failed
            sub.error = str(exc)[:2000]
        await session.commit()
