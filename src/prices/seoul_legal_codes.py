import csv
import os
import shutil
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEGAL_DONG_CODE_PATH = PROJECT_ROOT / "data" / "reference" / "legal_dong_codes.csv"
LEGAL_DONG_CODE_PATH_ENV = "LEGAL_DONG_CODE_PATH"
SEOUL_SIDO_NAME = "서울특별시"


# 법정동 CSV에서 서울시 존재 법정동 목록 로드
def load_legal_dong_codes(path: str | Path | None = None) -> list[dict[str, str]]:
    csv_path = resolve_legal_dong_code_path(path)
    rows = _read_legal_code_csv(csv_path)
    legal_codes: list[dict[str, str]] = []

    for row in rows:
        legal_code = str(row.get("법정동코드", "")).strip()
        legal_name = str(row.get("법정동명", "")).strip()
        deleted = str(row.get("폐지여부", "")).strip()

        if deleted != "존재" or not _is_seoul_dong_code(legal_code, legal_name):
            continue

        parts = legal_name.split()
        legal_codes.append(
            {
                "legal_dong_code": legal_code,
                "sido": parts[0],
                "sigungu": parts[1],
                "dong": parts[2],
                "sgg_cd": legal_code[:5],
                "bjdong_cd": legal_code[5:],
            }
        )

    return legal_codes


# 구/동 이름으로 서울시 법정동 코드 조회
def find_legal_dong_code(sigungu: str, dong: str, path: str | Path | None = None) -> dict[str, str]:
    normalized_sigungu = sigungu.strip()
    normalized_dong = dong.strip()

    for row in load_legal_dong_codes(path):
        if row["sigungu"] == normalized_sigungu and row["dong"] == normalized_dong:
            return row

    raise ValueError(f"Legal dong code not found: {normalized_sigungu} {normalized_dong}")


# 구 이름으로 서울시 법정동 코드 목록 조회
def find_legal_dong_codes_by_sigungu(sigungu: str, path: str | Path | None = None) -> list[dict[str, str]]:
    normalized_sigungu = sigungu.strip()
    rows = [row for row in load_legal_dong_codes(path) if row["sigungu"] == normalized_sigungu]

    if not rows:
        raise ValueError(f"Legal dong codes not found: {normalized_sigungu}")

    return rows


# 10자리 법정동 코드를 API용 구/동 코드로 분리
def split_legal_dong_code(legal_dong_code: str | int) -> dict[str, str]:
    code = str(legal_dong_code).strip()
    if len(code) != 10 or not code.isdigit():
        raise ValueError(f"Legal dong code must be 10 digits: {legal_dong_code}")

    return {
        "legal_dong_code": code,
        "sgg_cd": code[:5],
        "bjdong_cd": code[5:],
    }


# 구 이름으로 서울시 구 코드 조회
def get_sgg_cd(sigungu: str, path: str | Path | None = None) -> str:
    normalized_sigungu = sigungu.strip()

    for row in load_legal_dong_codes(path):
        if row["sigungu"] == normalized_sigungu:
            return row["sgg_cd"]

    raise ValueError(f"SGG code not found: {normalized_sigungu}")


# 법정동 CSV 기본 경로 확인
def resolve_legal_dong_code_path(path: str | Path | None = None) -> Path:
    _load_env()
    csv_path = Path(path or os.getenv(LEGAL_DONG_CODE_PATH_ENV) or DEFAULT_LEGAL_DONG_CODE_PATH)

    if not csv_path.exists():
        raise FileNotFoundError(
            "Legal dong code CSV not found. "
            f"Place the file at {DEFAULT_LEGAL_DONG_CODE_PATH} "
            f"or set {LEGAL_DONG_CODE_PATH_ENV} in .env."
        )

    return csv_path


# 외부 법정동 CSV를 프로젝트 기준 위치로 복사
def import_legal_dong_code_csv(source_path: str | Path, target_path: str | Path | None = None) -> Path:
    source = Path(source_path)
    target = Path(target_path or DEFAULT_LEGAL_DONG_CODE_PATH)

    if not source.exists():
        raise FileNotFoundError(f"Source legal dong code CSV not found: {source}")

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target


# 법정동 CSV 인코딩 자동 판별 로드
def _read_legal_code_csv(path: Path) -> list[dict[str, Any]]:
    for encoding in ("cp949", "utf-8-sig", "utf-8"):
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError("legal_code_csv", b"", 0, 1, f"Cannot decode CSV: {path}")


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


# 서울시 동 단위 법정동 코드 여부 확인
def _is_seoul_dong_code(legal_code: str, legal_name: str) -> bool:
    if len(legal_code) != 10 or not legal_code.isdigit():
        return False

    parts = legal_name.split()
    if len(parts) < 3 or parts[0] != SEOUL_SIDO_NAME:
        return False

    return legal_code[:2] == "11" and legal_code[5:] != "00000"
