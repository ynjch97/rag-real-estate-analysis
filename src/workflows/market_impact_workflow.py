from datetime import date
from pathlib import Path
from typing import Any

from src.analysis.answer_generator import generate_market_impact_answer
from src.analysis.context_builder import build_market_impact_context
from src.data.loaders import load_jsonl
from src.prices.market_analyzer import calculate_monthly_metrics, summarize_before_after
from src.prices.price_retriever import DEFAULT_TRANSACTION_PATH, retrieve_transactions
from src.retrieval.query_analyzer import analyze_query


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "data" / "sample" / "policies.jsonl"
DEFAULT_NEWS_PATH = PROJECT_ROOT / "data" / "sample" / "news.jsonl"


# 부동산 시장 영향 분석 워크플로우 실행
def analyze_market_impact(
    query: str,
    policy_path: str | Path = DEFAULT_POLICY_PATH,
    news_path: str | Path = DEFAULT_NEWS_PATH,
    transaction_path: str | Path = DEFAULT_TRANSACTION_PATH,
) -> dict[str, Any]:
    parsed_query = analyze_query(query).to_dict()
    policies = find_related_policies(parsed_query, policy_path)
    news_items = find_related_news(parsed_query, news_path)
    policy_month = _select_policy_month(policies)

    transactions = retrieve_transactions(
        region=parsed_query["region"],
        transaction_type=_to_korean_transaction_type(parsed_query["transaction_type"]),
        path=transaction_path,
    )
    monthly_metrics = calculate_monthly_metrics(transactions)
    market_summary = summarize_before_after(
        monthly_metrics,
        region=parsed_query["region"],
        policy_month=policy_month,
        months_before=parsed_query["months_before"],
        months_after=parsed_query["months_after"],
    )
    context = build_market_impact_context(parsed_query, policies, news_items, market_summary)
    answer = generate_market_impact_answer(parsed_query, policies, news_items, market_summary, context)

    return {
        "answer": answer,
        "parsed_query": parsed_query,
        "policies": policies,
        "news": news_items,
        "monthly_metrics": monthly_metrics,
        "market_summary": market_summary,
        "context": context,
    }


# 질문 분석 결과와 관련된 정책 샘플 조회
def find_related_policies(
    parsed_query: dict[str, Any],
    policy_path: str | Path = DEFAULT_POLICY_PATH,
    limit: int = 3,
) -> list[dict[str, Any]]:
    policies = load_jsonl(policy_path)
    region = parsed_query.get("region")
    policy_type = parsed_query.get("policy_type")
    event_keyword = parsed_query.get("event_keyword")

    matched = [
        policy
        for policy in policies
        if _matches_region_tag(policy, region)
        and (
            policy_type is None
            or policy.get("policy_type") == policy_type
            or _contains_keyword(policy.get("keywords", []), event_keyword)
        )
    ]
    return matched[:limit]


# 질문 분석 결과와 관련된 뉴스 샘플 조회
def find_related_news(
    parsed_query: dict[str, Any],
    news_path: str | Path = DEFAULT_NEWS_PATH,
    limit: int = 5,
) -> list[dict[str, Any]]:
    news_items = load_jsonl(news_path)
    region = parsed_query.get("region")
    policy_type = parsed_query.get("policy_type")

    matched = [
        news
        for news in news_items
        if _matches_region_tag(news, region)
        and (policy_type is None or policy_type in news.get("policy_tags", []))
    ]
    return matched[:limit]


# 정책 발표일 기준 분석 월 선택
def _select_policy_month(policies: list[dict[str, Any]]) -> str:
    if not policies:
        return date.today().strftime("%Y-%m")

    policy_date = policies[0].get("effective_date") or policies[0].get("published_date")
    return str(policy_date)[:7]


# 분석기 거래유형 값을 샘플 데이터의 한국어 값으로 변환
def _to_korean_transaction_type(transaction_type: str | None) -> str | None:
    mapping = {
        "sale": "매매",
        "jeonse": "전세",
        "monthly_rent": "월세",
    }
    return mapping.get(transaction_type, transaction_type)


# 지역 태그에 요청 지역이 포함되는지 확인
def _matches_region_tag(item: dict[str, Any], region: str | None) -> bool:
    if region is None:
        return True
    return region in item.get("region_tags", [])


# 키워드 목록에 검색 키워드가 포함되는지 확인
def _contains_keyword(keywords: list[str], keyword: str | None) -> bool:
    if keyword is None:
        return False
    return any(keyword in value or value in keyword for value in keywords)
