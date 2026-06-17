from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


# 채팅 화면 응답 검증
def test_chat_page():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "RAG 기반 부동산 의사결정 시스템" in response.text
    assert "/api/analyze" in response.text
    assert "1. 결론 요약" in response.text
    assert "2. 질문 해석" in response.text
    assert "3. 근거 및 상세 분석" in response.text
    assert "Agent Controller" in response.text


# 서버 상태 확인 API 검증
def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


# 분석 API 응답 구조 검증
def test_analyze_endpoint(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")

    response = client.post(
        "/api/analyze",
        json={"query": "이번 금리 인상이 성동구 아파트 매매가에 미친 영향을 알려줘"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["parsed_query"]["region"] == "성동구"
    assert data["parsed_query"]["policy_type"] == "interest_rate"
    assert data["market_summary"]["region"] == "성동구"
    assert data["sources"]["policies"] == ["policy_001"]
    assert data["sources"]["news"][0] == "news_001"
    assert "[질문 해석]" in data["answer"]
    assert "[결론 요약]" in data["answer"]
    assert "[정책 근거]" in data["answer"]
    assert "[관련 뉴스 요약]" in data["answer"]
    assert "[시세 변화 데이터]" in data["answer"]
    assert "[정책과 시세의 관계 해석]" in data["answer"]
    assert "[불확실성 및 추가 확인 필요 사항]" in data["answer"]
    assert "[참고 출처]" in data["answer"]
    assert "[컨텍스트]" not in data["answer"]
    assert "knowledge_graph" in data
    assert data["knowledge_graph"]["nodes"]
    assert data["knowledge_graph"]["edges"]
    assert "agent_plan" in data


# 빈 질문 요청 오류 검증
def test_analyze_endpoint_rejects_blank_query():
    response = client.post("/api/analyze", json={"query": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "query must not be blank"
