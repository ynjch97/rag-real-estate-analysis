import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NAVER_NEWS_API_URL = "https://openapi.naver.com/v1/search/news.json"


# 네이버 뉴스 검색 API URL 생성
def build_naver_news_url(
    query: str,
    display: int = 10,
    start: int = 1,
    sort: str = "date",
    base_url: str = NAVER_NEWS_API_URL,
) -> str:
    params = urlencode(
        {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort,
        }
    )
    return f"{base_url}?{params}"


# 네이버 뉴스 검색 원천 데이터 수집
def fetch_naver_news_raw(
    query: str,
    display: int = 10,
    start: int = 1,
    sort: str = "date",
    client_id: str | None = None,
    client_secret: str | None = None,
    opener: Callable[[Request], Any] = urlopen,
) -> list[dict[str, Any]]:
    client_id, client_secret = _get_naver_api_credentials(client_id, client_secret)
    url = build_naver_news_url(query=query, display=display, start=start, sort=sort)
    request = Request(
        url,
        headers={
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        },
    )

    with opener(request) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return parse_naver_news_response(payload)


# 네이버 뉴스 API JSON 응답에서 item 목록 추출
def parse_naver_news_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return payload.get("items", [])


# 네이버 뉴스 원천 데이터 JSONL 저장
def save_raw_news(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# 네이버 뉴스 API 키 조회
def _get_naver_api_credentials(
    client_id: str | None = None,
    client_secret: str | None = None,
) -> tuple[str, str]:
    _load_env()
    resolved_client_id = client_id or os.getenv("NAVER_CLIENT_ID")
    resolved_client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET") or os.getenv("NAVER_CLIENT_KEY")

    if not resolved_client_id or not resolved_client_secret:
        raise ValueError("Set NAVER_CLIENT_ID and NAVER_CLIENT_SECRET or NAVER_CLIENT_KEY.")

    return resolved_client_id, resolved_client_secret


# 네이버 뉴스 API 키 존재 여부 확인
def has_naver_api_credentials() -> bool:
    _load_env()
    return bool(os.getenv("NAVER_CLIENT_ID") and (os.getenv("NAVER_CLIENT_SECRET") or os.getenv("NAVER_CLIENT_KEY")))


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
