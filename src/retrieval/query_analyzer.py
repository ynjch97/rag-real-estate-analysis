import re
from dataclasses import asdict, dataclass

from src.prices.seoul_legal_codes import load_legal_dong_codes


SUPPORTED_REGIONS = ("성동구", "광진구", "강남구")

POLICY_KEYWORD_RULES = (
    ("interest_rate", "금리 인상", ("금리 인상", "기준금리 인상", "금리상승")),
    ("interest_rate", "금리", ("금리", "이자", "대출 이자")),
    ("loan_regulation", "대출 규제", ("대출 규제", "대출규제", "DSR", "LTV", "대출 한도")),
    ("supply_policy", "공급 정책", ("공급", "주택 공급", "정비사업", "재건축", "분양")),
)


@dataclass(frozen=True)
class ParsedQuery:
    query: str
    region: str | None
    event_keyword: str | None
    policy_type: str | None
    intent: str
    property_type: str
    transaction_type: str
    acc_year: int | None
    months_before: int
    months_after: int

    def to_dict(self) -> dict[str, str | int | None]:
        return asdict(self)


def analyze_query(query: str) -> ParsedQuery:
    normalized_query = query.strip()

    return ParsedQuery(
        query=normalized_query,
        region=_extract_region(normalized_query),
        event_keyword=_extract_event_keyword(normalized_query),
        policy_type=_extract_policy_type(normalized_query),
        intent=_extract_intent(normalized_query),
        property_type=_extract_property_type(normalized_query),
        transaction_type=_extract_transaction_type(normalized_query),
        acc_year=_extract_acc_year(normalized_query),
        months_before=6,
        months_after=6,
    )


def _extract_region(query: str) -> str | None:
    for region in _get_supported_regions():
        if region in query:
            return region
    return None


# 서울시 구 이름 목록 조회
def _get_supported_regions() -> tuple[str, ...]:
    regions = set(SUPPORTED_REGIONS)

    try:
        regions.update(row["sigungu"] for row in load_legal_dong_codes())
    except FileNotFoundError:
        pass

    return tuple(sorted(regions, key=len, reverse=True))


def _extract_event_keyword(query: str) -> str | None:
    for _, event_keyword, keywords in POLICY_KEYWORD_RULES:
        if any(keyword in query for keyword in keywords):
            return event_keyword
    return None


def _extract_policy_type(query: str) -> str | None:
    for policy_type, _, keywords in POLICY_KEYWORD_RULES:
        if any(keyword in query for keyword in keywords):
            return policy_type
    return None


def _extract_intent(query: str) -> str:
    policy_impact_keywords = ("영향", "미친", "변화", "왜", "원인", "분석")
    if any(keyword in query for keyword in policy_impact_keywords):
        return "policy_impact"
    return "general_search"


def _extract_property_type(query: str) -> str:
    if "오피스텔" in query:
        return "officetel"
    if "빌라" in query or "연립" in query:
        return "villa"
    return "apartment"


def _extract_transaction_type(query: str) -> str:
    if "전세" in query:
        return "jeonse"
    if "월세" in query:
        return "monthly_rent"
    return "sale"


# 질문에서 수집 기준 연도 추출
def _extract_acc_year(query: str) -> int | None:
    match = re.search(r"(20\d{2})\s*년?", query)
    if match is None:
        return None
    return int(match.group(1))
