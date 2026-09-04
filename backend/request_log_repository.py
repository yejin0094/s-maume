from sqlalchemy.orm import Session

from models import RequestLog


def create_request_log(
    db: Session,
    *,
    session_id: str,
    masked_question: str,
    question_type: str,
    source: str,
    response_time_ms: int,
    llm_used: bool,
    success: bool,
) -> RequestLog:
    request_log = RequestLog(
        session_id=session_id,
        masked_question=masked_question,
        question_type=question_type,
        source=source,
        response_time_ms=response_time_ms,
        llm_used=llm_used,
        success=success,
    )
    db.add(request_log)
    db.commit()
    return request_log
