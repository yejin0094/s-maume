import os

from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, AuthenticationError, OpenAI
from pydantic import BaseModel


app = FastAPI(title="S-MAUMe AI Agent")


class Message(BaseModel):
    message: str


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
    except APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="OpenAI service is unavailable",
        )
    return Message(message=response.output_text)
