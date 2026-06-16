from typing import Any


# README 7-3 구조 기반 LLM 입력 컨텍스트 구성
def build_market_impact_context(
    parsed_query: dict[str, Any],
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
) -> str:
    return "\n\n".join(
        [
            "[질문 해석]",
            _format_query(parsed_query),
            "[결론 요약]",
            _format_conclusion(market_summary),
            "[정책 근거]",
            _format_policies(policies),
            "[관련 뉴스 요약]",
            _format_news(news_items),
            "[시세 변화 데이터]",
            _format_market_summary(market_summary),
            "[정책과 시세의 관계 해석]",
            "정책 정보, 뉴스 반응, 시세 변화 데이터가 함께 제공된 범위 안에서만 관계를 해석한다.",
            "[불확실성 및 추가 확인 필요 사항]",
            "샘플 데이터 기반 결과이므로 실제 투자 판단에는 최신 실거래가, 정책 원문, 추가 뉴스 확인이 필요하다.",
            "[참고 출처]",
            _format_sources(policies, news_items),
            "[제약 조건]",
            "제공된 정보에 없는 내용은 추측하지 않는다.",
        ]
    )


# 질문 분석 결과를 컨텍스트 문자열로 변환
def _format_query(parsed_query: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- 지역/기간: {parsed_query.get('region') or '미확인'} / 전 {parsed_query.get('months_before')}개월, 후 {parsed_query.get('months_after')}개월",
            f"- 정책 이벤트: {parsed_query.get('event_keyword') or '미확인'}",
        ]
    )


# 결론 요약을 컨텍스트 문자열로 변환
def _format_conclusion(market_summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- 평균 매매가 변화율: {_format_percent(market_summary.get('price_change_rate'))}",
            f"- 거래량 변화율: {_format_percent(market_summary.get('transaction_count_change_rate'))}",
        ]
    )


# 정책 검색 결과를 컨텍스트 문자열로 변환
def _format_policies(policies: list[dict[str, Any]]) -> str:
    if not policies:
        return "- 관련 정책 없음"

    return "\n".join(
        f"- {policy.get('title')} (발표일: {policy.get('published_date')}, 시행일: {policy.get('effective_date') or '미확인'}): {policy.get('summary')}"
        for policy in policies
    )


# 뉴스 검색 결과를 컨텍스트 문자열로 변환
def _format_news(news_items: list[dict[str, Any]]) -> str:
    if not news_items:
        return "- 관련 뉴스 없음"

    return "\n".join(
        f"- {news.get('title')} ({news.get('published_date')}, {news.get('market_signal')}): {news.get('summary')}"
        for news in news_items
    )


# 시세 전후 비교 결과를 컨텍스트 문자열로 변환
def _format_market_summary(market_summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- 기준 지역/월: {market_summary.get('region')} / {market_summary.get('policy_month')}",
            f"- 평균 매매가: 정책 전 {_format_number(market_summary.get('before_avg_price'))} → 정책 후 {_format_number(market_summary.get('after_avg_price'))}",
            f"- 평균 매매가 변화율: {_format_percent(market_summary.get('price_change_rate'))}",
            f"- 정책 전 월평균 거래량: {_format_number(market_summary.get('before_avg_transaction_count'))}",
            f"- 정책 후 월평균 거래량: {_format_number(market_summary.get('after_avg_transaction_count'))}",
            f"- 거래량 변화율: {_format_percent(market_summary.get('transaction_count_change_rate'))}",
        ]
    )


# 정책과 뉴스 출처를 컨텍스트 문자열로 변환
def _format_sources(policies: list[dict[str, Any]], news_items: list[dict[str, Any]]) -> str:
    sources = [
        f"- 정책: {policy.get('policy_id')} {policy.get('url')}"
        for policy in policies
    ]
    sources.extend(
        f"- 뉴스: {news.get('news_id')} {news.get('url')}"
        for news in news_items
    )
    return "\n".join(sources) if sources else "- 참고 출처 없음"


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
