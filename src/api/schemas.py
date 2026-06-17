from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=1)


class Sources(BaseModel):
    policies: list[str]
    news: list[str]


class AnalyzeResponse(BaseModel):
    answer: str
    parsed_query: dict[str, Any]
    market_summary: dict[str, Any]
    sources: Sources
    context: str
    agent_plan: dict[str, Any] = {}
