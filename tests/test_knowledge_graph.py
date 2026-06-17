from src.analysis.knowledge_graph import (
    build_market_knowledge_graph,
    format_knowledge_graph_context,
    rank_news_by_graph,
    rank_policies_by_graph,
)


# 정책, 뉴스, 시세 지식 그래프 생성 검증
def test_builds_market_knowledge_graph():
    graph = build_market_knowledge_graph(
        parsed_query={
            "region": "성동구",
            "event_keyword": "금리 인상",
            "policy_type": "interest_rate",
        },
        policies=[
            {
                "policy_id": "policy_001",
                "title": "기준금리 인상",
                "summary": "주택담보대출 부담 증가",
                "keywords": ["금리", "대출"],
                "region_tags": ["전국"],
            }
        ],
        news_items=[
            {
                "news_id": "news_001",
                "title": "성동구 매수 문의 감소",
                "summary": "금리 인상 이후 거래 위축",
                "policy_tags": ["interest_rate"],
                "region_tags": ["성동구"],
                "market_signal": "거래 위축",
            }
        ],
        market_summary={
            "region": "성동구",
            "policy_month": "2024-01",
            "price_change_rate": -3.57,
        },
    )

    node_ids = {node.node_id for node in graph.nodes}
    relation_types = {edge.relation_type for edge in graph.edges}

    assert {"query", "market_summary", "policy_001", "news_001"} <= node_ids
    assert "query_matches_policy" in relation_types
    assert "policy_explained_by_news" in relation_types
    assert "news_reflects_market" in relation_types


# 지식 그래프 컨텍스트 문자열 생성 검증
def test_formats_knowledge_graph_context():
    graph = build_market_knowledge_graph(
        parsed_query={"region": "성동구"},
        policies=[],
        news_items=[],
        market_summary={"region": "성동구"},
    )

    context = format_knowledge_graph_context(graph)

    assert "[지식 그래프 노드]" in context
    assert "[지식 그래프 관계]" in context
    assert "[그래프 기반 정렬 순서]" in context


# 지식 그래프 기반 정책과 뉴스 정렬 검증
def test_ranks_policies_and_news_by_graph():
    policies = [
        {"policy_id": "policy_low", "title": "일반 정책", "keywords": ["세제"], "region_tags": ["전국"]},
        {"policy_id": "policy_high", "title": "성동구 금리 정책", "keywords": ["금리"], "region_tags": ["성동구"]},
    ]
    news_items = [
        {"news_id": "news_low", "title": "일반 뉴스", "summary": "시장 동향", "region_tags": ["서울"]},
        {"news_id": "news_high", "title": "성동구 금리 인상 영향", "summary": "거래 위축", "region_tags": ["성동구"]},
    ]
    graph = build_market_knowledge_graph(
        parsed_query={"region": "성동구", "event_keyword": "금리 인상", "policy_type": "interest_rate"},
        policies=policies,
        news_items=news_items,
        market_summary={"region": "성동구"},
    )

    ranked_policies = rank_policies_by_graph(graph, policies)
    ranked_news = rank_news_by_graph(graph, news_items)

    assert ranked_policies[0]["policy_id"] == "policy_high"
    assert ranked_news[0]["news_id"] == "news_high"
