# RAG 기반 부동산 의사결정 시스템 : 정책 변화에 따른 시세 영향 분석

## 1. 개요
- 부동산 의사결정에 필요한 정보는 매우 방대하고 분산되어 있음
- 국토교통부의 실거래가, 지자체의 보도자료, 대출 규제 관련 금융 정책 등을 직접 수집하고 비교 분석해야 함
  - 정보 간 연결의 어려움 : 정책 자료와 뉴스, 시세 데이터를 각각 조회한 후 이를 수동으로 비교해야 함
- 외부 데이터를 실시간으로 주입하는 RAG(Retrieval-Augmented Generation) 아키텍처가 필요
  - LLM을 활용해도 학습 데이터 기준 시점 이후의 정책 변경이나 시세 변동은 반영되지 않아 Hallucination 위험
- 정책·뉴스·시세 데이터를 통합적으로 분석하여 정책 변화와 시세 간 관계를 설명하는 시스템

## 2. 데이터 구성
- 정책, 뉴스, 시세 데이터를 중심으로 구성

### 2-1. 정책 데이터
- 부동산 시장 변화의 원인을 설명하기 위한 핵심 데이터
  - 대출 규제 및 금리 변화는 수요에 직접적인 영향
  - 공급 정책은 중장기적인 가격 형성에 영향
 
### 2-2. 뉴스 데이터
- 정책, 시장 반응, 시세 변화를 연결하는 설명 정보
  - 정책은 공식 문서 형태로 제공되기 때문에 직접적인 해석이 어렵지만 뉴스는 정책의 의미, 시장 반응, 전문가 의견 등을 포함
- 키워드와 날짜 기반 필터링으로 정책 시행 시점 전후 기사를 정밀하게 수집

### 2-3. 시세 데이터
- 아파트 매매 실거래가, 거래량 등의 데이터
- 정책 변화가 실제 가격에 미친 영향을 정량적으로 검증하는 결과 변수로 사용
- 실제 시장 반응을 수치적으로 보여주는 지표

## 3. 데이터 수집

### 3-1. 정책 데이터
- 국토교통부
  - https://www.molit.go.kr/USR/NEWS/m_71/lst.jsp
  - 대출 규제, 공급 정책, 재건축 완화, 세제 변화 등 핵심 정책 이벤트 추적
  - 수집 방식 : HTML 크롤링, 키워드 NLP 태깅
  - 수집 주기 : 주 1회
  - 수집 데이터 : 보도자료 제목, 발표 일자, 정책 키워드(대출 규제/공급 정책/세금 정책/청약 제도/재건축/재개발), 지역 키워드, 정책 시행일 등
- 한국은행
  - https://www.bok.or.kr/portal/main/main.do
  - 기준 금리, 대출 규제, DSR/LTV 정책, 유동성 공급
  - 수집 방식 : Open API로 정형 데이터 수집
  - 수집 주기 : 월 1회 + 금융통화위원회 회의 익일 (연 8회)
  - 수집 데이터 : 기준금리, 금리 인상/인하 여부 등

### 3-2. 뉴스 데이터
- 네이버 뉴스
  - https://news.naver.com/
  - Open API : https://developers.naver.com/docs/serviceapi/search/news/news.md
  - 정책 발표 직후 언론 반응 분석
  - 경제 뉴스 위주의 수집 (한국경제, 매일경제, 서울경제, 이데일리, 연합뉴스)
  - "전세 대란 우려" 등의 긍정/부정 표현 빈도 파악이 중요
  - 수집 방식 : 뉴스 API JSON 타입으로 수집
  - 수집 주기 : 일 1회
  - 수집 데이터 : 기사 제목, 본문, 작성 일시, 지역 키워드, 정책 키워드, 감성 분석 점수

### 3-3. 시세 데이터
- 국토교통부 실거래가 공개시스템 : https://rt.molit.go.kr/
  - 정책 발표 전후 가격 변화, 특정 지역 거래량 급증, 신고가 발생 빈도 등을 파악 가능
