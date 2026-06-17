from datetime import date
from pathlib import Path
from typing import Any

from src.analysis.answer_generator import generate_market_impact_answer
from src.analysis.context_builder import build_market_impact_context
from src.analysis.knowledge_graph import build_market_knowledge_graph
from src.prices.market_analyzer import calculate_monthly_metrics, summarize_before_after
from src.prices.price_retriever import DEFAULT_TRANSACTION_PATH, retrieve_or_collect_transactions
from src.retrieval.news_retriever import retrieve_news_documents
from src.retrieval.policy_retriever import retrieve_policy_documents
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
    policies = retrieve_policy_documents(parsed_query, query=query, fallback_path=policy_path)
    news_items = retrieve_news_documents(parsed_query, query=query, fallback_path=news_path)
    policy_month = _select_policy_month(policies)

    transactions = retrieve_or_collect_transactions(
        region=parsed_query["region"],
        acc_year=_select_transaction_year(parsed_query, policy_month),
        dong=parsed_query["dong"],
        transaction_type=_to_korean_transaction_type(parsed_query["transaction_type"]),
        fallback_path=transaction_path,
    )
    monthly_metrics = calculate_monthly_metrics(transactions)
    market_summary = summarize_before_after(
        monthly_metrics,
        region=parsed_query["region"],
        policy_month=policy_month,
        months_before=parsed_query["months_before"],
        months_after=parsed_query["months_after"],
    )
    if parsed_query.get("dong") is not None:
        market_summary["dong"] = parsed_query["dong"]
    knowledge_graph = build_market_knowledge_graph(parsed_query, policies, news_items, market_summary)
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
        "knowledge_graph": knowledge_graph.to_dict(),
    }


# 정책 발표일 기준 분석 월 선택
def _select_policy_month(policies: list[dict[str, Any]]) -> str:
    if not policies:
        return date.today().strftime("%Y-%m")

    policy_date = policies[0].get("effective_date") or policies[0].get("published_date")
    return str(policy_date)[:7]


# 시세 수집 기준 연도 선택
def _select_transaction_year(parsed_query: dict[str, Any], policy_month: str) -> int:
    if parsed_query.get("acc_year") is not None:
        return int(parsed_query["acc_year"])

    try:
        return int(policy_month[:4])
    except (TypeError, ValueError):
        return date.today().year


# 분석기 거래유형 값을 샘플 데이터의 한국어 값으로 변환
def _to_korean_transaction_type(transaction_type: str | None) -> str | None:
    mapping = {
        "sale": "매매",
        "jeonse": "전세",
        "monthly_rent": "월세",
    }
    return mapping.get(transaction_type, transaction_type)
