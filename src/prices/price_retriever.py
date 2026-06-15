import json
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRANSACTION_PATH = PROJECT_ROOT / "data" / "sample" / "transactions.jsonl"


# transactions.jsonl 파일을 읽어서 거래 데이터 목록으로 변환
def load_transactions(path: str | Path = DEFAULT_TRANSACTION_PATH) -> list[dict[str, Any]]:
    source_path = Path(path)
    transactions: list[dict[str, Any]] = []

    with source_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                transactions.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {source_path}:{line_number}") from exc

    return transactions


# 지역, 계약일 범위, 거래유형 조건에 맞는 거래 데이터만 조회
def retrieve_transactions(
    region: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    transaction_type: str | None = "매매",
    path: str | Path = DEFAULT_TRANSACTION_PATH,
) -> list[dict[str, Any]]:
    transactions = load_transactions(path)
    start = _parse_optional_date(start_date)
    end = _parse_optional_date(end_date)

    return [
        transaction
        for transaction in transactions
        if _matches_region(transaction, region)
        and _matches_transaction_type(transaction, transaction_type)
        and _is_in_date_range(transaction, start, end)
    ]


# 거래 데이터의 시군구가 요청 지역과 일치하는지 확인
def _matches_region(transaction: dict[str, Any], region: str | None) -> bool:
    if region is None:
        return True
    return transaction.get("sigungu") == region


# 거래 데이터의 거래유형이 요청 거래유형과 일치하는지 확인
def _matches_transaction_type(transaction: dict[str, Any], transaction_type: str | None) -> bool:
    if transaction_type is None:
        return True
    return transaction.get("transaction_type") == transaction_type


# 거래 데이터의 계약일이 요청한 시작일과 종료일 사이에 있는지 확인
def _is_in_date_range(transaction: dict[str, Any], start: date | None, end: date | None) -> bool:
    contract_date = _parse_date(transaction["contract_date"])

    if start is not None and contract_date < start:
        return False
    if end is not None and contract_date > end:
        return False
    return True


# 날짜 문자열이 있으면 date로 변환하고, 없으면 None을 반환
def _parse_optional_date(value: str | None) -> date | None:
    if value is None:
        return None
    return _parse_date(value)


# YYYY-MM-DD 형식의 날짜 문자열을 date 객체로 변환
def _parse_date(value: str) -> date:
    return date.fromisoformat(value)