- 공공데이터포털 Open API 국토교통부_아파트 매매 실거래가 자료 : https://www.data.go.kr/data/15126469/openapi.do
- 공공데이터포털 Open API 서울특별시_부동산 실거래가 정보 : https://www.data.go.kr/data/15052419/fileData.do
  - 서울시 부동산 실거래가 정보 : https://data.seoul.go.kr/dataList/OA-21275/S/1/datasetView.do ***(채택)***
- 데이터 수집
  - 수집 방식 : Open API로 데이터 수집
  - 수집 주기 : 월 1회
  - 수집 데이터 : 거래 금액, 거래 일자, 법정동, 아파트명, 전용면적, 층수, 건축년도, 거래 유형, 거래량

## 4. 데이터 전처리 및 청킹 전략
- 불필요한 HTML 태그 제거, 특수문자 및 불용어 제거 등

### 4-1. 정책 데이터
- 표와 이미지를 제거
- 문단 또는 의미 단위로 분할하기 위해 500~800 토큰을 기준으로 100 토큰 Overlap 적용
``` json
{"policy_id":"정책번호",
 "title":"제목",
 "url":"출처",
 "published_date":"발표일",
 "effective_date":"시행일",
 "policy_type":"정책유형",
 "region_tags":"적용지역",
 "keywords":"키워드",
 "summary":"요약"}
```

### 4-2. 뉴스 데이터
- HTML 태그를 제거, 광고성 문장 필터링
- 제목 유사도를 기준으로 중복 기사 제거
- 200~300 토큰을 기준으로 50 토큰 Overlap 적용
- 감성 분석보다 "시장 신호"를 우선으로 함
``` json
{"news_id":"뉴스번호",
"title":"제목",
"url":"출처",
"published_date":"작성일",
"news_site":"언론사",
"region_tags":"적용지역",
"policy_tags":"관련정책",
"sentiment_score":"감성분석점수",
"market_signal":"시장신호", // 매수세 증가, 거래 위축, 전세 불안, 신고가 등
"summary":"요약"}
```

### 4-3. 시세 데이터
- 결측값 처리, 거래 금액 상하위 1% 가량을 이상치로 설정해 제거
- 거래금액 숫자 변환, 계약일 월 단위 정규화, 지역 코드 표준화
- 정형 데이터이므로 인덱싱하여 시계열 구조로 저장
``` json
{"transaction_id":"거래번호",
"region_code":"법정동/행정구역코드",
"sido":"시도",
"sigungu":"시군구",
"dong":"동",
"apartment_name":"단지명",
"contract_date":"계약일",
"price":"거래금액",
"area_m2":"전용면적",
"floor":"층",
"built_year":"건축년도",
"transaction_type":"거래유형"} // 매매, 전세, 월세 등
```

## 5. 시스템 아키텍처

### 5-1. User Query
- 사용자의 자연어 질문이 입력되는 단계
- "강남 집값 왜 올랐어?" -> 이후 모듈에서 분석 가능하도록 의미 단위로 해석됨

### 5-2. Query Analyzer
- 지역, 시간 등의 핵심 엔티티와 질의 의도(원인 분석, 비교, 전망 등) 추출
- 비정형 자연어를 검색에 적합한 형태로 변환 + 필요 시 키워드 확장(Query Rewriting)
- 유사도 기반 검색 성능에 직접적인 영향을 미치는 전처리 단계

### 5-3. Agent Controller
- 질의의 복잡도를 판단하고, 어떤 데이터를 어떤 순서로 검색할지 전략을 결정하는 핵심 모듈
- "집값 상승 원인" -> 정책 → 뉴스 → 시세 순으로 제어
- 중간 결과를 바탕으로 추가 검색을 수행하는 멀티 스텝 Retrieval 및 Reasoning -> 단순 RAG를 넘어서는 Agentic RAG 구조를 구현

