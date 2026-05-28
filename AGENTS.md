# 프로젝트 개발 규칙

## 프로젝트 폴더 구조 규칙

This repository is currently minimal and contains only the root `README.md`. As implementation is added, keep the layout predictable:

- `src/`: 실제 프로그램 코드 (RAG, Retriever, Agent, 분석 로직)
- `tests/`: 테스트 코드 (질문 분석 테스트, 시세 필터링 테스트)
- `data/`: 샘플 데이터 저장
- `docs/`: 설계 문서, 아키텍처 설명, 사용법
- `assets/`: 이미지, 다이어그램, 정적 파일

```
src/
  data/
    loaders.py              # JSONL 읽기
  embeddings/
    build_index.py          # 정책/뉴스 JSONL -> FAISS 인덱스 생성
    vector_store.py         # FAISS 저장/로드/검색 helper

data/
  indexes/
    policy_faiss/           # policies.jsonl로 만든 FAISS 인덱스
    news_faiss/             # news.jsonl로 만든 FAISS 인덱스
```

Place modules near the domain they support instead of creating broad utility files prematurely.

## 실행/테스트 명령어 규칙

No build system or package manager is configured yet. Add commands when tooling is introduced. Recommended examples:

- `python -m pytest`: 전체 테스트 실행
- `python -m pytest tests/test_retriever.py`: 특정 테스트만 실행
- `python -m ruff check src tests`: 코드 스타일 검사
- `python -m ruff format src tests`: 자동 코드 정리

If another stack is adopted, document exact setup and execution commands in `README.md`.

## 코딩 스타일 규칙

- 파일명 : snake_case.py
- 함수명 : snake_case
- 클래스명 : PascalCase
- 4-space indentation (4칸 들여쓰기를 사용)

- 함수 이름을 실제 역할 기준으로 지을 것
  - get_data() 보다는 retrieve_policy_documents()
- 문서 파싱, 임베딩, CSV 처리 등은 검증된 라이브러리 사용
- API 키를 코드에 직접 작성하지 말 것

## 테스트 코드 규칙

- `tests/test_<module>.py`와 같은 명명 규칙을 따름
- `test_filters_transactions_by_region`과 같이 설명적인 테스트 함수를 사용
- 실제 개인정보 데이터는 쓰지 말 것

Prefer small fixtures with anonymized or synthetic real estate records. Do not commit production data, API keys, model outputs containing private text, or large generated artifacts.

## 보안 및 설정 규칙

- 비밀키는 환경 변수 사용 `OPENAI_API_KEY=<your-key>`
- 부동산 실거래 원본, 개인정보, 유료 API 응답 등은 올리지 말 것