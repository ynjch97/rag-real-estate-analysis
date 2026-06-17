from typing import Any

from src.agents.task_planner import (
    TASK_FORECAST,
    TASK_GENERAL,
    TASK_POLICY_IMPACT,
    TASK_PRICE_CAUSE,
    TASK_REGION_COMPARISON,
    AgentPlan,
    plan_agent_task,
)
from src.analysis.answer_generator import generate_agent_answer
from src.prices.market_analyzer import calculate_monthly_metrics
from src.prices.price_retriever import retrieve_or_collect_transactions
from src.retrieval.news_retriever import retrieve_news_documents
from src.retrieval.policy_retriever import retrieve_policy_documents
from src.workflows.market_impact_workflow import analyze_market_impact


# Agent Controller 기반 부동산 질문 분석 실행
def analyze_with_agent(query: str) -> dict[str, Any]:
    plan = plan_agent_task(query)

    if plan.task_type == TASK_POLICY_IMPACT:
        return _run_policy_impact_task(plan)
    if plan.task_type == TASK_REGION_COMPARISON:
        return _run_region_comparison_task(plan)
    if plan.task_type == TASK_PRICE_CAUSE:
        return _run_price_cause_task(plan)
    if plan.task_type == TASK_FORECAST:
        return _run_forecast_task(plan)

    return _run_general_task(plan)


# 정책 영향 분석 작업 실행
def _run_policy_impact_task(plan: AgentPlan) -> dict[str, Any]:
    result = analyze_market_impact(plan.query)
    result["agent_plan"] = plan.to_dict()
    result["parsed_query"]["task_type"] = plan.task_type
    return result


# 지역 비교 분석 작업 실행
def _run_region_comparison_task(plan: AgentPlan) -> dict[str, Any]:
    region_summaries = [_build_region_year_summary(region, plan.acc_year, plan.parsed_query) for region in plan.regions]
    news_items = _retrieve_news_for_regions(plan)
    market_summary = {
        "task_type": plan.task_type,
        "acc_year": plan.acc_year,
        "regions": region_summaries,
        "winner": _select_winner_region(region_summaries),
    }
    context = _format_agent_context(plan, [], news_items, market_summary)
    fallback_answer = _format_region_comparison_answer(plan, market_summary, news_items)

    return _build_agent_result(
        plan=plan,
        policies=[],
        news_items=news_items,
        monthly_metrics=[],
        market_summary=market_summary,
        answer=generate_agent_answer(plan.parsed_query, [], news_items, market_summary, context, fallback_answer),
    )


# 가격 상승 원인 분석 작업 실행
def _run_price_cause_task(plan: AgentPlan) -> dict[str, Any]:
    policies = retrieve_policy_documents(plan.parsed_query, query=plan.query)
    news_items = retrieve_news_documents(plan.parsed_query, query=plan.query)
    region = _first_region(plan)
    region_summary = _build_region_year_summary(region, plan.acc_year, plan.parsed_query) if region else {}
    market_summary = {
        "task_type": plan.task_type,
        "acc_year": plan.acc_year,
        "region": region,
        "price_summary": region_summary,
    }
    context = _format_agent_context(plan, policies, news_items, market_summary)
    fallback_answer = _format_price_cause_answer(plan, policies, news_items, market_summary)

    return _build_agent_result(
        plan=plan,
        policies=policies,
        news_items=news_items,
        monthly_metrics=region_summary.get("monthly_metrics", []),
        market_summary=market_summary,
        answer=generate_agent_answer(plan.parsed_query, policies, news_items, market_summary, context, fallback_answer),
    )


# 전망 질문 분석 작업 실행
def _run_forecast_task(plan: AgentPlan) -> dict[str, Any]:
    region = _first_region(plan)
    preferred_base_year = plan.acc_year - 1 if "내년" in plan.query else plan.acc_year
    news_items = retrieve_news_documents(plan.parsed_query, query=plan.query)
    policies = retrieve_policy_documents(plan.parsed_query, query=plan.query)
    region_summary = _build_latest_available_region_summary(region, preferred_base_year, plan.parsed_query) if region else {}
    market_summary = {
        "task_type": plan.task_type,
        "acc_year": plan.acc_year,
        "base_year": region_summary.get("acc_year") or preferred_base_year,
        "region": region,
        "price_summary": region_summary,
    }
    context = _format_agent_context(plan, policies, news_items, market_summary)
    fallback_answer = _format_forecast_answer(plan, policies, news_items, market_summary)

    return _build_agent_result(
        plan=plan,
        policies=policies,
        news_items=news_items,
        monthly_metrics=region_summary.get("monthly_metrics", []),
        market_summary=market_summary,
        answer=generate_agent_answer(plan.parsed_query, policies, news_items, market_summary, context, fallback_answer),
    )


