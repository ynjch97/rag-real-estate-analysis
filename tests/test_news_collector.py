import json

from src.collectors.news_collector import (
    build_naver_news_url,
    fetch_naver_news_raw,
    parse_naver_news_response,
    save_raw_news,
)


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


# 네이버 뉴스 검색 API URL 생성 검증
def test_builds_naver_news_url():
    url = build_naver_news_url(query="금리 인상 동작구 아파트 매매", display=10, start=1, sort="date")

    assert url == (
        "https://openapi.naver.com/v1/search/news.json?"
        "query=%EA%B8%88%EB%A6%AC+%EC%9D%B8%EC%83%81+%EB%8F%99%EC%9E%91%EA%B5%AC+%EC%95%84%ED%8C%8C%ED%8A%B8+%EB%A7%A4%EB%A7%A4"
        "&display=10&start=1&sort=date"
    )


# 네이버 뉴스 API JSON 응답 item 추출 검증
def test_parses_naver_news_response():
    payload = {"items": [{"title": "뉴스 제목"}]}

    assert parse_naver_news_response(payload) == [{"title": "뉴스 제목"}]


# 네이버 뉴스 원천 데이터 수집 검증
def test_fetches_naver_news_raw_with_fake_opener():
    payload = {"items": [{"title": "뉴스 제목"}]}
    seen_requests = []

    def fake_opener(request):
        seen_requests.append(request)
        return FakeResponse(payload)

    rows = fetch_naver_news_raw(
        query="금리 인상 동작구",
        client_id="test-client-id",
        client_secret="test-client-secret",
        opener=fake_opener,
    )

    assert rows == [{"title": "뉴스 제목"}]
    assert seen_requests[0].headers["X-naver-client-id"] == "test-client-id"
    assert seen_requests[0].headers["X-naver-client-secret"] == "test-client-secret"


# 네이버 뉴스 원천 데이터 JSONL 저장 검증
def test_saves_raw_news(tmp_path):
    output_path = tmp_path / "raw_news.jsonl"
    save_raw_news(output_path, [{"title": "뉴스 제목"}])

    assert output_path.read_text(encoding="utf-8").strip() == '{"title": "뉴스 제목"}'
