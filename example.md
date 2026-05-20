# RAG 기반 부동산 의사결정 시스템

> 정책·뉴스·시세 데이터 통합 분석 + Agent 기반 멀티 스텝 추론

---

## Phase 1: 프로젝트 구조 및 환경 설정

```
realestate_rag/
├── app/
│   ├── services/
│   │   ├── policy_collector.py    # 정부 보도자료 크롤링, 한국은행 ECOS API
│   │   ├── news_collector.py      # 네이버 Search API 뉴스 수집
│   │   ├── price_collector.py     # 국토교통부 실거래가 Open API
│   │   ├── preprocessor.py        # PDF: PDFPlumber, 뉴스: HTML제거, 시세: 결측값 처리
│   │   ├── chunker.py             # 정책 500~800토큰, 뉴스 200~300토큰, 시세: 정형 시계열
│   │   ├── embedding_store.py     # FAISS 또는 Chroma + text-embedding-3-small
│   │   ├── hybrid_search.py       # BM25 + Vector Search + Re-ranking
│   │   ├── knowledge_graph.py     # Neo4j (정책→시세 영향, 지역→뉴스→시세 관계)
│   │   ├── context_builder.py     # 원인→해석→결과 구조 컨텍스트 구성
│   │   └── rag_chain.py           # LLM 답변 생성 + 검증 절차
│   ├── agents/
│   │   ├── query_analyzer.py      # 지역, 시간, 핵심 엔티티, 의도 추출
│   │   └── agent_controller.py    # 멀티 스텝 Retrieval & Reasoning
│   └── api/routes.py
├── frontend/streamlit_app.py
├── data/ (정책, 뉴스, 시세)
└── config.ini

데이터:
- 정책: 국토교통부/기획재정부 보도자료 (주 1회), 한국은행 ECOS API (연 8회)
- 뉴스: 네이버 Search API ('부동산 규제', '아파트 시세' 등 키워드, 일 1회)
- 시세: 국토교통부 실거래가 공개 시스템 API (지역별 아파트 거래, 월 1회)

이중 구조: 비정형(정책/뉴스) → 벡터 검색, 정형(시세) → 조건 기반 필터링/시계열 조회
지식 그래프: 정책→시장 반응→시세 변화 인과 관계 명시적 표현 (Neo4j)
Agent: 질의 복잡도에 따라 단일 검색 또는 멀티 스텝 작업으로 확장
Hallucination 방지: 모든 수치 데이터 원본 소스 대조, 확인되지 않은 정보 명시적 표기
```
