from src.retrieval.hybrid_search import calculate_bm25_scores, calculate_tag_score, rerank_hybrid_results


# BM25 키워드 일치 점수 검증
def test_calculates_bm25_scores_for_keyword_match():
    scores = calculate_bm25_scores(
        query="금리 인상 동작구",
        documents=[
            "금리 인상 이후 동작구 아파트 매수세 둔화",
            "공급 정책과 강남구 재건축",
        ],
    )

    assert scores[0] > scores[1]


# 지역과 정책 태그 일치 점수 검증
def test_calculates_tag_score():
    item = {
        "region_tags": ["동작구"],
        "policy_tags": ["interest_rate"],
        "keywords": ["금리"],
    }
    parsed_query = {
        "region": "동작구",
        "policy_type": "interest_rate",
        "event_keyword": "금리 인상",
    }

    assert calculate_tag_score(item, parsed_query) > 0


# BM25, 벡터, 태그 점수 기반 재정렬 검증
def test_reranks_hybrid_results():
    items = [
        {
            "news_id": "news_001",
            "title": "강남구 공급 정책",
            "summary": "재건축 공급 확대",
            "region_tags": ["강남구"],
            "policy_tags": ["supply_policy"],
        },
        {
            "news_id": "news_002",
            "title": "금리 인상 이후 동작구 아파트 매매 둔화",
            "summary": "동작구 매수세가 줄었다",
            "region_tags": ["동작구"],
            "policy_tags": ["interest_rate"],
        },
    ]
    parsed_query = {
        "region": "동작구",
        "policy_type": "interest_rate",
        "event_keyword": "금리 인상",
    }

    results = rerank_hybrid_results(
        query="금리 인상 동작구 아파트 매매",
        items=items,
        parsed_query=parsed_query,
        text_fields=("title", "summary", "region_tags", "policy_tags"),
        id_field="news_id",
        top_k=2,
        vector_scores={"news_001": 0.9, "news_002": 0.4},
    )

    assert results[0]["news_id"] == "news_002"
    assert "hybrid_score" in results[0]
    assert "bm25_score" in results[0]
    assert "vector_score" in results[0]
    assert "tag_score" in results[0]
