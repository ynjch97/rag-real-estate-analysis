import json
import hashlib
from pathlib import Path
from typing import Any


ECOS_STAT_NAMES = {
    "121Y006": "예금은행 대출금리(신규취급액 기준)",
    "121Y015": "예금은행 대출금리(잔액 기준)",
}


# ECOS 금리 통계 항목을 README 4-1 정책 구조로 정규화
def normalize_ecos_interest_rate_items(raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    policies: list[dict[str, Any]] = []

    for raw in raw_items:
        policy = normalize_ecos_interest_rate_item(raw)
        if policy is not None:
            policies.append(policy)

    return policies


# ECOS 금리 통계 항목 1건을 README 4-1 정책 구조로 정규화
def normalize_ecos_interest_rate_item(raw: dict[str, Any]) -> dict[str, Any] | None:
    stat_code = str(raw.get("STAT_CODE") or "").strip()
    item_code = str(raw.get("ITEM_CODE") or raw.get("ITEM_CODE1") or "").strip()
    item_name = str(raw.get("ITEM_NAME") or raw.get("ITEM_NAME1") or "").strip()

    if not stat_code or not item_code or not item_name:
        return None

    stat_name = str(raw.get("STAT_NAME") or ECOS_STAT_NAMES.get(stat_code, "ECOS 금리 통계")).strip()
    start_time = _normalize_month(raw.get("START_TIME"))
    end_time = _normalize_month(raw.get("END_TIME"))
    unit_name = str(raw.get("UNIT_NAME") or "").strip()
    summary = _build_summary(stat_name, item_name, start_time, end_time, unit_name)

    return {
        "policy_id": f"ecos_{stat_code}_{item_code}",
        "title": f"{stat_name} - {item_name}",
        "url": f"https://ecos.bok.or.kr/api/StatisticItemList/[ECOS_KEY]/json/kr/1/100/{stat_code}",
        "published_date": end_time,
        "effective_date": end_time,
        "policy_type": "interest_rate",
        "region_tags": ["전국"],
        "keywords": ["금리", "대출금리", "예금은행", item_name],
        "summary": summary,
        "content": summary,
        "source": "ECOS",
        "stat_code": stat_code,
        "item_code": item_code,
        "item_name": item_name,
        "unit_name": unit_name,
        "start_time": start_time,
        "end_time": end_time,
    }


# 정책브리핑 정책뉴스 목록을 README 4-1 정책 구조로 정규화
def normalize_korea_policy_news_items(raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    policies: list[dict[str, Any]] = []

    for raw in raw_items:
        policy = normalize_korea_policy_news_item(raw)
        if policy is not None:
            policies.append(policy)

    return policies


# 정책브리핑 정책뉴스 1건을 README 4-1 정책 구조로 정규화
def normalize_korea_policy_news_item(raw: dict[str, Any]) -> dict[str, Any] | None:
    title = str(raw.get("title") or "").strip()
    url = str(raw.get("url") or "").strip()
    content = str(raw.get("content") or "").strip()

    if not title or not url:
        return None

    keywords = _extract_policy_keywords(f"{title} {content}")
    policy_type = _infer_policy_type(keywords)
    region_tags = _extract_region_tags(f"{title} {content}")
    summary = _build_policy_news_summary(raw)

    return {
        "policy_id": f"korea_policy_{_hash_text(url)}",
        "title": title,
        "url": url,
        "published_date": raw.get("published_date"),
        "effective_date": raw.get("published_date"),
        "policy_type": policy_type,
        "region_tags": region_tags,
        "keywords": keywords,
        "summary": summary,
        "content": content or summary,
        "source": "KoreaPolicyBriefing",
        "ministry": raw.get("ministry"),
    }


# 정규화된 정책 데이터 JSONL 저장
def save_policies(path: str | Path, policies: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for policy in policies:
            f.write(json.dumps(policy, ensure_ascii=False) + "\n")


# ECOS 월 문자열을 YYYY-MM로 변환
def _normalize_month(value: Any) -> str | None:
    if value in (None, ""):
        return None

    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) >= 6:
        return f"{digits[:4]}-{digits[4:6]}"
    if len(digits) == 4:
        return digits
    return str(value)


# ECOS 금리 통계 요약 생성
def _build_summary(
    stat_name: str,
    item_name: str,
    start_time: str | None,
    end_time: str | None,
    unit_name: str,
) -> str:
    period = " ~ ".join(value for value in (start_time, end_time) if value)
    unit = f", 단위: {unit_name}" if unit_name else ""
    if period:
        return f"{stat_name} 중 {item_name} 항목이다. 제공 기간: {period}{unit}."
    return f"{stat_name} 중 {item_name} 항목이다{unit}."


# 정책뉴스 요약 생성
def _build_policy_news_summary(raw: dict[str, Any]) -> str:
    subtitle = str(raw.get("subtitle") or "").strip()
    content = str(raw.get("content") or "").strip()

    if subtitle and content:
        return f"{subtitle} {content[:240]}".strip()
    if subtitle:
        return subtitle
    return content[:300]


# 정책뉴스 텍스트에서 정책 키워드 추출
def _extract_policy_keywords(text: str) -> list[str]:
    keyword_rules = (
        "금리",
        "대출",
        "DSR",
        "LTV",
        "공급",
        "청약",
        "재건축",
        "재개발",
        "세제",
        "전세",
        "주택",
        "부동산",
        "국토",
        "금융",
    )
    keywords = [keyword for keyword in keyword_rules if keyword in text]
    return keywords or ["정책뉴스"]


# 정책 키워드 기반 정책 유형 추정
def _infer_policy_type(keywords: list[str]) -> str:
    if any(keyword in keywords for keyword in ("금리",)):
        return "interest_rate"
    if any(keyword in keywords for keyword in ("대출", "DSR", "LTV", "금융")):
        return "loan_regulation"
    if any(keyword in keywords for keyword in ("공급", "청약", "재건축", "재개발", "주택", "국토")):
        return "supply_policy"
    if any(keyword in keywords for keyword in ("세제",)):
        return "tax_policy"
    return "policy_news"


# 정책뉴스 텍스트에서 지역 태그 추출
def _extract_region_tags(text: str) -> list[str]:
    region_candidates = (
        "서울",
        "강남구",
        "서초구",
        "송파구",
        "강서구",
        "마포구",
        "은평구",
        "영등포구",
        "동작구",
        "성동구",
        "광진구",
        "강북구",
        "전국",
    )
    regions = [region for region in region_candidates if region in text]
    return regions or ["전국"]


# 텍스트 해시 생성
def _hash_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