# 일반 검색 작업 실행
def _run_general_task(plan: AgentPlan) -> dict[str, Any]:
    result = analyze_market_impact(plan.query)
    result["agent_plan"] = plan.to_dict()
    result["parsed_query"]["task_type"] = TASK_GENERAL
    return result


# 지역/연도 기준 시세 요약 생성
def _build_region_year_summary(region: str, acc_year: int, parsed_query: dict[str, Any]) -> dict[str, Any]:
    transactions = retrieve_or_collect_transactions(
        region=region,
        acc_year=acc_year,
        dong=parsed_query.get("dong") if parsed_query.get("region") == region else None,
        transaction_type=_to_korean_transaction_type(parsed_query.get("transaction_type")),
    )
    monthly_metrics = calculate_monthly_metrics(transactions)
    region_metrics = [metric for metric in monthly_metrics if metric["region"] == region]
    comparable_metrics = _filter_comparable_monthly_metrics(region_metrics)
    before_metrics, after_metrics = _split_comparison_windows(comparable_metrics)
    before_avg_price_per_m2 = _safe_average([metric["price_per_m2"] for metric in before_metrics])
    after_avg_price_per_m2 = _safe_average([metric["price_per_m2"] for metric in after_metrics])
    price_change_rate = _calculate_change_rate(after_avg_price_per_m2, before_avg_price_per_m2)

    return {
        "region": region,
        "acc_year": acc_year,
        "first_month": before_metrics[0]["month"] if before_metrics else None,
        "last_month": after_metrics[-1]["month"] if after_metrics else None,
        "first_avg_price": _safe_average([metric["avg_price"] for metric in before_metrics]),
        "last_avg_price": _safe_average([metric["avg_price"] for metric in after_metrics]),
        "first_price_per_m2": before_avg_price_per_m2,
        "last_price_per_m2": after_avg_price_per_m2,
        "price_change_rate": price_change_rate,
        "price_change_warning": _build_price_change_warning(price_change_rate, len(comparable_metrics)),
        "comparison_basis": "초반 3개월 평균 ㎡당 가격 대비 후반 3개월 평균 ㎡당 가격",
        "total_transaction_count": sum(int(metric["transaction_count"]) for metric in region_metrics),
        "monthly_metrics": region_metrics,
    }


# 최근 수집 가능한 연도 기준 시세 요약 생성
def _build_latest_available_region_summary(
    region: str,
    preferred_year: int,
    parsed_query: dict[str, Any],
    max_lookback_years: int = 3,
) -> dict[str, Any]:
    for year in range(preferred_year, preferred_year - max_lookback_years - 1, -1):
        summary = _build_region_year_summary(region, year, parsed_query)
        if summary.get("monthly_metrics"):
            return summary

    return _build_region_year_summary(region, preferred_year, parsed_query)


# 지역별 뉴스 조회
def _retrieve_news_for_regions(plan: AgentPlan) -> list[dict[str, Any]]:
    news_items: list[dict[str, Any]] = []
    for region in plan.regions:
        parsed_query = dict(plan.parsed_query)
        parsed_query["region"] = region
        news_items.extend(retrieve_news_documents(parsed_query, query=f"{plan.acc_year}년 {region} 집값"))
    return _deduplicate_by_id(news_items, "news_id")


