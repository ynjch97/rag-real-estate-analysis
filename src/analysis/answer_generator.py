import os
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LLM_MODEL = "gpt-4o-mini"


# 컨텍스트와 계산 결과 기반 템플릿 답변 생성
def generate_market_impact_answer(
    parsed_query: dict[str, Any],
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
    context: str,
) -> str:
    llm_answer = _generate_answer_with_llm(
        parsed_query=parsed_query,
        policies=policies,
        news_items=news_items,
        market_summary=market_summary,
        context=context,
    )
    if llm_answer:
        return llm_answer

    return _generate_market_impact_answer_from_template(
        parsed_query=parsed_query,
        policies=policies,
        news_items=news_items,
        market_summary=market_summary,
        context=context,
    )


# Agent Controller 답변 생성
def generate_agent_answer(
    parsed_query: dict[str, Any],
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
    context: str,
    fallback_answer: str,
) -> str:
    llm_answer = _generate_answer_with_llm(
        parsed_query=parsed_query,
        policies=policies,
        news_items=news_items,
        market_summary=market_summary,
        context=context,
    )
    return llm_answer or fallback_answer


# LLM 기반 답변 생성
def _generate_answer_with_llm(
    parsed_query: dict[str, Any],
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
    context: str,
) -> str | None:
    _load_env()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "sk-proj-xxxxxxxx":
        return None

    try:
        llm = ChatOpenAI(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", DEFAULT_LLM_MODEL),
            temperature=0,
        )
        response = llm.invoke(_build_llm_messages(parsed_query, policies, news_items, market_summary, context))
    except Exception:
        return None

    answer = str(getattr(response, "content", "") or "").strip()
    if not _has_required_answer_sections(answer):
        return None
    return answer


# LLM 메시지 생성
def _build_llm_messages(
    parsed_query: dict[str, Any],
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
    context: str,
) -> list[tuple[str, str]]:
    system_prompt = "\n".join(
        [
            "너는 RAG 기반 부동산 의사결정 시스템의 답변 생성기다.",
            "반드시 제공된 컨텍스트, 정책, 뉴스, 시세 데이터 안에서만 답변한다.",
            "제공된 정보에 없는 사실, 수치, 원인, 전망은 절대 추측하지 않는다.",
            "정책과 시세의 관계는 단정하지 말고 근거 수준과 불확실성을 함께 설명한다.",
            "지식 그래프가 제공되면 노드와 관계를 근거 정렬에 활용하되, weight를 인과관계 확정값으로 해석하지 않는다.",
            "답변은 반드시 아래 섹션명과 순서를 그대로 사용한다.",
            "[질문 해석]",
            "[결론 요약]",
            "[정책 근거]",
            "[관련 뉴스 요약]",
            "[시세 변화 데이터]",
            "[정책과 시세의 관계 해석]",
            "[불확실성 및 추가 확인 필요 사항]",
            "[참고 출처]",
        ]
    )
    user_prompt = "\n\n".join(
        [
            "[사용자 질문 분석 결과]",
            str(parsed_query),
            "[검색된 정책 데이터]",
            str(policies),
            "[검색된 뉴스 데이터]",
            str(news_items),
            "[시세 계산 데이터]",
            str(market_summary),
            "[LLM 입력 컨텍스트]",
            context,
            "[작성 지시]",
            "위 데이터만 근거로 한국어 답변을 작성하라.",
        ]
    )
    return [("system", system_prompt), ("user", user_prompt)]


# 필수 답변 섹션 포함 여부 확인
def _has_required_answer_sections(answer: str) -> bool:
    required_sections = (
        "[질문 해석]",
        "[결론 요약]",
        "[정책 근거]",
        "[관련 뉴스 요약]",
        "[시세 변화 데이터]",
        "[정책과 시세의 관계 해석]",
        "[불확실성 및 추가 확인 필요 사항]",
        "[참고 출처]",
    )
    return all(section in answer for section in required_sections)


