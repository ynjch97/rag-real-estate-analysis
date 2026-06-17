import json
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
