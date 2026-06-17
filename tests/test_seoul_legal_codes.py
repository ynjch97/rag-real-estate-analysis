from src.prices.seoul_legal_codes import (
    find_legal_dong_code,
    get_sgg_cd,
    import_legal_dong_code_csv,
    load_legal_dong_codes,
    resolve_legal_dong_code_path,
    split_legal_dong_code,
)


# 테스트용 법정동 CSV 생성
def write_legal_code_csv(path):
    path.write_text(
        "\n".join(
            [
                "법정동코드,법정동명,폐지여부",
                "1100000000,서울특별시,존재",
                "1156000000,서울특별시 영등포구,존재",
                "1156011700,서울특별시 영등포구 당산동,존재",
                "1150010300,서울특별시 강서구 화곡동,존재",
                "1156011800,서울특별시 영등포구 당산동1가,폐지",
            ]
        ),
        encoding="utf-8-sig",
    )


# 서울시 동 단위 법정동 코드 로드 검증
def test_loads_seoul_legal_dong_codes(tmp_path):
    csv_path = tmp_path / "legal_codes.csv"
    write_legal_code_csv(csv_path)

    rows = load_legal_dong_codes(csv_path)

    assert rows == [
        {
            "legal_dong_code": "1156011700",
            "sido": "서울특별시",
            "sigungu": "영등포구",
            "dong": "당산동",
            "sgg_cd": "11560",
            "bjdong_cd": "11700",
        },
        {
            "legal_dong_code": "1150010300",
            "sido": "서울특별시",
            "sigungu": "강서구",
            "dong": "화곡동",
            "sgg_cd": "11500",
            "bjdong_cd": "10300",
        },
    ]


# 구/동 이름 기준 법정동 코드 조회 검증
def test_finds_legal_dong_code_by_sigungu_and_dong(tmp_path):
    csv_path = tmp_path / "legal_codes.csv"
    write_legal_code_csv(csv_path)

    row = find_legal_dong_code("영등포구", "당산동", csv_path)

    assert row["legal_dong_code"] == "1156011700"
    assert row["sgg_cd"] == "11560"
    assert row["bjdong_cd"] == "11700"


# 10자리 법정동 코드 분리 검증
def test_splits_legal_dong_code():
    result = split_legal_dong_code("1156011700")

    assert result == {
        "legal_dong_code": "1156011700",
        "sgg_cd": "11560",
        "bjdong_cd": "11700",
    }


# 구 이름 기준 구 코드 조회 검증
def test_gets_sgg_cd_by_sigungu(tmp_path):
    csv_path = tmp_path / "legal_codes.csv"
    write_legal_code_csv(csv_path)

    assert get_sgg_cd("영등포구", csv_path) == "11560"


# 외부 법정동 CSV 프로젝트 위치 복사 검증
def test_imports_legal_dong_code_csv(tmp_path):
    source_path = tmp_path / "source.csv"
    target_path = tmp_path / "reference" / "legal_dong_codes.csv"
    write_legal_code_csv(source_path)

    imported_path = import_legal_dong_code_csv(source_path, target_path)

    assert imported_path == target_path
    assert target_path.exists()
    assert find_legal_dong_code("영등포구", "당산동", target_path)["bjdong_cd"] == "11700"


# 환경변수 기준 법정동 CSV 경로 확인 검증
def test_resolves_legal_dong_code_path_from_env(tmp_path, monkeypatch):
    csv_path = tmp_path / "legal_codes.csv"
    write_legal_code_csv(csv_path)
    monkeypatch.setenv("LEGAL_DONG_CODE_PATH", str(csv_path))

    assert resolve_legal_dong_code_path() == csv_path
