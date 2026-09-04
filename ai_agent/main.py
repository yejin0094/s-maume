import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, AuthenticationError, InternalServerError, OpenAI, RateLimitError
from pydantic import BaseModel


app = FastAPI(title="S-MAUMe AI Agent")


class Message(BaseModel):
    message: str


IntentLabel = Literal[
    "structured",
    "document",
    "relationship",
    "hybrid",
    "other",
]


class ClassifyResponse(BaseModel):
    intent: IntentLabel


CLASSIFICATION_INSTRUCTIONS = """\
Classify this campus question after an FAQ miss into exactly one intent:
- structured: Best answered by querying structured data such as PostgreSQL, including cafeteria menus, timetables, facility information, and structured campus operations data.
- document: Best answered by searching the text of notices, regulations, scholarship information, extracurricular program information, or academic documents.
- relationship: Best answered by exploring relationships between entities, including prerequisites, department or organizational relationships, building connections, locations, and travel routes.
- hybrid: Requires combining results from two or more different knowledge base types.
- other: Outside the current campus knowledge base or not clearly classifiable as one of the four intents above.
"""


def classify_intent(request: Message) -> ClassifyResponse:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key is not configured",
        )

    client = OpenAI()
    response = client.responses.parse(
        model="gpt-5.6-luna",
        instructions=CLASSIFICATION_INSTRUCTIONS,
        input=request.message,
        text_format=ClassifyResponse,
    )
    return response.output_parsed


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/echo", response_model=Message)
def echo(request: Message) -> Message:
    return request


@app.post("/generate", response_model=Message)
def generate(request: Message) -> Message:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key is not configured",
        )

    client = OpenAI()
    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            input=request.message,
        )
    except AuthenticationError:
        raise HTTPException(
            status_code=503,
            detail="OpenAI authentication failed",
        )
    except RateLimitError:
        raise HTTPException(
            status_code=503,
            detail="OpenAI rate limit exceeded",
        )
    except InternalServerError:
        raise HTTPException(
            status_code=503,
            detail="OpenAI server error",
        )
    except APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="OpenAI service is unavailable",
        )
    return Message(message=response.output_text)
