import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import main
from database import Base, get_db
from models import FAQ
from seed import SEED_FAQS, seed_faqs


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_faqs(session)
        yield session


@pytest.fixture
def client(db: Session) -> TestClient:
    def override_get_db():
        yield db

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


def test_backend_health_remains_available(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_faq_found_without_llm_or_agent(client: TestClient, monkeypatch) -> None:
    class AgentMustNotBeCalled:
        def __init__(self, *args, **kwargs):
            raise AssertionError("FAQ request called the AI Agent")

    monkeypatch.setattr(main.httpx, "AsyncClient", AgentMustNotBeCalled)
    response = client.post(
        "/api/faq/search", json={"question": "도서관 몇 시까지 열어?"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "found": True,
        "answer": "테스트용 안내: 중앙도서관 운영시간은 평일 09:00~22:00입니다.",
        "source": "faq",
        "llm_used": False,
    }


def test_faq_not_found(client: TestClient) -> None:
    response = client.post("/api/faq/search", json={"question": "오늘 비 와?"})

    assert response.status_code == 200
    assert response.json() == {
        "found": False,
        "answer": None,
        "source": "faq",
        "llm_used": False,
    }


def test_database_error_is_sanitized(client: TestClient, monkeypatch) -> None:
    def fail_search(*args, **kwargs):
        raise OperationalError("select", {}, Exception("database unavailable"))

    monkeypatch.setattr(main, "search_faq", fail_search)
    response = client.post("/api/faq/search", json={"question": "도서관"})

    assert response.status_code == 503
    assert response.json() == {"detail": "FAQ 데이터베이스에 연결할 수 없습니다."}


def test_seed_is_idempotent(db: Session) -> None:
    assert seed_faqs(db) == 0
    count = db.scalar(select(func.count()).select_from(FAQ))
    assert count == len(SEED_FAQS)
