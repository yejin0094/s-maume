from fastapi import FastAPI
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