### 5-4. Retriever Layer
- 정책/뉴스 데이터
  - Embedding Model을 통해 벡터화되어 Vector DB에 저장됨
  - 유사도 계산(Cosine Similarity 등)을 통해 관련 문서 검색
  - 하이브리드 검색(Hybrid Search) 적용
    - **BM25 알고리즘을 통한 정확한 키워드 일치 검색 + 코사인 유사도(Cosine Similarity)를 활용한 Vector Search**
    - `BM25` : "DSR", "LTV", "금리 인상", "광명"
    - `Vector Search` : "집값 왜 올랐어?" <-> "매수세 증가", "공급 부족" 연결
- 시세 데이터
  - 정형 데이터이므로 벡터 검색이 아닌 지역·시간 조건 기반 필터링 및 시계열 조회 방식

### 5-5. Context Builder
- LLM 입력용 컨텍스트 구성
- 지식 그래프 구조를 활용하여 데이터 간 관계를 정렬하고, 기준에 따라 순서를 재배열(Re-ranking)
- 불필요한 정보는 제거하고 핵심 정보만 유지 -> LLM이 정확한 추론을 수행하도록 함

### 5-6. LLM Generator
- 구성된 컨텍스트를 기반으로 정책 변화와 시세 간의 관계를 분석하고 자연어 응답을 생성
- 단순 요약이 아닌 원인(정책) → 과정(시장 반응) → 결과(시세 변화) 구조
- 원본 검색 데이터와 대조하는 검증 절차를 포함해 Hallucination을 최소화하고 신뢰성을 확보

## 6. RAG 기반 검색 및 분석 설계
- 검색(Retrieval) 흐름 
  - 사용자 질의 -> 임베딩 벡터로 변환 -> 벡터 DB -> 유사도 계산 -> Top-k 문서 추출

### 6-1. 임베딩 및 벡터 인덱싱
- [TODO]

### 6-2. Retrieval 구조 및 유사도 계산 방식
- [TODO]

### 6-3. 지식 그래프 구성
- [TODO]

## 7. Agent 기반 의사결정 지원 설계

### 7-1. Query 분석 및 작업 분해
``` plain
[질의] "이번 대출 규제가 마포구 아파트 시세에 미친 영향을 알려줘."

[작업 분해]
① 최신 대출 규제 정책 문서 검색
② 마포구 실거래가 시계열 데이터 조회
③ 정책 시행 전후 시세 변동 비교
④ 관련 뉴스(시장 반응) 검색
⑤ 결과 통합 및 응답 생성
```
- [TODO]

### 7-2. 멀티 스텝 Retrieval 및 Reasoning
- [TODO]

### 7-3. 컨텍스트 구성 전략
``` plain
[질문 해석]
- 지역/기간:
- 정책 이벤트:

[결론 요약]

[정책 근거]: {검색된 정책 요약, 발표일/시행일}
→ [관련 뉴스 요약]: {시장 반응 및 전문가 의견}
→ [시세 변화 데이터]: {평균 매매가 및 거래량 변동 수치}

[정책과 시세의 관계 해석]
[불확실성 및 추가 확인 필요 사항]
[참고 출처]
```
- 중복 정보 제거, 핵심 문장만 추출, Top-k 방식 사용
- 지식 그래프를 기반으로 데이터를 연결해 정책-뉴스-시세 관계 설명의 일관성 확보
- *"제공된 정보에 없는 내용은 절대 추측하지 마시오"*라는 제약 조건을 컨텍스트와 함께 전달하여 Hallucination 방지

## 8. 참고자료
- `example` 폴더
  - FAISS 기반 임베딩, 질문 분석, FastAPI/CLI 응답 구조

### 8-1. example\modules\aibot
- `create_embeddings.py` : 문서를 임베딩하고 청킹한 뒤 FAISS에 저장하는 흐름
- `search_info.py` : 질문 분석 → 관련 문서 검색 → 컨텍스트 구성 → LLM 답변 생성 흐름
  - 본 프로젝트는 정책 검색, 뉴스 검색, 시세 조회, 분석 생성을 분리해야 함
