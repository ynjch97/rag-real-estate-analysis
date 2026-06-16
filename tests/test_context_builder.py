from src.analysis.context_builder import build_market_impact_context


# 컨텍스트가 README 7-3 주요 섹션 포함 검증
def test_builds_context_with_readme_sections():
    context = build_market_impact_context(
        parsed_query={
            "region": "성동구",
            "event_keyword": "금리 인상",
            "policy_type": "interest_rate",
            "intent": "policy_impact",
            "transaction_type": "sale",
            "months_before": 6,
            "months_after": 6,
        },
        policies=[
            {
                "policy_id": "policy_001",
                "title": "기준금리 인상",
                "published_date": "2024-01-15",
                "summary": "대출 이자 부담 증가",
                "url": "sample://policy/policy_001",
            }
        ],
        news_items=[
            {
                "news_id": "news_001",
                "title": "성동구 매수 문의 감소",
                "published_date": "2024-02-10",
                "market_signal": "거래 위축",
                "summary": "매수 문의 감소",
                "url": "sample://news/news_001",
            }
        ],
        market_summary={
            "region": "성동구",
            "policy_month": "2024-01",
            "before_avg_price": 1400000000,
            "after_avg_price": 1350000000,
            "price_change_rate": -3.57,
            "before_avg_transaction_count": 2,
            "after_avg_transaction_count": 1,
            "transaction_count_change_rate": -50.0,
        },
    )

    assert "[질문 해석]" in context
    assert "[결론 요약]" in context
    assert "[정책 근거]" in context
    assert "[관련 뉴스 요약]" in context
    assert "[시세 변화 데이터]" in context
    assert "- 지역/기간: 성동구 / 전 6개월, 후 6개월" in context
    assert "평균 매매가 변화율" in context
    assert "제공된 정보에 없는 내용은 추측하지 않는다." in context


# 관련 자료가 없는 컨텍스트 기본값 검증
def test_builds_context_without_sources():
    context = build_market_impact_context(
        parsed_query={},
        policies=[],
        news_items=[],
        market_summary={},
    )

    assert "관련 정책 없음" in context
    assert "관련 뉴스 없음" in context
    assert "참고 출처 없음" in context
