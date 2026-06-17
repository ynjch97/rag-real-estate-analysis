# 프로젝트 개발 규칙

## 프로젝트 폴더 구조 규칙

This repository is currently minimal and contains only the root `README.md`. As implementation is added, keep the layout predictable:

- `src/`: 실제 프로그램 코드 (RAG, Retriever, Agent, 분석 로직)
- `tests/`: 테스트 코드 (질문 분석 테스트, 시세 필터링 테스트)
- `data/`: 샘플 데이터 저장
- `docs/`: 설계 문서, 아키텍처 설명, 사용법
- `assets/`: 이미지, 다이어그램, 정적 파일

```
run_app.py                  # 서버 실행을 위함

src/
  data/
    __init__.py
    loaders.py              # JSONL 읽기
  collectors/
    transaction_collector.py # 시세 데이터 원천 데이터 수집
    news_collector.py       # 뉴스 데이터 원천 데이터 수집
    ecos_collector.py       # 정책(금리) 데이터 원천 데이터 수집
    policy_collector.py     # 정책(정책) 데이터 원천 데이터 수집
  preprocessing/
    transaction_cleaner.py  # 시세 데이터 정규화
    news_cleaner.py         # 뉴스 데이터 정규화
    policy_cleaner.py       # 정책 데이터 정규화
  embeddings/
    __init__.py
    build_index.py          # 정책/뉴스 JSONL -> FAISS 인덱스 생성
    vector_store.py         # FAISS 저장/로드/검색 공통 래퍼
  agents/
    task_planner.py         # 질문 유형 판단, 유형별 검색 순서 결정
    controller.py           # 정책/뉴스/시세 조회, 답변 문자열 생성
  retrieval/
    __init__.py
    query_analyzer.py       # 질문에서 지역/정책 키워드/의도/기간 추출
    policy_retriever.py     # FAISS 기반 정책 검색
    news_retriever.py       # FAISS 기반 뉴스 검색
    hybrid_search.py        # Hybrid Search 적용
  prices/
    __init__.py
    price_retriever.py      # transactions.jsonl 조회 (지역/기간 필터링)
    market_analyzer.py      # 월별 평균가, 중위값, 거래 건수 등을 계산
  analysis/
    __init__.py
    context_builder.py      # LLM 입력 컨텍스트 구성
    answer_generator.py     # 컨텍스트 기반 최종 답변 생성
  workflows/
    __init__.py
    market_impact_workflow.py # 질문 분석 → 정책/뉴스 검색 → 시세 분석 → 컨텍스트 구성 → 답변 생성 워크플로우
  api/
    __init__.py
    main.py                 # FastAPI 앱과 /api/analyze 엔드포인트
    schemas.py              # 요청/응답 모델

data/
  sample/
    policies.jsonl          # 정책 샘플 문서
    news.jsonl              # 뉴스 샘플 문서
    transactions.jsonl      # 거래별 아파트 매매 샘플 데이터
  reference/
    legal_dong_codes.csv    # 법정동 코드
  indexes/
    policy_faiss/           # policies.jsonl로 만든 FAISS 인덱스
    news_faiss/             # news.jsonl로 만든 FAISS 인덱스

tests/
  test_query_analyzer.py    # 규칙 기반 분석기 테스트
  test_price_retriever.py   # 시세 조회 테스트
  test_market_analyzer.py   # 일별 지표 계산 테스트
  test_context_builder.py   # 컨텍스트 구성 테스트
  test_market_impact_workflow.py # 워크플로우 테스트
  test_api.py               # /api/analyze 호출 테스트
  test_policy_retriever.py
  test_news_retriever.py
  test_transaction_cleaner.py
  test_transaction_collector.py
  test_news_cleaner.py
  test_news_collector.py
  test_policy_cleaner.py
  test_policy_collector.py
  test_ecos_collector.py
  test_hybrid_search.py
  test_agent_controller.py
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