- `qa_bot.py` : FastAPI/CLI 형태로 질의응답 인터페이스를 제공하는 구조
- `config_utils.py` : 설정 파일을 읽고 경로를 관리하는 방식

### 8-2. requirements.txt 설치
- `requirements.txt` : 프로젝트에 필요한 라이브러리 목록

| 패키지               | 역할                   |
| ------------------- | --------------------- |
| openai              | GPT API 연결           |
| langchain           | RAG 파이프라인          |
| langchain-openai    | LangChain + OpenAI 연결|
| langchain-community | FAISS 등 외부 기능      |
| faiss-cpu           | 벡터 검색(DB)           |
| fastapi             | API 서버               |
| uvicorn             | FastAPI 실행           |
| pydantic            | API 데이터 검증         |
- 프로젝트 전용 Python 가상환경(venv) 생성
  - 패키지 충돌 방지, 프로젝트 독립성 확보, GitHub 협업 편함, RAG 프로젝트는 라이브러리 많음
  - `.venv`는 GitHub에 올리지 않음
``` bash
cd "D:\STUDY\git_ragRealEstateAnalysis\example"
python -m pip install -r requirements.txt # requirements.txt 안에 적힌 라이브러리들을 설치

# Would you like to create a virtual environment with these packages to isolate your dependencies?
# 해당 팝업에 Create 선택 후 Python 선택, requirements.txt 선택하고 라이브러리 설치
```
- 터미널에 아래와 같이 나오는지 확인
``` bash
(.venv) PS D:\STUDY\git_ragRealEstateAnalysis\example> python --version
Python 3.10.2
```
- 프로젝트 받을 때 : `pip install -r requirements.txt`
- `.venv` 삭제 후 다시 실행할 때
``` bash
cd D:\STUDY\git_ragRealEstateAnalysis
deactivate
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\example\requirements.txt
```
- 정상 설치되었는지 확인
``` bash
(.venv) PS D:\STUDY\git_ragRealEstateAnalysis> python -m pip list
Package                  Version
------------------------ ---------
aiohappyeyeballs         2.6.2
aiohttp                  3.13.5
aiosignal                1.4.0

===== 생략 =====
```

### 8-3. example 실행
``` bash
# 실행은 반드시 이 폴더에서
cd D:\STUDY\git_ragRealEstateAnalysis\example\modules\aibot

# python -X utf8로 CLI 대화형 실행
python -X utf8 qa_bot.py --mode cli

# API 서버 실행
python -X utf8 qa_bot.py --mode api

⚡️ 설정을 로드하는 중...
🤖 AI 시스템을 초기화하는 중...
✅ AI 시스템 초기화 완료! (소요시간: 0.86초)
🚀 API 서버 시작...
INFO:     Started server process [23624]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5001 (Press CTRL+C to quit)
```
- http://127.0.0.1:5001 로 접속
- 새 터미널 열어 아래와 같이 상태 확인 가능
``` bash
(.venv) PS D:\STUDY\git_ragRealEstateAnalysis> Invoke-RestMethod http://127.0.0.1:5001/health

status           timestamp active_sessions
------           --------- ---------------
healthy 1779989389.4502301               0
```
- 질문 API 호출 예시
``` bash
Invoke-RestMethod `
  -Uri http://127.0.0.1:5001/api/query `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body '{"query":"이 문서들은 어떤 내용을 담고 있어?"}'
                                      
