from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class KnowledgeNode:
    node_id: str
    node_type: str
    label: str
    properties: dict[str, Any]

    # KnowledgeNode를 dict로 변환
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeEdge:
    source_id: str
    target_id: str
    relation_type: str
    weight: float
    evidence: str

    # KnowledgeEdge를 dict로 변환
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeGraph:
    nodes: list[KnowledgeNode]
    edges: list[KnowledgeEdge]

    # KnowledgeGraph를 dict로 변환
    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


# 정책, 뉴스, 시세 기반 지식 그래프 생성
def build_market_knowledge_graph(
    parsed_query: dict[str, Any],
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
) -> KnowledgeGraph:
    nodes = _build_nodes(parsed_query, policies, news_items, market_summary)
    edges = _build_edges(parsed_query, policies, news_items, market_summary)
    return KnowledgeGraph(nodes=nodes, edges=edges)


# 지식 그래프를 LLM 컨텍스트 문자열로 변환
def format_knowledge_graph_context(graph: KnowledgeGraph) -> str:
    return "\n".join(
        [
            "[지식 그래프 노드]",
            _format_nodes(graph.nodes),
            "[지식 그래프 관계]",
            _format_edges(graph.edges),
            "[그래프 기반 정렬 순서]",
            _format_ranked_nodes(graph),
        ]
    )


