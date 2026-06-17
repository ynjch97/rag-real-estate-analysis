import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from src.collectors.transaction_collector import (
    fetch_seoul_transactions_by_dong,
    fetch_seoul_transactions_by_sigungu,
    save_raw_transactions,
)
from src.preprocessing.transaction_cleaner import normalize_transactions, save_transactions
from src.prices.seoul_legal_codes import find_legal_dong_code, get_sgg_cd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRANSACTION_PATH = PROJECT_ROOT / "data" / "sample" / "transactions.jsonl"
DEFAULT_RAW_TRANSACTION_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_PROCESSED_TRANSACTION_DIR = PROJECT_ROOT / "data" / "processed"


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
    dong: str | None = None,
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
        and _matches_dong(transaction, dong)
        and _matches_transaction_type(transaction, transaction_type)
        and _is_in_date_range(transaction, start, end)
    ]


# 실제 서울시 API 데이터 우선 거래 데이터 조회
def retrieve_or_collect_transactions(
    region: str | None,
    acc_year: str | int,
    dong: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    transaction_type: str | None = "매매",
    fallback_path: str | Path = DEFAULT_TRANSACTION_PATH,
) -> list[dict[str, Any]]:
    if region is None:
        return retrieve_transactions(
            region=region,
            dong=dong,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            path=fallback_path,
        )

    processed_path = _build_processed_transaction_path(region=region, acc_year=acc_year, dong=dong)
    if processed_path.exists():
        return retrieve_transactions(
            region=region,
            dong=dong,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            path=processed_path,
        )

    if not _has_transaction_api_key():
        return retrieve_transactions(
            region=region,
            dong=dong,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            path=fallback_path,
        )

    raw_rows = _fetch_raw_transactions(region=region, dong=dong, acc_year=acc_year)
    raw_path = _build_raw_transaction_path(region=region, acc_year=acc_year, dong=dong)
    save_raw_transactions(raw_path, raw_rows)

    transactions = normalize_transactions(raw_rows)
    save_transactions(processed_path, transactions)

    return retrieve_transactions(
        region=region,
        dong=dong,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
        path=processed_path,
    )


# 거래 데이터의 시군구가 요청 지역과 일치하는지 확인
def _matches_region(transaction: dict[str, Any], region: str | None) -> bool:
    if region is None:
        return True
    return transaction.get("sigungu") == region


# 거래 데이터의 법정동이 요청 동과 일치하는지 확인
def _matches_dong(transaction: dict[str, Any], dong: str | None) -> bool:
    if dong is None:
        return True
    return transaction.get("dong") == dong


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


# 지역/연도 기준 정규화 거래 파일 경로 생성
def _build_processed_transaction_path(region: str, acc_year: str | int, dong: str | None = None) -> Path:
    sgg_cd = get_sgg_cd(region)
    if dong is not None:
        bjdong_cd = find_legal_dong_code(region, dong)["bjdong_cd"]
        return DEFAULT_PROCESSED_TRANSACTION_DIR / f"transactions_{acc_year}_{sgg_cd}_{bjdong_cd}.jsonl"
    return DEFAULT_PROCESSED_TRANSACTION_DIR / f"transactions_{acc_year}_{sgg_cd}.jsonl"


# 지역/연도 기준 원천 거래 파일 경로 생성
def _build_raw_transaction_path(region: str, acc_year: str | int, dong: str | None = None) -> Path:
    sgg_cd = get_sgg_cd(region)
    if dong is not None:
        bjdong_cd = find_legal_dong_code(region, dong)["bjdong_cd"]
        return DEFAULT_RAW_TRANSACTION_DIR / f"seoul_transactions_{acc_year}_{sgg_cd}_{bjdong_cd}.jsonl"
    return DEFAULT_RAW_TRANSACTION_DIR / f"seoul_transactions_{acc_year}_{sgg_cd}.jsonl"


# 지역/동 조건 기준 원천 거래 데이터 수집
def _fetch_raw_transactions(region: str, dong: str | None, acc_year: str | int) -> list[dict[str, Any]]:
    if dong is not None:
        return fetch_seoul_transactions_by_dong(acc_year=acc_year, sigungu=region, dong=dong)
    return fetch_seoul_transactions_by_sigungu(acc_year=acc_year, sigungu=region)


# 거래 API 키 존재 여부 확인
def _has_transaction_api_key() -> bool:
    _load_env()
    return bool(os.getenv("TRANSACTION_API_KEY") or os.getenv("SEOUL_API_KEY"))


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