response                           
--------                            
이 문서들은 주로 일본어 학습과 관련된 내용과 건국대학교의 인공지능 전공 강의에 대한 정보를 담고 있습니다. 구체적으로는:...
```
- 한글이 깨지면 -> `chcp 65001` 입력 / 터미널 재실행

## 9. 프로젝트 구조 및 환경 설정

### 9-1. AGENT.md
- 이 Repository에서 작업하는 AI/개발자를 위한 작업 규칙 문서
  - 프로젝트 구성 방식 / 폴더 구조 정리 / 코딩 스타일 / 코드 네이밍 규칙
  - AI 코딩 Agent / GitHub 관리 / API 키 보안

### 9-2. 역할 분리
- 정책/뉴스 : FAISS 검색 대상 (벡터 검색)
- 시세 : 정형 데이터 조회 대상 (조건 기반 필터링/시계열 조회)
- 분석 : 정책 전후 가격과 거래량 변화를 계산
  - 지식 그래프 : 정책→시장 반응→시세 변화 인과 관계 명시적 표현
  - Agent : 질의 복잡도에 따라 단일 검색 또는 멀티 스텝 작업으로 확장
  - Hallucination 방지 : 모든 수치 데이터 원본 소스 대조, 확인되지 않은 정보 명시적 표기
- API : 사용자의 질문을 받아 워크플로우를 실행

### 9-3. 프로젝트 구조
```
```

## 10. 개발 이력

### 10-1. 샘플 데이터 생성
``` plain
data/sample/policies.jsonl
data/sample/news.jsonl
data/sample/transactions.jsonl
```

### 10-2. 정책/뉴스 FAISS 인덱스
- JSONL을 읽어서 검색 가능한 FAISS 벡터 인덱스로 변환
``` bash
# FAISS 인덱스 저장 결과 폴더
data/indexes/policy_faiss/
data/indexes/news_faiss/
```
- `policies.jsonl`, `news.jsonl`을 읽어서 임베딩하고 저장하는 코드 필요
  - `loaders.py` : `policies.jsonl`, `news.jsonl`을 LangChain Document로 변환
  - `vector_store.py` : FAISS 생성/저장/로드 helper
  - `build_index.py` : 정책/뉴스 FAISS 인덱스 생성 실행 파일
- FAISS 인덱스 저장 실행
``` bash
# 실행 테스트
python -m src.embeddings.build_index --dry-run

Policy documents: 5
News documents: 12
Dry run only. FAISS indexes were not created.

# index.faiss, index.pkl 생성하기
python -m src.embeddings.build_index

💾 Policy documents: 5
💾 News documents: 12
💾 Policy FAISS index saved to: D:\STUDY\git_ragRealEstateAnalysis\data\indexes\policy_faiss
💾 News FAISS index saved to: D:\STUDY\git_ragRealEstateAnalysis\data\indexes\news_faiss
```

### 10-3. 질문을 구조화하는 규칙 기반 분석기
- 사용자 질문을 이후 검색/분석 모듈이 쓰기 쉬운 형태로 바꾸는 것
- `query_analyzer.py`
``` python
# "이번 금리 인상이 성동구 아파트 매매가에 미친 영향을 알려줘"
# 이와 같은 입력을 아래 구조로 바꿈 (현재는 LLM 쓰지 말고 규칙으로)
{
    "region": "성동구",
    "event_keyword": "금리 인상",
    "intent": "policy_impact",
    "property_type": "apartment",
    "transaction_type": "sale",
    "months_before": 6,
    "months_after": 6,
}
```
- 현재 동작
  - 성동구, 광진구, 강남구 추출
  - 금리 인상, 대출 규제, 공급 정책 규칙 추출
  - policy_type을 interest_rate, loan_regulation, supply_policy로 분류
  - 기본값: apartment, sale, 전후 6개월
  - .to_dict()로 이후 workflow 입력에 바로 넘길 수 있음
- 테스트 실행
``` bash
# pytest 설치
(.venv) PS D:\STUDY\git_ragRealEstateAnalysis> python -m pip install pytest
(.venv) PS D:\STUDY\git_ragRealEstateAnalysis> python -m pytest --version
pytest 9.0.3

# pytest 실행
(.venv) PS D:\STUDY\git_ragRealEstateAnalysis> python -m pytest tests/test_query_analyzer.py
=========================================== test session starts ===========================================
platform win32 -- Python 3.10.2, pytest-9.0.3, pluggy-1.6.0
rootdir: D:\STUDY\git_ragRealEstateAnalysis
plugins: anyio-4.13.0, langsmith-0.8.6
collected 5 items 

tests\test_query_analyzer.py ..... [100%]

