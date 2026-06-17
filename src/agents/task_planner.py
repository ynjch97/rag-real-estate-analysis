import re
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from src.prices.seoul_legal_codes import load_legal_dong_codes
from src.retrieval.query_analyzer import analyze_query


TASK_POLICY_IMPACT = "policy_impact"
TASK_REGION_COMPARISON = "region_comparison"
TASK_PRICE_CAUSE = "price_cause"
TASK_FORECAST = "forecast"
TASK_GENERAL = "general_search"


@dataclass(frozen=True)
class AgentPlan:
    task_type: str
    query: str
    parsed_query: dict[str, Any]
    regions: list[str]
    acc_year: int
    retrieval_steps: list[str]
    reasoning_strategy: str

    # AgentPlan을 dict로 변환
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# 질문 유형과 검색 계획 생성
def plan_agent_task(query: str) -> AgentPlan:
    normalized_query = query.strip()
    parsed_query = analyze_query(normalized_query).to_dict()
    regions = _extract_regions(normalized_query, parsed_query)
    task_type = _classify_task(normalized_query, parsed_query, regions)
    acc_year = parsed_query.get("acc_year") or _infer_relative_year(normalized_query)

    return AgentPlan(
        task_type=task_type,
        query=normalized_query,
        parsed_query=parsed_query,
        regions=regions,
        acc_year=acc_year,
        retrieval_steps=_build_retrieval_steps(task_type),
        reasoning_strategy=_build_reasoning_strategy(task_type),
    )


# 질문 유형 분류
def _classify_task(query: str, parsed_query: dict[str, Any], regions: list[str]) -> str:
    if _is_region_comparison_query(query, regions):
        return TASK_REGION_COMPARISON
    if _is_forecast_query(query):
        return TASK_FORECAST
    if _is_price_cause_query(query):
        return TASK_PRICE_CAUSE
    if parsed_query.get("policy_type") or parsed_query.get("event_keyword"):
        return TASK_POLICY_IMPACT
    return TASK_GENERAL


# 지역 비교 질문 여부 확인
def _is_region_comparison_query(query: str, regions: list[str]) -> bool:
    comparison_keywords = ("중", "비교", "어디", "더")
    return len(regions) >= 2 and any(keyword in query for keyword in comparison_keywords)


# 전망 질문 여부 확인
def _is_forecast_query(query: str) -> bool:
    forecast_keywords = ("내년", "전망", "예상", "어떨", "오를까", "내릴까")
    return any(keyword in query for keyword in forecast_keywords)


# 가격 상승 원인 질문 여부 확인
def _is_price_cause_query(query: str) -> bool:
    cause_keywords = ("왜", "원인", "이유")
    price_keywords = ("집값", "가격", "시세", "매매가")
    upward_keywords = ("올랐", "상승", "급등")
    return (
        any(keyword in query for keyword in cause_keywords)
        and any(keyword in query for keyword in price_keywords)
        and any(keyword in query for keyword in upward_keywords)
    )


# 질문에서 서울시 구 목록 추출
def _extract_regions(query: str, parsed_query: dict[str, Any]) -> list[str]:
    regions = []

    try:
        legal_regions = sorted({row["sigungu"] for row in load_legal_dong_codes()}, key=lambda region: (-len(region), query.find(region)))
    except FileNotFoundError:
        legal_regions = []

    for region in legal_regions:
        if region in query:
            regions.append(region)

    if not regions and parsed_query.get("region"):
        regions.append(str(parsed_query["region"]))

    return sorted(list(dict.fromkeys(regions)), key=lambda region: query.find(region))


# 상대 연도 표현을 수집 기준 연도로 변환
def _infer_relative_year(query: str) -> int:
    current_year = date.today().year
    if "내년" in query:
        return current_year + 1
    if "작년" in query:
        return current_year - 1
    if "올해" in query:
        return current_year

    match = re.search(r"(20\d{2})\s*년?", query)
    if match:
        return int(match.group(1))

    return current_year


# 질문 유형별 검색 순서 생성
def _build_retrieval_steps(task_type: str) -> list[str]:
    steps_by_task = {
        TASK_POLICY_IMPACT: ["policy", "news", "price"],
        TASK_REGION_COMPARISON: ["price", "news"],
        TASK_PRICE_CAUSE: ["policy", "news", "price"],
        TASK_FORECAST: ["price", "news", "policy"],
        TASK_GENERAL: ["policy", "news", "price"],
    }
    return steps_by_task.get(task_type, steps_by_task[TASK_GENERAL])


# 질문 유형별 추론 전략 생성
def _build_reasoning_strategy(task_type: str) -> str:
    strategies = {
        TASK_POLICY_IMPACT: "정책 이벤트를 기준으로 뉴스 반응과 시세 전후 변화를 연결",
        TASK_REGION_COMPARISON: "지역별 같은 연도 시세 변화율과 거래량을 비교",
        TASK_PRICE_CAUSE: "정책, 뉴스, 시세 흐름을 순서대로 확인해 상승 원인 후보를 정리",
        TASK_FORECAST: "최근 시세 흐름과 뉴스 신호를 근거로 제한적 전망 시나리오 제시",
        TASK_GENERAL: "정책, 뉴스, 시세 데이터를 순차 조회해 일반 분석 수행",
    }
    return strategies.get(task_type, strategies[TASK_GENERAL])
