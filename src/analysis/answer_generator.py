from typing import Any


# 컨텍스트와 계산 결과 기반 템플릿 답변 생성
def generate_market_impact_answer(
    parsed_query: dict[str, Any],
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
    context: str,
) -> str:
    region = parsed_query.get("region") or "대상 지역"
    event_keyword = parsed_query.get("event_keyword") or "해당 이벤트"
    price_change_rate = market_summary.get("price_change_rate")
    transaction_change_rate = market_summary.get("transaction_count_change_rate")

    return "\n".join(
        [
            "[결론 요약]",
            f"{region}의 {event_keyword} 전후 시세를 비교한 결과, 평균 가격 변화율은 {_format_percent(price_change_rate)}입니다.",
            f"월평균 거래량 변화율은 {_format_percent(transaction_change_rate)}입니다.",
            "",
            "[근거]",
            f"- 관련 정책 {len(policies)}건, 관련 뉴스 {len(news_items)}건을 함께 검토했습니다.",
            f"- 정책 전 평균 가격: {_format_number(market_summary.get('before_avg_price'))}",
            f"- 정책 후 평균 가격: {_format_number(market_summary.get('after_avg_price'))}",
            "",
            "[해석]",
            _build_interpretation(price_change_rate, transaction_change_rate),
            "",
            "[주의]",
            "이 답변은 현재 샘플 데이터와 제공된 컨텍스트만 기반으로 하며, 제공되지 않은 사실은 추측하지 않습니다.",
            "",
            "[컨텍스트]",
            context,
        ]
    )


# 가격과 거래량 변화율 기반 해석 문장 생성
def _build_interpretation(price_change_rate: float | None, transaction_change_rate: float | None) -> str:
    if price_change_rate is None:
        return "가격 변화율을 계산할 수 없어 정책과 시세의 관계를 단정하기 어렵습니다."

    if price_change_rate > 0 and (transaction_change_rate is None or transaction_change_rate >= 0):
        return "가격과 거래량이 함께 증가해 시장 수요가 유지되었을 가능성이 있습니다."
    if price_change_rate > 0 and transaction_change_rate < 0:
        return "가격은 상승했지만 거래량은 감소해 일부 선호 단지 중심의 제한적 상승일 가능성이 있습니다."
    if price_change_rate < 0:
        return "평균 가격이 하락해 정책 이후 매수 심리 또는 거래 조건이 약해졌을 가능성이 있습니다."
    return "평균 가격 변화가 크지 않아 정책 영향은 제한적으로 해석하는 편이 적절합니다."


# 숫자 값을 읽기 쉬운 문자열로 변환
def _format_number(value: Any) -> str:
    if value is None:
        return "계산 불가"
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    return str(value)


# 퍼센트 값을 읽기 쉬운 문자열로 변환
def _format_percent(value: Any) -> str:
    if value is None:
        return "계산 불가"
    return f"{value}%"