=========================================== 5 passed in 0.06s ===========================================
```

### 10-4. 시세 조회와 월별 집계
- 시세 데이터 : 조건 기반 필터링 및 시계열 조회 방식
- 월별 지표 : 입력 데이터를 가공해서 만든 분석 지표
  - 시세 원천 데이터 `transactions.jsonl` > 지역/기간으로 필터링 > 월별 집계 계산 > 월별 지표
``` json
// 예시
{
  "month": "2024-01",           // contract_date → month로 변환
  "region": "성동구",            // sigungu → region으로 사용
  "avg_price": 1367500000,      // price 의 평균가
  "median_price": 1367500000,   // price 의 중위값
  "price_per_m2": 19000000,     // price / area_m2 → price_per_m2
  "transaction_count": 2,       // 거래 건수
  "mom_change_rate": -1.2       // 전월 대비 평균 가격 변화율
}
```
- 테스트 실행
``` bash
# pytest 실행
(.venv) PS D:\STUDY\git_ragRealEstateAnalysis> python -m pytest tests/test_price_retriever.py tests/test_market_analyzer.py

5 passed in 0.10s
```

### 10-5. 정책 영향 분석 워크플로우
- `context_builder.py` : 7-3. 컨텍스트 구성 전략 형식으로 정책/뉴스/시세 컨텍스트 구성
- `answer_generator.py` : 현재는 OpenAI 호출 없이 템플릿 기반 답변 생성
- `market_impact_workflow.py` : 전체 흐름을 하나로 묶는 워크플로우 파일 / 전체 실행 순서를 담당
  - 질문 분석 (`query_analyzer.py`) + 정책/뉴스 인덱스 (`build_index.py`, `vector_store.py`) + 시세 조회/집계 (`price_retriever.py`, `market_analyzer.py`)
- 현재까지는 FAISS 검색이 아니라 샘플 JSONL 기반 규칙 매칭
  - API 키 없이 테스트 가능하도록 MVP 구현
- 테스트 실행
``` bash
# pytest 실행
(.venv) PS D:\STUDY\git_ragRealEstateAnalysis> python -m pytest tests/test_market_impact_workflow.py -v

tests/test_market_impact_workflow.py::test_analyzes_market_impact_end_to_end PASSED
tests/test_market_impact_workflow.py::test_analyzes_loan_regulation_query PASSED

# 워크플로우 테스트
(.venv) PS D:\STUDY\git_ragRealEstateAnalysis> python -c "from src.workflows.market_impact_workflow import analyze_market_impact; result = analyze_market_impact('이번 금리 인상이 성동구 아파트 매매가에 미친 영향을 알려줘'); print(result['answer'])"

[결론 요약]
성동구의 금리 인상 전후 시세를 비교한 결과, 평균 가격 변화율은 -0.49%입니다.
월평균 거래량 변화율은 0.0%입니다.

(중략)
```

### 10-6. FastAPI 엔드포인트 만들기
- 분석 워크플로우를 API 형태로 호출할 수 있게 함
  - `api/main.py` : FastAPI 앱과 /api/analyze 엔드포인트
  - `api/schemas.py` : 요청/응답 Pydantic 모델
``` text
사용자 질문 (POST /api/analyze)
↓
market_impact_workflow.analyze_market_impact(query)
↓
질문 분석 + 정책/뉴스 조회 + 월별 시세 집계 + 답변 생성
↓
JSON 응답 반환
```
- FastAPI 엔드포인트 구조
``` json
Method: POST
URL: http://127.0.0.1:5001/api/analyze
Body:
{
  "query": "이번 금리 인상이 성동구 아파트 매매가에 미친 영향을 알려줘"
}
```
- 터미널 테스트 실행
``` bash
# FastAPI 서버 실행 (종료 시 Ctrl + C)
(.venv) PS D:\STUDY\git_ragRealEstateAnalysis> python -X utf8 run_app.py --mode api

# 새 터미널에서 상태 확인
Invoke-RestMethod http://127.0.0.1:8000/health

