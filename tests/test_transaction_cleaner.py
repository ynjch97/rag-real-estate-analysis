import json

from src.preprocessing.transaction_cleaner import normalize_transaction, normalize_transactions, save_transactions


# 서울시 원천 필드 정규화 검증
def test_normalizes_seoul_raw_transaction():
    raw = {
        "ACC_YEAR": "2024",
        "SGG_CD": "11500",
        "SGG_NM": "강서구",
        "BJDONG_CD": "10300",
        "BJDONG_NM": "화곡동",
        "BLDG_NM": "화곡센트럴",
        "OBJ_AMT": "75,000",
        "BLDG_AREA": "59.99",
        "FLR_NO": "7",
        "BUILD_YEAR": "2005",
        "DEAL_YMD": "20240115",
        "HOUSE_TYPE": "아파트",
    }

    transaction = normalize_transaction(raw)

    assert transaction == {
        "transaction_id": "tx_11500_20240115_0001",
        "region_code": "11500",
        "sido": "서울",
        "sigungu": "강서구",
        "dong": "화곡동",
        "apartment_name": "화곡센트럴",
        "contract_date": "2024-01-15",
        "price": 750000000,
        "area_m2": 59.99,
        "floor": 7,
        "built_year": 2005,
        "transaction_type": "매매",
    }


# 서울시 실제 API 후보 필드명 정규화 검증
def test_normalizes_seoul_api_alias_fields():
    raw = {
        "ACC_YEAR": "2024",
        "CGG_CD": "11500",
        "CGG_NM": "강서구",
        "STDG_NM": "화곡동",
        "APTFNO": "화곡센트럴",
        "THING_AMT": "75,000",
        "BLDG_AR": "59.99",
        "FLOOR": "7",
        "ARCH_YEAR": "2005",
        "CNTRCT_DE": "20240115",
        "HOUSE_TYPE": "아파트",
    }

    transaction = normalize_transaction(raw)

    assert transaction["region_code"] == "11500"
    assert transaction["sigungu"] == "강서구"
    assert transaction["dong"] == "화곡동"
    assert transaction["apartment_name"] == "화곡센트럴"
    assert transaction["contract_date"] == "2024-01-15"
    assert transaction["price"] == 750000000
    assert transaction["area_m2"] == 59.99
    assert transaction["floor"] == 7
    assert transaction["built_year"] == 2005


# 서울시 null 문자열 빈 값 처리 검증
def test_normalizes_seoul_null_string_fields():
    raw = {
        "CGG_CD": "11500",
        "CGG_NM": "강서구",
        "STDG_NM": "화곡동",
        "BLDG_NM": "베아트리스",
        "THING_AMT": "23000",
        "ARCH_AREA": 29.97,
        "FLR": 2.0,
        "ARCH_YR": "null",
        "CTRT_DAY": "20241231",
        "BLDG_USG": "연립다세대",
    }

    transaction = normalize_transaction(raw)

    assert transaction["price"] == 230000000
    assert transaction["built_year"] is None
    assert transaction["transaction_type"] == "매매"


# 필수 값 누락 거래 제외 검증
def test_skips_invalid_seoul_raw_transaction():
    transactions = normalize_transactions([{"SGG_CD": "11500", "SGG_NM": "강서구"}])

    assert transactions == []


# 정규화된 거래 데이터 JSONL 저장 검증
def test_saves_normalized_transactions(tmp_path):
    output_path = tmp_path / "transactions.jsonl"
    transactions = [
        {
            "transaction_id": "tx_11500_20240115_0001",
            "region_code": "11500",
            "sido": "서울",
            "sigungu": "강서구",
            "dong": "화곡동",
            "apartment_name": "화곡센트럴",
            "contract_date": "2024-01-15",
            "price": 750000000,
            "area_m2": 59.99,
            "floor": 7,
            "built_year": 2005,
            "transaction_type": "매매",
        }
    ]

    save_transactions(output_path, transactions)
    saved = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

    assert saved == transactions
