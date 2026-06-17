import hashlib
import html
import json
import re
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


# 네이버 뉴스 목록을 README 4-2 구조로 정규화
def normalize_naver_news_items(
    raw_news_items: list[dict[str, Any]],
    parsed_query: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for raw in raw_news_items:
        news = normalize_naver_news_item(raw, parsed_query=parsed_query)
        if news is not None and not _is_duplicate(news, normalized):
            normalized.append(news)

    return normalized


# 네이버 뉴스 1건을 README 4-2 구조로 정규화
def normalize_naver_news_item(
    raw: dict[str, Any],
    parsed_query: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    title = _clean_text(raw.get("title"))
    summary = _clean_text(raw.get("description"))
    url = str(raw.get("originallink") or raw.get("link") or "").strip()
    published_date = _normalize_pub_date(raw.get("pubDate"))

    if not title or not url:
        return None

    return {
        "news_id": _build_news_id(url),
        "title": title,
        "url": url,
        "published_date": published_date,
        "news_site": _extract_news_site(url),
        "region_tags": _build_region_tags(parsed_query),
        "policy_tags": _build_policy_tags(parsed_query),
        "sentiment_score": None,
        "market_signal": _infer_market_signal(f"{title} {summary}"),
        "summary": summary,
        "content": summary,
    }


# 정규화된 뉴스 데이터 JSONL 저장
def save_news(path: str | Path, news_items: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for news in news_items:
            f.write(json.dumps(news, ensure_ascii=False) + "\n")


# HTML 태그와 엔티티 제거
def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    unescaped = html.unescape(str(value))
    without_tags = re.sub(r"<[^>]+>", "", unescaped)
    return re.sub(r"\s+", " ", without_tags).strip()


# pubDate를 YYYY-MM-DD로 변환
def _normalize_pub_date(value: Any) -> str | None:
    if value in (None, ""):
        return None

    try:
        return parsedate_to_datetime(str(value)).date().isoformat()
    except (TypeError, ValueError, IndexError):
        return None


# URL 기반 뉴스 ID 생성
def _build_news_id(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"naver_news_{digest}"


# URL에서 언론사 도메인 추출
def _extract_news_site(url: str) -> str:
    host = urlparse(url).netloc
    return host.replace("www.", "") or "naver"


# 질문 분석 결과 기반 지역 태그 생성
def _build_region_tags(parsed_query: dict[str, Any] | None) -> list[str]:
    if parsed_query is None:
        return []

    tags = [tag for tag in (parsed_query.get("region"), parsed_query.get("dong")) if tag]
    return list(dict.fromkeys(str(tag) for tag in tags))


# 질문 분석 결과 기반 정책 태그 생성
def _build_policy_tags(parsed_query: dict[str, Any] | None) -> list[str]:
    if parsed_query is None or parsed_query.get("policy_type") is None:
        return []
    return [str(parsed_query["policy_type"])]


# 제목/요약 기반 시장 신호 추정
def _infer_market_signal(text: str) -> str:
    signal_rules = (
        ("거래 위축", ("거래절벽", "거래 위축", "매수세 둔화", "관망", "하락")),
        ("매수세 증가", ("매수세", "문의 증가", "수요 증가", "상승세")),
        ("전세 불안", ("전세", "전셋값", "역전세", "전세난")),
        ("신고가", ("신고가", "최고가")),
    )

    for signal, keywords in signal_rules:
        if any(keyword in text for keyword in keywords):
            return signal

    return "시장 반응"


# 뉴스 URL 중복 여부 확인
def _is_duplicate(news: dict[str, Any], existing_items: list[dict[str, Any]]) -> bool:
    return any(item["url"] == news["url"] for item in existing_items)
