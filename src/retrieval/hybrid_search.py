import math
import re
from collections import Counter
from typing import Any


DEFAULT_HYBRID_WEIGHTS = {
    "bm25": 0.45,
    "vector": 0.35,
    "tag": 0.20,
}


# BM25, 벡터, 태그 점수 기반 검색 결과 재정렬
def rerank_hybrid_results(
    query: str,
    items: list[dict[str, Any]],
    parsed_query: dict[str, Any],
    text_fields: tuple[str, ...],
    id_field: str,
    top_k: int,
    vector_scores: dict[str, float] | None = None,
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    if not items:
        return []

    weights = weights or DEFAULT_HYBRID_WEIGHTS
    vector_scores = vector_scores or {}
    bm25_scores = calculate_bm25_scores(query, [_build_search_text(item, text_fields) for item in items])
    normalized_bm25_scores = _normalize_scores(bm25_scores)
    normalized_vector_scores = _normalize_mapping_scores(vector_scores)

    scored_items = []
    for index, item in enumerate(items):
        item_id = str(item.get(id_field, index))
        bm25_score = normalized_bm25_scores[index]
        vector_score = normalized_vector_scores.get(item_id, 0.0)
        tag_score = calculate_tag_score(item, parsed_query)
        hybrid_score = (
            weights.get("bm25", 0.0) * bm25_score
            + weights.get("vector", 0.0) * vector_score
            + weights.get("tag", 0.0) * tag_score
        )
        scored_item = dict(item)
        scored_item["hybrid_score"] = round(hybrid_score, 6)
        scored_item["bm25_score"] = round(bm25_score, 6)
        scored_item["vector_score"] = round(vector_score, 6)
        scored_item["tag_score"] = round(tag_score, 6)
        scored_items.append(scored_item)

    return sorted(scored_items, key=lambda item: item["hybrid_score"], reverse=True)[:top_k]


# BM25 키워드 점수 계산
def calculate_bm25_scores(query: str, documents: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    query_terms = tokenize(query)
    document_terms = [tokenize(document) for document in documents]
    document_count = len(document_terms)
    average_length = _safe_average([len(terms) for terms in document_terms])
    document_frequency = _calculate_document_frequency(document_terms)

    scores: list[float] = []
    for terms in document_terms:
        term_counts = Counter(terms)
        score = 0.0

        for term in query_terms:
            if term not in term_counts:
                continue

            idf = math.log(1 + (document_count - document_frequency.get(term, 0) + 0.5) / (document_frequency.get(term, 0) + 0.5))
            frequency = term_counts[term]
            denominator = frequency + k1 * (1 - b + b * (len(terms) / average_length))
            score += idf * ((frequency * (k1 + 1)) / denominator)

        scores.append(score)

    return scores


# 질문 분석 결과와 문서 태그 일치 점수 계산
def calculate_tag_score(item: dict[str, Any], parsed_query: dict[str, Any]) -> float:
    scores = []

    if parsed_query.get("region"):
        scores.append(_tag_specificity_score(item.get("region_tags", []), parsed_query.get("region")))
    if parsed_query.get("dong"):
        scores.append(_tag_specificity_score(item.get("region_tags", []), parsed_query.get("dong")))
    if parsed_query.get("policy_type"):
        scores.append(
            max(
                _tag_specificity_score(item.get("policy_tags", []), parsed_query.get("policy_type")),
                1.0 if item.get("policy_type") == parsed_query.get("policy_type") else 0.0,
            )
        )
    if parsed_query.get("event_keyword"):
        scores.append(1.0 if _contains_keyword(item.get("keywords", []), parsed_query.get("event_keyword")) else 0.0)

    if not scores:
        return 0.0
    return min(sum(scores) / len(scores), 1.0)


# 검색 텍스트 토큰화
def tokenize(text: str) -> list[str]:
    return re.findall(r"[0-9A-Za-z가-힣]+", text.lower())


# 검색 대상 필드 문자열 결합
def _build_search_text(item: dict[str, Any], text_fields: tuple[str, ...]) -> str:
    values: list[str] = []
    for field in text_fields:
        value = item.get(field)
        if value is None:
            continue
        if isinstance(value, list):
            values.extend(str(part) for part in value)
        else:
            values.append(str(value))
    return " ".join(values)


# 문서 빈도 계산
def _calculate_document_frequency(document_terms: list[list[str]]) -> dict[str, int]:
    frequency: dict[str, int] = {}
    for terms in document_terms:
        for term in set(terms):
            frequency[term] = frequency.get(term, 0) + 1
    return frequency


# 점수 목록 0~1 정규화
def _normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []

    max_score = max(scores)
    min_score = min(scores)
    if max_score == min_score:
        return [1.0 if max_score > 0 else 0.0 for _ in scores]

    return [(score - min_score) / (max_score - min_score) for score in scores]


# 점수 dict 0~1 정규화
def _normalize_mapping_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}

    keys = list(scores.keys())
    normalized_values = _normalize_scores([scores[key] for key in keys])
    return dict(zip(keys, normalized_values))


# 평균값 안전 계산
def _safe_average(values: list[int]) -> float:
    if not values:
        return 1.0
    average = sum(values) / len(values)
    return average if average > 0 else 1.0


# 태그 목록에서 대상 태그의 구체성 점수 계산
def _tag_specificity_score(tags: Any, target: str | None) -> float:
    if target is None:
        return 0.0
    if not isinstance(tags, list):
        return 0.0
    if target in tags:
        return 1 / max(len(tags), 1)
    if "전국" in tags:
        return 0.25
    return 0.0


# 키워드 목록에 대상 키워드 포함 여부 확인
def _contains_keyword(keywords: Any, keyword: str | None) -> bool:
    if keyword is None or not isinstance(keywords, list):
        return False
    return any(keyword in str(value) or str(value) in keyword for value in keywords)
