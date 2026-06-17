import json

from src.collectors.ecos_collector import (
    build_ecos_statistic_item_list_url,
    fetch_ecos_statistic_items_raw,
    parse_ecos_statistic_item_response,
    save_raw_ecos_items,
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


# ECOS 통계 항목 목록 API URL 생성 검증
def test_builds_ecos_statistic_item_list_url():
    url = build_ecos_statistic_item_list_url(stat_code="121Y006", api_key="test-key")

    assert url == "https://ecos.bok.or.kr/api/StatisticItemList/test-key/json/kr/1/100/121Y006"


# ECOS 통계 항목 API JSON 응답 row 추출 검증
def test_parses_ecos_statistic_item_response():
    payload = {
        "StatisticItemList": {
            "RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다"},
            "row": [{"STAT_CODE": "121Y006", "ITEM_CODE": "BECBLA02"}],
        }
    }

    assert parse_ecos_statistic_item_response(payload) == [{"STAT_CODE": "121Y006", "ITEM_CODE": "BECBLA02"}]


# ECOS 통계 항목 원천 데이터 수집 검증
def test_fetches_ecos_statistic_items_raw_with_fake_opener():
    payload = {
        "StatisticItemList": {
            "RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다"},
            "row": [{"STAT_CODE": "121Y006", "ITEM_CODE": "BECBLA02"}],
        }
    }
    seen_urls = []

    def fake_opener(url):
        seen_urls.append(url)
        return FakeResponse(payload)

    rows = fetch_ecos_statistic_items_raw(stat_code="121Y006", api_key="test-key", opener=fake_opener)

    assert rows == [{"STAT_CODE": "121Y006", "ITEM_CODE": "BECBLA02"}]
    assert seen_urls[0] == "https://ecos.bok.or.kr/api/StatisticItemList/test-key/json/kr/1/100/121Y006"


# ECOS 원천 데이터 JSONL 저장 검증
def test_saves_raw_ecos_items(tmp_path):
    output_path = tmp_path / "ecos_items.jsonl"
    save_raw_ecos_items(output_path, [{"STAT_CODE": "121Y006"}])

    assert output_path.read_text(encoding="utf-8").strip() == '{"STAT_CODE": "121Y006"}'
