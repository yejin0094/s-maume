import os
from uuid import UUID, uuid4

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import main
from database import Base, get_db
from models import RequestLog
from privacy import mask_personal_data
from seed import seed_faqs


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


def test_masks_name_student_id_and_hyphenated_phone() -> None:
    original = (
        "제 이름은 김민지이고 학번은 2026123456이에요. "
        "전화번호는 010-1234-5678입니다."
    )

    masked = mask_personal_data(original)

    assert masked == (
        "제 이름은 ***이고 학번은 **********이에요. "
        "전화번호는 ***-****-****입니다."
    )
    assert "김민지" not in masked
    assert "2026123456" not in masked
    assert "010-1234-5678" not in masked


@pytest.mark.parametrize(
    "phone",
    ["010-1234-5678", "010 1234 5678", "01012345678"],
)
def test_normalizes_supported_phone_formats(phone: str) -> None:
    assert mask_personal_data(phone) == "***-****-****"


def test_masks_explicit_name_contexts() -> None:
    assert mask_personal_data("제 이름은 김민지입니다.") == "제 이름은 ***입니다."
    assert mask_personal_data("이름: 김민지") == "이름: ***"


def test_preserves_general_text_and_empty_string() -> None:
    assert mask_personal_data("도서관 몇 시까지 해?") == "도서관 몇 시까지 해?"
    assert mask_personal_data("") == ""


def test_faq_request_saves_anonymous_masked_log(
    client: TestClient,
    db: Session,
) -> None:
    session_id = str(uuid4())
    question = (
        "제 이름은 김민지이고 학번은 2026123456이에요. "
        "전화번호는 010-1234-5678이고 도서관 몇 시까지 해?"
    )

    response = client.post(
        "/api/faq/search",
        json={"question": question},
        headers={"X-Session-ID": session_id},
    )

    assert response.status_code == 200
    request_log = db.scalar(select(RequestLog))
    assert request_log is not None
    assert request_log.session_id == session_id
    assert request_log.masked_question == (
        "제 이름은 ***이고 학번은 **********이에요. "
        "전화번호는 ***-****-****이고 도서관 몇 시까지 해?"
    )
    assert "김민지" not in request_log.masked_question
    assert "2026123456" not in request_log.masked_question
    assert "010-1234-5678" not in request_log.masked_question
    assert request_log.question_type == "faq"
    assert request_log.source == "faq"
    assert request_log.llm_used is False
    assert request_log.success is True
    assert request_log.response_time_ms >= 0
    assert request_log.created_at is not None


@pytest.mark.parametrize("header_value", [None, "abc123"])
def test_missing_or_invalid_session_id_is_replaced(
    client: TestClient,
    db: Session,
    header_value: str | None,
) -> None:
    headers = {"X-Session-ID": header_value} if header_value is not None else {}

    response = client.post(
        "/api/faq/search",
        json={"question": "도서관 몇 시까지 해?"},
        headers=headers,
    )

    assert response.status_code == 200
    request_log = db.scalar(select(RequestLog))
    assert request_log is not None
    assert str(UUID(request_log.session_id)) == request_log.session_id
    assert request_log.session_id != header_value


def test_faq_not_found_saves_unsuccessful_log(
    client: TestClient,
    db: Session,
) -> None:
    response = client.post(
        "/api/faq/search",
        json={"question": "오늘 비 와?"},
    )

    assert response.status_code == 200
    assert response.json()["found"] is False
    request_log = db.scalar(select(RequestLog))
    assert request_log is not None
    assert request_log.question_type == "faq"
    assert request_log.source == "faq"
    assert request_log.llm_used is False
    assert request_log.success is False


def test_log_failure_does_not_break_faq_response_or_expose_question(
    client: TestClient,
    monkeypatch,
) -> None:
    private_question = "제 이름은 김민지이고 도서관 몇 시까지 해?"

    def fail_log(*args, **kwargs):
        raise OperationalError("insert", {}, Exception("log unavailable"))

    monkeypatch.setattr(main, "create_request_log", fail_log)
    response = client.post(
        "/api/faq/search",
        json={"question": private_question},
    )

    assert response.status_code == 200
    assert response.json() == {
        "found": True,
        "answer": "테스트용 안내: 중앙도서관 운영시간은 평일 09:00~22:00입니다.",
        "source": "faq",
        "llm_used": False,
    }
    assert "김민지" not in response.text
