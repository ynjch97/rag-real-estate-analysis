import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEOUL_API_BASE_URL = "http://openapi.seoul.go.kr:8088"
SEOUL_REAL_ESTATE_SERVICE = "tbLnOpendataRtmsV"


# 서울시 부동산 실거래가 API URL 생성
def build_seoul_transaction_url(
    api_key: str,
    start_index: int = 1,
    end_index: int = 1000,
    acc_year: str | int | None = None,
    sgg_cd: str | int | None = None,
    sgg_nm: str | None = None,
    bjdong_cd: str | int | None = None,
    land_gbn: str | int | None = None,
    land_gbn_nm: str | None = None,
    bonbun: str | int | None = None,
    bubun: str | int | None = None,
    floor: str | int | None = None,
    contract_date: str | int | None = None,
    house_type: str | None = None,
    response_type: str = "json",
    base_url: str = DEFAULT_SEOUL_API_BASE_URL,
) -> str:
    path_parts = [
        api_key,
        response_type,
        SEOUL_REAL_ESTATE_SERVICE,
        start_index,
        end_index,
        acc_year,
        sgg_cd,
        sgg_nm,
        bjdong_cd,
        land_gbn,
        land_gbn_nm,
        bonbun,
        bubun,
        floor,
        contract_date,
        house_type,
    ]
    encoded_path = "/".join(_encode_path_part(part) for part in path_parts)
    return f"{base_url.rstrip('/')}/{encoded_path}"


# 서울시 부동산 실거래가 원천 데이터 수집
def fetch_seoul_transactions_raw(
    api_key: str | None = None,
    start_index: int = 1,
    end_index: int = 1000,
    acc_year: str | int | None = None,
    sgg_cd: str | int | None = None,
    sgg_nm: str | None = None,
    bjdong_cd: str | int | None = None,
    land_gbn: str | int | None = None,
    land_gbn_nm: str | None = None,
    bonbun: str | int | None = None,
    bubun: str | int | None = None,
    floor: str | int | None = None,
    contract_date: str | int | None = None,
    house_type: str | None = None,
    opener: Callable[[str], Any] = urlopen,
) -> list[dict[str, Any]]:
    api_key = api_key or _get_transaction_api_key()
    url = build_seoul_transaction_url(
        api_key=api_key,
        start_index=start_index,
        end_index=end_index,
        acc_year=acc_year,
        sgg_cd=sgg_cd,
        sgg_nm=sgg_nm,
        bjdong_cd=bjdong_cd,
        land_gbn=land_gbn,
        land_gbn_nm=land_gbn_nm,
        bonbun=bonbun,
        bubun=bubun,
        floor=floor,
        contract_date=contract_date,
        house_type=house_type,
    )

    with opener(url) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return parse_seoul_transaction_response(payload)


# 서울시 API JSON 응답에서 row 목록 추출
def parse_seoul_transaction_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = payload.get(SEOUL_REAL_ESTATE_SERVICE)
    if body is None:
        result = payload.get("RESULT", {})
        if result.get("CODE") == "INFO-200":
            return []
        raise ValueError(f"Unexpected Seoul API response: {payload}")

    result = body.get("RESULT", {})
    if result and result.get("CODE") not in ("INFO-000", "INFO-200"):
        raise ValueError(f"Seoul API error: {result}")

    return body.get("row", [])


# 서울시 원천 거래 데이터 JSONL 저장
def save_raw_transactions(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# 거래 API 키 조회
def _get_transaction_api_key() -> str:
    _load_env()
    api_key = os.getenv("TRANSACTION_API_KEY") or os.getenv("SEOUL_API_KEY")
    if not api_key:
        raise ValueError("Set TRANSACTION_API_KEY before collecting Seoul transaction data.")
    return api_key


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


# URL path segment 인코딩
def _encode_path_part(value: Any) -> str:
    if value is None:
        return ""
    return quote(str(value), safe="")