# 루트 .env 환경변수 로드
def _load_env(env_path: Path = PROJECT_ROOT / ".env") -> None:
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# 템플릿 기반 답변 생성
def _generate_market_impact_answer_from_template(
    parsed_query: dict[str, Any],
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
    context: str,
) -> str:
    region = _format_location(parsed_query)
    event_keyword = parsed_query.get("event_keyword") or "해당 이벤트"
    price_change_rate = market_summary.get("price_change_rate")
    transaction_change_rate = market_summary.get("transaction_count_change_rate")

    return "\n".join(
        [
            "[질문 해석]",
            _format_query(parsed_query),
            "",
            "[결론 요약]",
            f"{region}의 {event_keyword} 전후 시세를 비교한 결과, 평균 가격 변화율은 {_format_percent(price_change_rate)}입니다.",
            f"월평균 거래량 변화율은 {_format_percent(transaction_change_rate)}입니다.",
            "",
            "[정책 근거]",
            _format_policies(policies),
            "",
            "[관련 뉴스 요약]",
            _format_news(news_items),
            "",
            "[시세 변화 데이터]",
            _format_market_summary(market_summary),
            "",
            "[정책과 시세의 관계 해석]",
            _build_interpretation(price_change_rate, transaction_change_rate),
            "",
            "[불확실성 및 추가 확인 필요 사항]",
            "- 현재 결과는 샘플 데이터 기반입니다.",
            "- 실제 판단에는 최신 실거래가, 정책 원문, 추가 뉴스 확인이 필요합니다.",
            "- 제공된 데이터만으로 정책과 시세의 인과관계를 단정하지 않습니다.",
            "",
            "[참고 출처]",
            _format_sources(policies, news_items),
        ]
    )


# 질문 분석 결과를 답변 섹션으로 변환
def _format_query(parsed_query: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- 지역/기간: {_format_location(parsed_query)} / 전 {parsed_query.get('months_before')}개월, 후 {parsed_query.get('months_after')}개월",
            f"- 정책 이벤트: {parsed_query.get('event_keyword') or '미확인'}",
        ]
    )


# 정책 정보를 답변 섹션으로 변환
def _format_policies(policies: list[dict[str, Any]]) -> str:
    if not policies:
        return "- 관련 정책 없음"

    return "\n".join(
        f"- {policy.get('title')} (발표일: {policy.get('published_date')}, 시행일: {policy.get('effective_date') or '미확인'}): {policy.get('summary')}"
        for policy in policies
    )


# 뉴스 정보를 답변 섹션으로 변환
def _format_news(news_items: list[dict[str, Any]]) -> str:
    if not news_items:
        return "- 관련 뉴스 없음"

    return "\n".join(
        f"- {news.get('title')} ({news.get('published_date')}, {news.get('market_signal')}): {news.get('summary')}"
        for news in news_items
    )


# 시세 요약을 답변 섹션으로 변환
def _format_market_summary(market_summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- 기준 지역/월: {_format_market_location(market_summary)} / {market_summary.get('policy_month')}",
            f"- 평균 매매가: 정책 전 {_format_number(market_summary.get('before_avg_price'))} → 정책 후 {_format_number(market_summary.get('after_avg_price'))}",
            f"- 평균 매매가 변화율: {_format_percent(market_summary.get('price_change_rate'))}",
            f"- 정책 전 월평균 거래량: {_format_number(market_summary.get('before_avg_transaction_count'))}",
            f"- 정책 후 월평균 거래량: {_format_number(market_summary.get('after_avg_transaction_count'))}",
            f"- 거래량 변화율: {_format_percent(market_summary.get('transaction_count_change_rate'))}",
        ]
    )


# 참고 출처를 답변 섹션으로 변환
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


# 질문 분석 위치 문자열 변환
def _format_location(parsed_query: dict[str, Any]) -> str:
    region = parsed_query.get("region")
    dong = parsed_query.get("dong")
    if region and dong:
        return f"{region} {dong}"
    return region or "대상 지역"


# 시세 요약 위치 문자열 변환
def _format_market_location(market_summary: dict[str, Any]) -> str:
    region = market_summary.get("region")
    dong = market_summary.get("dong")
    if region and dong:
        return f"{region} {dong}"
    return str(region or "미확인")


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
