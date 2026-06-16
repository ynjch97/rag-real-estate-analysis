import json
import re
from pathlib import Path
from typing import Any


# 서울시 원천 거래 목록을 README 4-3 구조로 정규화
def normalize_transactions(raw_transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_transactions, start=1):
        transaction = normalize_transaction(raw, index=index)
        if transaction is not None:
            normalized.append(transaction)

    return normalized


# 서울시 원천 거래 1건을 README 4-3 구조로 정규화
def normalize_transaction(raw: dict[str, Any], index: int = 1) -> dict[str, Any] | None:
    contract_date = _normalize_contract_date(
        _get_first(raw, "DEAL_YMD", "CNTRCT_DE", "CTRT_DAY", "DEAL_DATE", "계약일", "contract_date")
    )
    price = _parse_price(_get_first(raw, "OBJ_AMT", "THING_AMT", "DEAL_AMOUNT", "물건금액", "거래금액", "price"))
    area_m2 = _parse_float(_get_first(raw, "BLDG_AREA", "BLDG_AR", "ARCH_AREA", "건물면적", "전용면적", "area_m2"))

    if contract_date is None or price is None or area_m2 is None:
        return None

    region_code = str(_get_first(raw, "SGG_CD", "CGG_CD", "자치구코드", "region_code") or "")
    sigungu = str(_get_first(raw, "SGG_NM", "CGG_NM", "자치구명", "sigungu") or "")
    dong = str(_get_first(raw, "BJDONG_NM", "STDG_NM", "법정동명", "법정동", "dong") or "")
    apartment_name = str(_get_first(raw, "BLDG_NM", "APTFNO", "HOUSE_NM", "건물명", "단지명", "아파트명", "apartment_name") or "")

    return {
        "transaction_id": _get_first(raw, "transaction_id", "거래번호") or _build_transaction_id(region_code, contract_date, index),
        "region_code": region_code,
        "sido": str(_get_first(raw, "SIDO_NM", "시도", "sido") or "서울"),
        "sigungu": sigungu,
        "dong": dong,
        "apartment_name": apartment_name,
        "contract_date": contract_date,
        "price": price,
        "area_m2": area_m2,
        "floor": _parse_int(_get_first(raw, "FLR_NO", "FLOOR", "FLR", "층", "floor")),
        "built_year": _parse_int(_get_first(raw, "BUILD_YEAR", "ARCH_YEAR", "ARCH_YR", "BLDG_YEAR", "건축년도", "built_year")),
        "transaction_type": _normalize_transaction_type(_get_first(raw, "HOUSE_TYPE", "BLDG_USG", "건물주용도", "거래유형", "transaction_type")),
    }


# 정규화된 거래 데이터 JSONL 저장
def save_transactions(path: str | Path, transactions: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for transaction in transactions:
            f.write(json.dumps(transaction, ensure_ascii=False) + "\n")


# 여러 후보 키 중 첫 번째 값 조회
def _get_first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


# 계약일 문자열을 YYYY-MM-DD로 변환
def _normalize_contract_date(value: Any) -> str | None:
    if value in (None, ""):
        return None

    digits = re.sub(r"[^0-9]", "", str(value))
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return None


# 물건금액을 원 단위 정수로 변환
def _parse_price(value: Any) -> int | None:
    if _is_blank(value):
        return None

    number = int(re.sub(r"[^0-9]", "", str(value)))
    if number < 10_000_000:
        return number * 10_000
    return number


# 숫자 문자열을 float로 변환
def _parse_float(value: Any) -> float | None:
    if _is_blank(value):
        return None
    return float(str(value).replace(",", "").strip())


# 숫자 문자열을 int로 변환
def _parse_int(value: Any) -> int | None:
    if _is_blank(value):
        return None
    return int(float(str(value).replace(",", "").strip()))


# 서울시 건물주용도 값을 거래유형 기본값으로 변환
def _normalize_transaction_type(value: Any) -> str:
    if _is_blank(value):
        return "매매"
    if str(value) in {"아파트", "연립다세대", "단독다가구"}:
        return "매매"
    return str(value)


# 거래번호 기본값 생성
def _build_transaction_id(region_code: str, contract_date: str, index: int) -> str:
    region = region_code or "unknown"
    return f"tx_{region}_{contract_date.replace('-', '')}_{index:04d}"


# 빈 값 여부 확인
def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip().lower() in {"", "null", "none", "-"}
