import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import main


def make_fake_openai(output_parsed=None, error: Exception | None = None):
    class FakeResponses:
        def parse(self, **kwargs):
            if error is not None:
                raise error
            return type("FakeResponse", (), {"output_parsed": output_parsed})()

    class FakeOpenAI:
        def __init__(self):
            self.responses = FakeResponses()

    return FakeOpenAI


def make_openai_error(error_type, status_code: int) -> Exception:
    request = httpx.Request(
        "POST",
        "https://api.openai.com/v1/responses",
    )
    if error_type is main.APIConnectionError:
        return error_type(request=request)

    response = httpx.Response(status_code, request=request)
    return error_type(
        "test error",
        response=response,
        body=None,
    )


def test_classify_intent_returns_structured(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    parsed = main.ClassifyResponse(intent="structured")
    monkeypatch.setattr(main, "OpenAI", make_fake_openai(parsed))

    result = main.classify_intent(main.Message(message="test"))

    assert result.intent == "structured"


def test_classify_intent_requires_api_key(monkeypatch) -> None:
    class OpenAIMustNotBeCreated:
        def __init__(self):
            raise AssertionError("OpenAI client was created without an API key")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(main, "OpenAI", OpenAIMustNotBeCreated)

    with pytest.raises(HTTPException) as exc_info:
        main.classify_intent(main.Message(message="test"))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "OpenAI API key is not configured"


@pytest.mark.parametrize(
    ("error_type", "status_code", "detail"),
    [
        (main.AuthenticationError, 401, "OpenAI authentication failed"),
        (main.RateLimitError, 429, "OpenAI rate limit exceeded"),
        (main.InternalServerError, 500, "OpenAI server error"),
        (main.APIConnectionError, 0, "OpenAI service is unavailable"),
    ],
)
def test_classify_intent_maps_openai_errors(
    monkeypatch,
    error_type,
    status_code: int,
    detail: str,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    error = make_openai_error(error_type, status_code)
    monkeypatch.setattr(
        main,
        "OpenAI",
        make_fake_openai(error=error),
    )

    with pytest.raises(HTTPException) as exc_info:
        main.classify_intent(main.Message(message="test"))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == detail


def test_classify_intent_rejects_unparsed_response(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(main, "OpenAI", make_fake_openai())

    with pytest.raises(HTTPException) as exc_info:
        main.classify_intent(main.Message(message="test"))

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "OpenAI response could not be parsed"


def test_classify_endpoint_returns_only_intent(monkeypatch) -> None:
    calls: list[dict[str, str]] = []

    class FakeGraph:
        def invoke(self, state: dict[str, str]) -> dict[str, str]:
            calls.append(state)
            return {
                "message": "test",
                "intent": "structured",
            }

    monkeypatch.setattr(main, "classification_graph", FakeGraph())

    with TestClient(main.app) as client:
        response = client.post(
            "/classify",
            json={"message": "test"},
        )

    assert response.status_code == 200
    assert response.json() == {"intent": "structured"}
    assert calls == [{"message": "test"}]