# Agent 결과 공통 구조 생성
def _build_agent_result(
    plan: AgentPlan,
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    monthly_metrics: list[dict[str, Any]],
    market_summary: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    parsed_query = dict(plan.parsed_query)
    parsed_query["task_type"] = plan.task_type

    return {
        "answer": answer,
        "parsed_query": parsed_query,
        "policies": policies,
        "news": news_items,
        "monthly_metrics": monthly_metrics,
        "market_summary": market_summary,
        "context": _format_agent_context(plan, policies, news_items, market_summary),
        "agent_plan": plan.to_dict(),
    }


# 지역 비교 답변 생성
def _format_region_comparison_answer(plan: AgentPlan, market_summary: dict[str, Any], news_items: list[dict[str, Any]]) -> str:
    winner = market_summary.get("winner")
    return "\n".join(
        [
            "[질문 해석]",
            f"- 질문 유형: 지역 비교",
            f"- 비교 지역: {', '.join(plan.regions)}",
            f"- 기준 연도: {plan.acc_year}",
            "",
            "[결론 요약]",
            f"- 가격 상승률 기준으로는 {winner or '판단 불가'}가 더 높게 나타났습니다.",
            "",
            "[시세 변화 데이터]",
            _format_region_summaries(market_summary.get("regions", [])),
            "",
            "[관련 뉴스 요약]",
            _format_news(news_items),
            "",
            "[정책과 시세의 관계 해석]",
            "- 지역별 상승률 차이는 거래량, 선호 단지, 정책·뉴스 신호를 함께 봐야 합니다.",
            "",
            "[불확실성 및 추가 확인 필요 사항]",
            "- 현재 비교는 수집된 실거래 데이터 범위 안에서만 계산한 결과입니다.",
            "",
            "[참고 출처]",
            _format_sources([], news_items),
        ]
    )


# 가격 상승 원인 답변 생성
def _format_price_cause_answer(
    plan: AgentPlan,
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
) -> str:
    region = market_summary.get("region") or "대상 지역"
    price_summary = market_summary.get("price_summary", {})
    return "\n".join(
        [
            "[질문 해석]",
            f"- 질문 유형: 가격 상승 원인 분석",
            f"- 지역/기간: {region} / {plan.acc_year}",
            "",
            "[결론 요약]",
            f"- {region}의 비교 기준 가격 변화율은 {_format_percent(price_summary.get('price_change_rate'))}입니다.",
            f"- 비교 기준: {price_summary.get('comparison_basis') or '미확인'}",
            _format_warning(price_summary.get("price_change_warning")),
            "- 상승 원인은 정책, 뉴스 반응, 거래 데이터가 동시에 뒷받침하는 범위에서만 해석해야 합니다.",
            "",
            "[정책 근거]",
            _format_policies(policies),
            "",
            "[관련 뉴스 요약]",
            _format_news(news_items),
            "",
            "[시세 변화 데이터]",
            _format_single_region_summary(price_summary),
            "",
            "[정책과 시세의 관계 해석]",
            "- 정책 → 뉴스 → 시세 순서로 확인한 결과를 종합해 원인 후보를 좁히는 방식입니다.",
            "",
            "[불확실성 및 추가 확인 필요 사항]",
            "- 실제 원인은 단일 요인으로 단정하지 않고 거래량, 공급, 금리, 지역 선호를 함께 확인해야 합니다.",
            "",
            "[참고 출처]",
            _format_sources(policies, news_items),
        ]
    )


# 전망 답변 생성
def _format_forecast_answer(
    plan: AgentPlan,
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
) -> str:
    region = market_summary.get("region") or "대상 지역"
    price_summary = market_summary.get("price_summary", {})
    return "\n".join(
        [
            "[질문 해석]",
            f"- 질문 유형: 전망 질문",
            f"- 지역/전망 연도: {region} / {plan.acc_year}",
            "",
            "[결론 요약]",
            "- 제공된 데이터만으로 미래 가격을 단정 예측하지 않습니다.",
            f"- 최근 기준 연도({market_summary.get('base_year')})의 가격 변화율은 {_format_percent(price_summary.get('price_change_rate'))}입니다.",
            "",
            "[정책 근거]",
            _format_policies(policies),
            "",
            "[관련 뉴스 요약]",
            _format_news(news_items),
            "",
            "[시세 변화 데이터]",
            _format_single_region_summary(price_summary),
            "",
            "[정책과 시세의 관계 해석]",
            "- 최근 시세 흐름과 뉴스 신호가 같은 방향이면 해당 방향의 가능성을 참고하고, 엇갈리면 관망으로 해석합니다.",
            "",
            "[불확실성 및 추가 확인 필요 사항]",
            "- 전망은 금리, 공급, 거래량, 정책 변화에 따라 달라질 수 있습니다.",
            "",
            "[참고 출처]",
            _format_sources(policies, news_items),
        ]
    )


# Agent 컨텍스트 문자열 생성
def _format_agent_context(
    plan: AgentPlan,
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
) -> str:
    return "\n\n".join(
        [
            "[Agent Plan]",
            f"- task_type: {plan.task_type}",
            f"- retrieval_steps: {' -> '.join(plan.retrieval_steps)}",
            f"- reasoning_strategy: {plan.reasoning_strategy}",
            "[정책 근거]",
            _format_policies(policies),
            "[관련 뉴스 요약]",
            _format_news(news_items),
            "[시세 변화 데이터]",
            str(market_summary),
        ]
    )


# 지역별 시세 요약 문자열 생성
def _format_region_summaries(region_summaries: list[dict[str, Any]]) -> str:
    if not region_summaries:
        return "- 계산 가능한 지역 시세 데이터 없음"

    return "\n".join(_format_single_region_summary(summary) for summary in region_summaries)


# 단일 지역 시세 요약 문자열 생성
def _format_single_region_summary(summary: dict[str, Any]) -> str:
    if not summary:
        return "- 계산 가능한 시세 데이터 없음"
    return (
        f"- {summary.get('region')}: {summary.get('first_month') or '미확인'} "
        f"㎡당 {_format_number(summary.get('first_price_per_m2'))} → "
        f"{summary.get('last_month') or '미확인'} ㎡당 {_format_number(summary.get('last_price_per_m2'))}, "
        f"변화율 {_format_percent(summary.get('price_change_rate'))}, "
        f"거래건수 {_format_number(summary.get('total_transaction_count'))}"
    )


# 가격 변화율 경고 문구 생성
def _build_price_change_warning(price_change_rate: float | None, comparable_month_count: int) -> str | None:
    if comparable_month_count < 6:
        return "비교 가능한 월 데이터가 6개월 미만이라 변화율 신뢰도가 낮습니다."
    if price_change_rate is not None and abs(price_change_rate) >= 30:
        return "변화율이 비정상적으로 커서 표본 구성, 면적, 거래유형 혼입 여부 확인이 필요합니다."
    return None


# 경고 문구 문자열 변환
def _format_warning(value: str | None) -> str:
    if not value:
        return "- 데이터 품질 경고: 없음"
    return f"- 데이터 품질 경고: {value}"


# 정책 목록 문자열 생성
def _format_policies(policies: list[dict[str, Any]]) -> str:
    if not policies:
        return "- 관련 정책 없음"
    return "\n".join(
        f"- {policy.get('title')} ({policy.get('published_date') or '일자 미확인'}): {policy.get('summary')}"
        for policy in policies
    )


# 뉴스 목록 문자열 생성
def _format_news(news_items: list[dict[str, Any]]) -> str:
    if not news_items:
        return "- 관련 뉴스 없음"
    return "\n".join(
        f"- {news.get('title')} ({news.get('published_date') or '일자 미확인'}, {news.get('market_signal') or '시장 신호 미확인'}): {news.get('summary')}"
        for news in news_items[:5]
    )


# 참고 출처 문자열 생성
def _format_sources(policies: list[dict[str, Any]], news_items: list[dict[str, Any]]) -> str:
    sources = [f"- 정책: {policy.get('policy_id')} {policy.get('url')}" for policy in policies]
    sources.extend(f"- 뉴스: {news.get('news_id')} {news.get('url')}" for news in news_items[:5])
    return "\n".join(sources) if sources else "- 참고 출처 없음"


# 상승률 기준 우위 지역 선택
def _select_winner_region(region_summaries: list[dict[str, Any]]) -> str | None:
    valid_summaries = [summary for summary in region_summaries if summary.get("price_change_rate") is not None]
    if not valid_summaries:
        return None
    return max(valid_summaries, key=lambda summary: summary["price_change_rate"]).get("region")


# 첫 번째 지역 조회
def _first_region(plan: AgentPlan) -> str | None:
    if plan.regions:
        return plan.regions[0]
    if plan.parsed_query.get("region"):
        return str(plan.parsed_query["region"])
    return None


# 거래유형 값을 한국어로 변환
def _to_korean_transaction_type(transaction_type: str | None) -> str | None:
    mapping = {
        "sale": "매매",
        "jeonse": "전세",
        "monthly_rent": "월세",
    }
    return mapping.get(transaction_type, transaction_type)


# 변화율 계산
def _calculate_change_rate(current: Any, previous: Any) -> float | None:
    if current is None or previous is None or float(previous) == 0:
        return None
    return round(((float(current) - float(previous)) / float(previous)) * 100, 2)


# 비교 가능한 월별 지표만 조회
def _filter_comparable_monthly_metrics(monthly_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        metric
        for metric in monthly_metrics
        if metric.get("price_per_m2") is not None
    ]


# 비교 구간 분리
def _split_comparison_windows(monthly_metrics: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if len(monthly_metrics) >= 6:
        return monthly_metrics[:3], monthly_metrics[-3:]
    if len(monthly_metrics) >= 2:
        return [monthly_metrics[0]], [monthly_metrics[-1]]
    return monthly_metrics, []


# 평균값 안전 계산
def _safe_average(values: list[Any]) -> float | None:
    numeric_values = [float(value) for value in values if value is not None]
    if not numeric_values:
        return None
    return sum(numeric_values) / len(numeric_values)


# ID 기준 중복 제거
def _deduplicate_by_id(items: list[dict[str, Any]], id_field: str) -> list[dict[str, Any]]:
    seen = set()
    unique_items = []
    for item in items:
        item_id = item.get(id_field)
        if item_id in seen:
            continue
        seen.add(item_id)
        unique_items.append(item)
    return unique_items


# 숫자 값 문자열 변환
def _format_number(value: Any) -> str:
    if value is None:
        return "계산 불가"
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    return str(value)


# 퍼센트 값 문자열 변환
def _format_percent(value: Any) -> str:
    if value is None:
        return "계산 불가"
    return f"{value}%"
