import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import FAQ


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def search_faq(db: Session, question: str) -> FAQ | None:
    """Return the active FAQ with the most keyword matches."""
    normalized_question = _normalize(question)
    faqs = db.scalars(select(FAQ).where(FAQ.is_active.is_(True))).all()

    best_faq: FAQ | None = None
    best_score = (0, 0)

    for faq in faqs:
        matched = {
            normalized_keyword
            for keyword in faq.keywords
            if (normalized_keyword := _normalize(keyword))
            and normalized_keyword in normalized_question
        }
        score = (len(matched), sum(len(keyword) for keyword in matched))
        if score > best_score:
            best_faq = faq
            best_score = score

    return best_faq
