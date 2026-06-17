import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ECOS_API_BASE_URL = "https://ecos.bok.or.kr/api"
ECOS_INTEREST_RATE_STAT_CODES = ("121Y006", "121Y015")


# ECOS 통계 항목 목록 API URL 생성
def build_ecos_statistic_item_list_url(
    stat_code: str,
    api_key: str,
    start_count: int = 1,
    end_count: int = 100,
    language: str = "kr",
    response_type: str = "json",
    base_url: str = ECOS_API_BASE_URL,
) -> str:
    return f"{base_url.rstrip('/')}/StatisticItemList/{api_key}/{response_type}/{language}/{start_count}/{end_count}/{stat_code}"


# ECOS 통계 항목 원천 데이터 수집
def fetch_ecos_statistic_items_raw(
    stat_code: str,
    api_key: str | None = None,
    start_count: int = 1,
    end_count: int = 100,
    opener: Callable[[str], Any] = urlopen,
) -> list[dict[str, Any]]:
    api_key = api_key or _get_ecos_api_key()
    url = build_ecos_statistic_item_list_url(
        stat_code=stat_code,
        api_key=api_key,
        start_count=start_count,
        end_count=end_count,
    )

    with opener(url) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return parse_ecos_statistic_item_response(payload)


# ECOS 금리 통계 항목 원천 데이터 수집
def fetch_ecos_interest_rate_items_raw(
    api_key: str | None = None,
    opener: Callable[[str], Any] = urlopen,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for stat_code in ECOS_INTEREST_RATE_STAT_CODES:
        rows.extend(fetch_ecos_statistic_items_raw(stat_code=stat_code, api_key=api_key, opener=opener))

    return rows


# ECOS 통계 항목 API JSON 응답에서 row 목록 추출
def parse_ecos_statistic_item_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = payload.get("StatisticItemList")
    if body is None:
        result = payload.get("RESULT", {})
        if result.get("CODE"):
            raise ValueError(f"ECOS API error: {result}")
        return []

    result = body.get("RESULT", {})
    if result and result.get("CODE") not in ("INFO-000",):
        raise ValueError(f"ECOS API error: {result}")

    return body.get("row", [])


# ECOS 원천 데이터 JSONL 저장
def save_raw_ecos_items(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ECOS API 키 조회
def _get_ecos_api_key() -> str:
    _load_env()
    api_key = os.getenv("ECOS_KEY")
    if not api_key:
        raise ValueError("Set ECOS_KEY before collecting ECOS data.")
    return api_key


# ECOS API 키 존재 여부 확인
def has_ecos_api_key() -> bool:
    _load_env()
    return bool(os.getenv("ECOS_KEY"))


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
