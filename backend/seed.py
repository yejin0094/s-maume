from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import FAQ


SEED_FAQS = [
    {
        "question": "도서관 몇 시까지 해?",
        "answer": "테스트용 안내: 중앙도서관 운영시간은 평일 09:00~22:00입니다.",
        "keywords": ["도서관", "운영시간", "몇시", "몇 시", "열어"],
        "category": "운영시간",
    },
    {
        "question": "학생처 전화번호 알려줘",
        "answer": "테스트용 학생처 전화번호 안내입니다. 실제 연락처는 학교 공식 안내를 확인해 주세요.",
        "keywords": ["학생처", "전화번호", "연락처"],
        "category": "연락처",
    },
    {
        "question": "학생식당 몇 시까지 해?",
        "answer": "테스트용 학생식당 운영시간 안내입니다. 실제 운영시간은 학교 공식 안내를 확인해 주세요.",
        "keywords": ["학생식당", "학식", "운영시간", "몇시", "몇 시"],
        "category": "운영시간",
    },
    {
        "question": "도서관 위치 알려줘",
        "answer": "테스트용 도서관 위치 안내입니다. 실제 위치는 학교 공식 안내를 확인해 주세요.",
        "keywords": ["도서관", "위치", "어디"],
        "category": "위치",
    },
    {
        "question": "교무처 운영시간 알려줘",
        "answer": "테스트용 교무처 운영시간 안내입니다. 실제 운영시간은 학교 공식 안내를 확인해 주세요.",
        "keywords": ["교무처", "운영시간", "몇시", "몇 시"],
        "category": "운영시간",
    },
    {
        "question": "증명서는 어디서 발급해?",
        "answer": "테스트용 증명서 발급 안내입니다. 실제 발급 방법은 학교 공식 안내를 확인해 주세요.",
        "keywords": ["증명서", "발급", "어디"],
        "category": "학사",
    },
]


def seed_faqs(db: Session) -> int:
    existing_questions = set(db.scalars(select(FAQ.question)).all())
    new_faqs = [
        FAQ(**faq) for faq in SEED_FAQS if faq["question"] not in existing_questions
    ]
    db.add_all(new_faqs)
    db.commit()
    return len(new_faqs)


def main() -> None:
    with SessionLocal() as db:
        created = seed_faqs(db)
    print(f"FAQ seed complete: {created} row(s) created")


if __name__ == "__main__":
    main()
