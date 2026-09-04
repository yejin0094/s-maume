import os
import logging
import time
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from faq_repository import search_faq
from privacy import mask_personal_data
from request_log_repository import create_request_log
from schemas import FAQSearchRequest, FAQSearchResponse


app = FastAPI(title="S-MAUMe Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

AI_AGENT_BASE_URL = os.getenv("AI_AGENT_BASE_URL", "http://127.0.0.1:8001")
AI_AGENT_ECHO_URL = f"{AI_AGENT_BASE_URL.rstrip('/')}/echo"
logger = logging.getLogger(__name__)


class Message(BaseModel):
    message: str


def _anonymous_session_id(value: str | None) -> str:
    if value is not None:
        try:
            return str(UUID(value))
        except ValueError:
            pass
    return str(uuid4())


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/faq/search", response_model=FAQSearchResponse)
def faq_search(
    request: FAQSearchRequest,
    db: Session = Depends(get_db),
    session_id_header: str | None = Header(default=None, alias="X-Session-ID"),
) -> FAQSearchResponse:
    started_at = time.perf_counter()
    try:
        faq = search_faq(db, request.question)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="FAQ 데이터베이스에 연결할 수 없습니다.",
        ) from error

    response = FAQSearchResponse(
        found=faq is not None,
        answer=faq.answer if faq is not None else None,
    )
    response_time_ms = int((time.perf_counter() - started_at) * 1000)

    try:
        create_request_log(
            db,
            session_id=_anonymous_session_id(session_id_header),
            masked_question=mask_personal_data(request.question),
            question_type="faq",
            source="faq",
            response_time_ms=response_time_ms,
            llm_used=False,
            success=faq is not None,
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to save FAQ request log")

    return response


@app.post("/api/agent-test", response_model=Message)
async def agent_test(request: Message) -> Message:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(
                AI_AGENT_ECHO_URL,
                json={"message": request.message},
            )
            response.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError) as error:
        raise HTTPException(
            status_code=503,
            detail="AI Agent 연결 실패",
        ) from error

    return Message.model_validate(response.json())
