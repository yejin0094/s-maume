import os

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from faq_repository import search_faq
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


class Message(BaseModel):
    message: str


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/faq/search", response_model=FAQSearchResponse)
def faq_search(
    request: FAQSearchRequest,
    db: Session = Depends(get_db),
) -> FAQSearchResponse:
    try:
        faq = search_faq(db, request.question)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="FAQ 데이터베이스에 연결할 수 없습니다.",
        ) from error

    if faq is None:
        return FAQSearchResponse(found=False, answer=None)

    return FAQSearchResponse(found=True, answer=faq.answer)


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