# 새 터미널에서 분석 API 테스트
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/analyze `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body '{"query":"이번 금리 인상이 성동구 아파트 매매가에 미친 영향을 알려줘"}'

# 한글 깨지면 아래 먼저 실행
chcp 65001
```
- 브라우저 테스트 실행
  - FastAPI가 자동으로 제공하는 Swagger 화면 : http://127.0.0.1:8000/docs
  - `Try it out` -> Request body 에 JSON 입력 -> `Execute`
``` json
{
  "query": "이번 금리 인상이 성동구 아파트 매매가에 미친 영향을 알려줘"
}
```

### 10-7. FAISS 검색으로 교체
- `market_impact_workflow.py` : 정책/뉴스의 샘플 JSONL 직접 검색 방식에서 FAISS 기반 검색 방식으로 변경
  - `policy_retriever.py` : data/indexes/policy_faiss 로드 -> 질문/정책 키워드로 관련 정책 Top-k 검색
  - `news_retriever.py` : data/indexes/news_faiss 로드 -> 지역 + 정책 기준 관련 뉴스 Top-k 검색
- 테스트 실행
``` bash
# pytest 실행
(.venv) PS D:\STUDY\git_ragRealEstateAnalysis> python -m pytest tests/test_policy_retriever.py tests/test_news_retriever.py -v

5 passed in 0.10s
```

### 10-8. 시세 데이터 수집
- 서울특별시 부동산 실거래가 API
- `data/reference/legal_dong_codes.csv` : 법정동 코드 CSV
  - 예시 : `1156011700` -> `sgg_cd=11560`, `bjdong_cd=11700`
- `seoul_legal_codes.py` : 법정동 CSV를 읽어 구/동 이름을 서울시 API 코드로 변환
  - `영등포구`, `당산동` -> `11560`, `11700`
- `transaction_collector.py` : 서울특별시 부동산 실거래가 API 호출 (지역/기간별 거래 원천 데이터 수집)
  - `data/raw/seoul_transactions_2024_11500.jsonl` -> 원천 데이터 저장
- `transaction_cleaner.py` : [4-3. 시세 데이터](#4-3-시세-데이터) 구조로 정규화 (price 숫자 변환, contract_date YYYY-MM-DD 정규화 등)
  - `data/processed/transactions_2024_11500.jsonl` -> 정규화된 데이터 저장
- 테스트 실행
``` bash
# 법정동 코드 변환 테스트
python -c "from src.prices.seoul_legal_codes import find_legal_dong_code; print(find_legal_dong_code('영등포구', '당산동'))"

# 호출 테스트
python -c "from src.collectors.transaction_collector import fetch_seoul_transactions_raw; rows = fetch_seoul_transactions_raw(acc_year=2024, sgg_cd=11500, sgg_nm='강서구', bjdong_cd=10300, land_gbn=1, land_gbn_nm='대지', house_type='아파트'); print(len(rows)); print(rows[:1])"

# 구/동 이름 기준 호출 테스트
python -c "from src.collectors.transaction_collector import fetch_seoul_transactions_by_dong; rows = fetch_seoul_transactions_by_dong(acc_year=2024, sigungu='영등포구', dong='당산동'); print(len(rows)); print(rows[:1])"

# 정규화 테스트
python -c "from src.collectors.transaction_collector import fetch_seoul_transactions_raw; from src.preprocessing.transaction_cleaner import normalize_transactions; rows = fetch_seoul_transactions_raw(acc_year=2024, sgg_cd=11500, sgg_nm='강서구', bjdong_cd=10300, land_gbn=1, land_gbn_nm='대지', house_type='아파트'); tx = normalize_transactions(rows); print(len(tx)); print(tx[:1])"

# 질문 분석 -> 데이터 수집 테스트
python -c "from src.workflows.market_impact_workflow import analyze_market_impact; result = analyze_market_impact('2026년 개포동 부동산에 대해 알려줘'); print(result['parsed_query']); print(len(result['monthly_metrics'])); print(result['monthly_metrics'][:1])"
```


