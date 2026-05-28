import json
from pathlib import Path
from typing import Any, Iterable

from langchain_core.documents import Document


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source_path = Path(path)
    rows: list[dict[str, Any]] = []

    with source_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {source_path}:{line_number}") from exc

    return rows


def load_policy_documents(path: str | Path) -> list[Document]:
    return [
        Document(
            page_content=_join_content(
                row,
                fields=("title", "summary", "policy_type", "region_tags", "keywords"),
            ),
            metadata=_select_metadata(
                row,
                fields=(
                    "policy_id",
                    "title",
                    "url",
                    "published_date",
                    "effective_date",
                    "policy_type",
                    "region_tags",
                    "keywords",
                ),
            ),
        )
        for row in load_jsonl(path)
    ]


def load_news_documents(path: str | Path) -> list[Document]:
    return [
        Document(
            page_content=_join_content(
                row,
                fields=("title", "summary", "region_tags", "policy_tags", "market_signal"),
            ),
            metadata=_select_metadata(
                row,
                fields=(
                    "news_id",
                    "title",
                    "url",
                    "published_date",
                    "news_site",
                    "region_tags",
                    "policy_tags",
                    "sentiment_score",
                    "market_signal",
                ),
            ),
        )
        for row in load_jsonl(path)
    ]


def _join_content(row: dict[str, Any], fields: Iterable[str]) -> str:
    parts: list[str] = []

    for field in fields:
        value = row.get(field)
        if value is None or value == "":
            continue

        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)

        parts.append(f"{field}: {value}")

    return "\n".join(parts)


def _select_metadata(row: dict[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    return {field: row[field] for field in fields if field in row}
