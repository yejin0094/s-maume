import os
from typing import Literal, NotRequired, TypedDict

from fastapi import FastAPI, HTTPException
from langgraph.graph import END, START, StateGraph
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


class ClassificationState(TypedDict):
    message: str
    intent: NotRequired[IntentLabel]


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
    try:
        response = client.responses.parse(
            model="gpt-5.6-luna",
            instructions=CLASSIFICATION_INSTRUCTIONS,
            input=request.message,
            text_format=ClassifyResponse,
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
    if response.output_parsed is None:
        raise HTTPException(
            status_code=502,
            detail="OpenAI response could not be parsed",
        )
    return response.output_parsed


def classification_node(
    state: ClassificationState,
) -> dict[str, IntentLabel]:
    result = classify_intent(
        Message(message=state["message"])
    )
    return {
        "intent": result.intent,
    }


workflow = StateGraph(ClassificationState)
workflow.add_node(
    "classification",
    classification_node,
)
workflow.add_edge(
    START,
    "classification",
)
workflow.add_edge(
    "classification",
    END,
)
classification_graph = workflow.compile()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/echo", response_model=Message)
def echo(request: Message) -> Message:
    return request


@app.post("/classify", response_model=ClassifyResponse)
def classify(request: Message) -> ClassifyResponse:
    result = classification_graph.invoke(
        {
            "message": request.message,
        }
    )
    return ClassifyResponse(
        intent=result["intent"],
    )


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
