from src.workflows.market_impact_workflow import analyze_market_impact


# 시장 영향 분석 워크플로우 전체 결과 구조 검증
def test_analyzes_market_impact_end_to_end(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")

    result = analyze_market_impact("이번 금리 인상이 성동구 아파트 매매가에 미친 영향을 알려줘")

    assert result["parsed_query"]["region"] == "성동구"
    assert result["parsed_query"]["policy_type"] == "interest_rate"
    assert result["policies"][0]["policy_id"] == "policy_001"
    assert result["news"][0]["news_id"] == "news_001"
    assert result["market_summary"]["region"] == "성동구"
    assert result["market_summary"]["policy_month"] == "2024-01"
    assert "[질문 해석]" in result["answer"]
    assert "[결론 요약]" in result["answer"]
    assert "[정책 근거]" in result["answer"]
    assert "[관련 뉴스 요약]" in result["answer"]
    assert "[시세 변화 데이터]" in result["answer"]
    assert "[정책과 시세의 관계 해석]" in result["answer"]
    assert "[불확실성 및 추가 확인 필요 사항]" in result["answer"]
    assert "[참고 출처]" in result["answer"]
    assert "[컨텍스트]" not in result["answer"]
    assert "[질문 해석]" in result["context"]
    assert "[결론 요약]" in result["context"]
    assert "[정책 근거]" in result["context"]
    assert "[지식 그래프]" in result["context"]
    assert result["knowledge_graph"]["nodes"]
    assert result["knowledge_graph"]["edges"]


# 대출 규제 질문의 정책/뉴스 매칭 검증
def test_analyzes_loan_regulation_query(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")

    result = analyze_market_impact("DSR 대출 규제가 강남구 매매 시장에 어떤 영향을 줬어?")

    assert result["parsed_query"]["region"] == "강남구"
    assert result["parsed_query"]["policy_type"] == "loan_regulation"
    assert result["policies"][0]["policy_id"] == "policy_002"
    assert result["news"][0]["news_id"] == "news_007"