# 그래프 기반 관련 정책 정렬
def rank_policies_by_graph(graph: KnowledgeGraph, policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    policy_weights = _build_target_weight_map(graph, "policy")
    return sorted(
        policies,
        key=lambda policy: policy_weights.get(str(policy.get("policy_id")), 0),
        reverse=True,
    )


# 그래프 기반 관련 뉴스 정렬
def rank_news_by_graph(graph: KnowledgeGraph, news_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    news_weights = _build_target_weight_map(graph, "news")
    return sorted(
        news_items,
        key=lambda news: news_weights.get(str(news.get("news_id")), 0),
        reverse=True,
    )


# 지식 그래프 노드 생성
def _build_nodes(
    parsed_query: dict[str, Any],
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
) -> list[KnowledgeNode]:
    nodes = [
        KnowledgeNode(
            node_id="query",
            node_type="query",
            label="사용자 질문",
            properties=parsed_query,
        ),
        KnowledgeNode(
            node_id="market_summary",
            node_type="market",
            label=_build_market_label(market_summary),
            properties=market_summary,
        ),
    ]
    nodes.extend(_build_policy_nodes(policies))
    nodes.extend(_build_news_nodes(news_items))
    return nodes


# 정책 노드 생성
def _build_policy_nodes(policies: list[dict[str, Any]]) -> list[KnowledgeNode]:
    return [
        KnowledgeNode(
            node_id=str(policy.get("policy_id")),
            node_type="policy",
            label=str(policy.get("title") or policy.get("policy_id")),
            properties=policy,
        )
        for policy in policies
    ]


# 뉴스 노드 생성
def _build_news_nodes(news_items: list[dict[str, Any]]) -> list[KnowledgeNode]:
    return [
        KnowledgeNode(
            node_id=str(news.get("news_id")),
            node_type="news",
            label=str(news.get("title") or news.get("news_id")),
            properties=news,
        )
        for news in news_items
    ]


# 지식 그래프 관계 생성
def _build_edges(
    parsed_query: dict[str, Any],
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
) -> list[KnowledgeEdge]:
    edges = []
    edges.extend(_build_query_edges(parsed_query, policies, news_items, market_summary))
    edges.extend(_build_policy_news_edges(policies, news_items))
    edges.extend(_build_news_market_edges(news_items, market_summary))
    edges.extend(_build_policy_market_edges(policies, market_summary))
    return edges


# 질문과 검색 결과 관계 생성
def _build_query_edges(
    parsed_query: dict[str, Any],
    policies: list[dict[str, Any]],
    news_items: list[dict[str, Any]],
    market_summary: dict[str, Any],
) -> list[KnowledgeEdge]:
    edges = []
    for policy in policies:
        edges.append(
            KnowledgeEdge(
                source_id="query",
                target_id=str(policy.get("policy_id")),
                relation_type="query_matches_policy",
                weight=_score_item_match(parsed_query, policy, ("title", "summary", "keywords", "region_tags")),
                evidence="질문 키워드와 정책 메타데이터 일치",
            )
        )
    for news in news_items:
        edges.append(
            KnowledgeEdge(
                source_id="query",
                target_id=str(news.get("news_id")),
                relation_type="query_matches_news",
                weight=_score_item_match(parsed_query, news, ("title", "summary", "region_tags", "policy_tags")),
                evidence="질문 키워드와 뉴스 메타데이터 일치",
            )
        )
    if market_summary:
        edges.append(
            KnowledgeEdge(
                source_id="query",
                target_id="market_summary",
                relation_type="query_targets_market",
                weight=1.0,
                evidence="질문 지역과 시세 요약 연결",
            )
        )
    return edges


# 정책과 뉴스 관계 생성
def _build_policy_news_edges(policies: list[dict[str, Any]], news_items: list[dict[str, Any]]) -> list[KnowledgeEdge]:
    edges = []
    for policy in policies:
        for news in news_items:
            weight = _score_policy_news_match(policy, news)
            if weight <= 0:
                continue
            edges.append(
                KnowledgeEdge(
                    source_id=str(policy.get("policy_id")),
                    target_id=str(news.get("news_id")),
                    relation_type="policy_explained_by_news",
                    weight=weight,
                    evidence="정책 키워드와 뉴스 정책 태그/본문 일치",
                )
            )
    return edges


# 뉴스와 시세 관계 생성
def _build_news_market_edges(news_items: list[dict[str, Any]], market_summary: dict[str, Any]) -> list[KnowledgeEdge]:
    if not market_summary:
        return []

    return [
        KnowledgeEdge(
            source_id=str(news.get("news_id")),
            target_id="market_summary",
            relation_type="news_reflects_market",
            weight=_score_market_match(news, market_summary),
            evidence="뉴스 지역/시장신호와 시세 요약 연결",
        )
        for news in news_items
    ]


# 정책과 시세 관계 생성
def _build_policy_market_edges(policies: list[dict[str, Any]], market_summary: dict[str, Any]) -> list[KnowledgeEdge]:
    if not market_summary:
        return []

    return [
        KnowledgeEdge(
            source_id=str(policy.get("policy_id")),
            target_id="market_summary",
            relation_type="policy_related_to_market",
            weight=_score_market_match(policy, market_summary),
            evidence="정책 지역/유형과 시세 요약 연결",
        )
        for policy in policies
    ]


# 질문과 항목 일치 점수 계산
def _score_item_match(parsed_query: dict[str, Any], item: dict[str, Any], fields: tuple[str, ...]) -> float:
    query_terms = _extract_query_terms(parsed_query)
    item_text = _join_item_fields(item, fields)
    if not query_terms:
        return 0.5

    matches = sum(1 for term in query_terms if term and term in item_text)
    return round(min(1.0, 0.3 + matches / max(len(query_terms), 1)), 3)


# 정책과 뉴스 일치 점수 계산
def _score_policy_news_match(policy: dict[str, Any], news: dict[str, Any]) -> float:
    policy_terms = set(str(value) for value in policy.get("keywords", []) if value)
    news_text = _join_item_fields(news, ("title", "summary", "content", "policy_tags", "region_tags"))
    if not policy_terms:
        return 0.0

    matches = sum(1 for term in policy_terms if term in news_text)
    return round(min(1.0, matches / len(policy_terms)), 3)


# 시세 요약 일치 점수 계산
def _score_market_match(item: dict[str, Any], market_summary: dict[str, Any]) -> float:
    region = market_summary.get("region")
    dong = market_summary.get("dong")
    item_text = _join_item_fields(item, ("title", "summary", "content", "region_tags", "keywords"))
    score = 0.3
    if region and str(region) in item_text:
        score += 0.5
    if dong and str(dong) in item_text:
        score += 0.2
    return round(min(1.0, score), 3)


# 그래프 타겟 노드 가중치 합산
def _build_target_weight_map(graph: KnowledgeGraph, node_type: str) -> dict[str, float]:
    node_ids = {node.node_id for node in graph.nodes if node.node_type == node_type}
    weights = {node_id: 0.0 for node_id in node_ids}
    for edge in graph.edges:
        if edge.target_id in weights:
            weights[edge.target_id] += edge.weight
        if edge.source_id in weights:
            weights[edge.source_id] += edge.weight * 0.5
    return weights


# 질문 분석 결과에서 검색어 추출
def _extract_query_terms(parsed_query: dict[str, Any]) -> list[str]:
    return [
        str(value)
        for value in (
            parsed_query.get("region"),
            parsed_query.get("dong"),
            parsed_query.get("event_keyword"),
            parsed_query.get("policy_type"),
        )
        if value
    ]


# 항목 필드 문자열 병합
def _join_item_fields(item: dict[str, Any], fields: tuple[str, ...]) -> str:
    values = []
    for field in fields:
        value = item.get(field)
        if isinstance(value, list):
            values.extend(str(entry) for entry in value)
        elif value is not None:
            values.append(str(value))
    return " ".join(values)


# 시세 노드 라벨 생성
def _build_market_label(market_summary: dict[str, Any]) -> str:
    region = market_summary.get("region") or "지역 미확인"
    price_change_rate = market_summary.get("price_change_rate")
    if price_change_rate is None:
        return f"{region} 시세 변화"
    return f"{region} 시세 변화율 {price_change_rate}%"


# 지식 그래프 노드 문자열 생성
def _format_nodes(nodes: list[KnowledgeNode]) -> str:
    if not nodes:
        return "- 노드 없음"
    return "\n".join(f"- {node.node_id} ({node.node_type}): {node.label}" for node in nodes)


# 지식 그래프 관계 문자열 생성
def _format_edges(edges: list[KnowledgeEdge]) -> str:
    if not edges:
        return "- 관계 없음"
    return "\n".join(
        f"- {edge.source_id} -> {edge.target_id} ({edge.relation_type}, weight={edge.weight}): {edge.evidence}"
        for edge in edges
    )


# 그래프 기반 정렬 순서 문자열 생성
def _format_ranked_nodes(graph: KnowledgeGraph) -> str:
    weights = _build_rank_weight_map(graph)
    ranked_nodes = sorted(
        [node for node in graph.nodes if node.node_type in {"policy", "news", "market"}],
        key=lambda node: weights.get(node.node_id, 0),
        reverse=True,
    )
    if not ranked_nodes:
        return "- 정렬 대상 없음"
    return "\n".join(f"- {node.node_type}: {node.label}" for node in ranked_nodes)


# 그래프 노드 가중치 합산
def _build_rank_weight_map(graph: KnowledgeGraph) -> dict[str, float]:
    weights = {node.node_id: 0.0 for node in graph.nodes}
    for edge in graph.edges:
        weights[edge.source_id] = weights.get(edge.source_id, 0.0) + edge.weight * 0.5
        weights[edge.target_id] = weights.get(edge.target_id, 0.0) + edge.weight
    return weights
