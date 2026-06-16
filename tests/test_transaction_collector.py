import json

from src.collectors.transaction_collector import (
    build_seoul_transaction_url,
    fetch_seoul_transactions_raw,
    parse_seoul_transaction_response,
    save_raw_transactions,
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


# 서울시 실거래가 API URL 생성 검증
def test_builds_seoul_transaction_url():
    url = build_seoul_transaction_url(
        api_key="test-key",
        start_index=1,
        end_index=1000,
        acc_year=2024,
        sgg_cd=11500,
        sgg_nm="강서구",
        bjdong_cd=10300,
        land_gbn=1,
        land_gbn_nm="대지",
        house_type="아파트",
    )

    assert url == (
        "http://openapi.seoul.go.kr:8088/test-key/json/tbLnOpendataRtmsV/1/1000/"
        "2024/11500/%EA%B0%95%EC%84%9C%EA%B5%AC/10300/1/%EB%8C%80%EC%A7%80/////%EC%95%84%ED%8C%8C%ED%8A%B8"
    )


# 서울시 API JSON 응답 row 추출 검증
def test_parses_seoul_transaction_response():
    payload = {
        "tbLnOpendataRtmsV": {
            "list_total_count": 1,
            "RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다"},
            "row": [
                {
                    "ACC_YEAR": "2024",
                    "SGG_CD": "11500",
                    "SGG_NM": "강서구",
                    "BJDONG_CD": "10300",
                    "BJDONG_NM": "화곡동",
                    "OBJ_AMT": "75,000",
                    "BLDG_AREA": "59.99",
                    "FLR_NO": "7",
                    "BUILD_YEAR": "2005",
                    "DEAL_YMD": "20240115",
                    "HOUSE_TYPE": "아파트",
                }
            ],
        }
    }

    rows = parse_seoul_transaction_response(payload)

    assert rows == payload["tbLnOpendataRtmsV"]["row"]


# 서울시 API 원천 데이터 수집 검증
def test_fetches_seoul_transactions_raw_with_fake_opener():
    payload = {
        "tbLnOpendataRtmsV": {
            "RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다"},
            "row": [{"SGG_NM": "강서구"}],
        }
    }
    seen_urls = []

    def fake_opener(url):
        seen_urls.append(url)
        return FakeResponse(payload)

    rows = fetch_seoul_transactions_raw(
        api_key="test-key",
        acc_year=2024,
        sgg_cd=11500,
        sgg_nm="강서구",
        house_type="아파트",
        opener=fake_opener,
    )

    assert rows == [{"SGG_NM": "강서구"}]
    assert seen_urls[0].startswith("http://openapi.seoul.go.kr:8088/test-key/json/tbLnOpendataRtmsV/1/1000/2024/11500/")


# 서울시 원천 거래 데이터 JSONL 저장 검증
def test_saves_raw_transactions(tmp_path):
    output_path = tmp_path / "raw_transactions.jsonl"
    save_raw_transactions(output_path, [{"SGG_NM": "강서구"}])

    assert output_path.read_text(encoding="utf-8").strip() == '{"SGG_NM": "강서구"}'
