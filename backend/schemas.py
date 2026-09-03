from pydantic import BaseModel, Field


class FAQSearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class FAQSearchResponse(BaseModel):
    found: bool
    answer: str | None
    source: str = "faq"
    llm_used: bool = False
