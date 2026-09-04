from fastapi import FastAPI
from openai import OpenAI
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
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5.6-luna",
        input=request.message,
    )
    return Message(message=response.output_text)
