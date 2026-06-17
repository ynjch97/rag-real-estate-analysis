import os
import re
from pathlib import Path
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from src.collectors.news_collector import fetch_naver_news_raw, has_naver_api_credentials, save_raw_news
from src.data.loaders import load_jsonl
from src.embeddings.vector_store import load_vector_store
from src.preprocessing.news_cleaner import normalize_naver_news_items, save_news
from src.retrieval.hybrid_search import rerank_hybrid_results


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NEWS_INDEX_DIR = PROJECT_ROOT / "data" / "indexes" / "news_faiss"
DEFAULT_NEWS_SOURCE = PROJECT_ROOT / "data" / "sample" / "news.jsonl"
DEFAULT_RAW_NEWS_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_PROCESSED_NEWS_DIR = PROJECT_ROOT / "data" / "processed"


# FAISS 인덱스 기반 관련 뉴스 검색
def retrieve_news_documents(
    parsed_query: dict[str, Any],
    query: str | None = None,
    index_dir: str | Path = DEFAULT_NEWS_INDEX_DIR,
    top_k: int = 5,
    embeddings: Embeddings | None = None,
    fallback_path: str | Path = DEFAULT_NEWS_SOURCE,
    use_faiss: bool = True,
    use_live_api: bool = True,
    use_hybrid: bool = True,
) -> list[dict[str, Any]]:
    if use_live_api and has_naver_api_credentials():
        try:
            live_news = _retrieve_news_documents_from_naver(parsed_query, query=query, top_k=top_k, use_hybrid=use_hybrid)
            if live_news:
                return live_news
        except Exception:
            pass

    if not use_faiss:
        return _retrieve_news_documents_from_sample(parsed_query, fallback_path, top_k, query=query, use_hybrid=use_hybrid)

    query_text = query or _build_news_query(parsed_query)
    embeddings = embeddings or _load_openai_embeddings()

    if embeddings is None:
        return _retrieve_news_documents_from_sample(parsed_query, fallback_path, top_k)

    vector_store = load_vector_store(index_dir, embeddings)
    documents_with_scores = _similarity_search_with_scores(vector_store, query_text, k=max(top_k * 4, top_k))
    news_items = [_document_to_news(document) for document, _ in documents_with_scores]
    vector_scores = _build_news_vector_scores(documents_with_scores)
    filtered_news = _filter_news_documents(news_items, parsed_query)
    candidates = filtered_news or news_items
    if use_hybrid:
        return rerank_hybrid_results(
            query=query_text,
            items=candidates,
            parsed_query=parsed_query,
            text_fields=("title", "summary", "content", "region_tags", "policy_tags", "market_signal"),
            id_field="news_id",
            top_k=top_k,
            vector_scores=vector_scores,
        )
    return candidates[:top_k]


# 네이버 뉴스 API 기반 관련 뉴스 검색
def _retrieve_news_documents_from_naver(
    parsed_query: dict[str, Any],
    query: str | None = None,
    top_k: int = 5,
    use_hybrid: bool = True,
) -> list[dict[str, Any]]:
    query_text = _build_naver_news_query(parsed_query, query)
    raw_news_items = fetch_naver_news_raw(query=query_text, display=min(max(top_k * 2, 10), 100), sort="date")
    news_items = normalize_naver_news_items(raw_news_items, parsed_query=parsed_query)
    filtered_news = _filter_live_news_documents(news_items, parsed_query)

    save_raw_news(_build_raw_news_path(query_text), raw_news_items)
    save_news(_build_processed_news_path(query_text), filtered_news or news_items)

    candidates = filtered_news or news_items
    if use_hybrid:
        return rerank_hybrid_results(
            query=query_text,
            items=candidates,
            parsed_query=parsed_query,
            text_fields=("title", "summary", "content", "region_tags", "policy_tags", "market_signal"),
            id_field="news_id",
            top_k=top_k,
        )
    return candidates[:top_k]


# 네이버 뉴스 검색어 생성
def _build_naver_news_query(parsed_query: dict[str, Any], query: str | None = None) -> str:
    values = [
        parsed_query.get("event_keyword"),
        parsed_query.get("region"),
        parsed_query.get("dong"),
        _to_korean_property_type(parsed_query.get("property_type")),
        _to_korean_transaction_type(parsed_query.get("transaction_type")),
    ]
    built_query = " ".join(str(value) for value in values if value)
    return built_query or query or _build_news_query(parsed_query)


# 질문 분석 결과 기반 뉴스 검색어 생성
def _build_news_query(parsed_query: dict[str, Any]) -> str:
    values = [
        parsed_query.get("region"),
        parsed_query.get("event_keyword"),
        parsed_query.get("policy_type"),
    ]
    return " ".join(str(value) for value in values if value)


# 네이버 원천 뉴스 저장 경로 생성
def _build_raw_news_path(query: str) -> Path:
    return DEFAULT_RAW_NEWS_DIR / f"naver_news_{_slugify_query(query)}.jsonl"


# 네이버 정규화 뉴스 저장 경로 생성
def _build_processed_news_path(query: str) -> Path:
    return DEFAULT_PROCESSED_NEWS_DIR / f"news_naver_{_slugify_query(query)}.jsonl"


# 검색어 파일명 변환
def _slugify_query(query: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", query).strip("_")
    return slug[:80] or "query"


# OpenAI 임베딩 객체 생성
def _load_openai_embeddings() -> OpenAIEmbeddings | None:
    _load_env()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "sk-proj-xxxxxxxx":
        return None
    return OpenAIEmbeddings(api_key=api_key)


# 루트 .env 환경변수 로드
def _load_env(env_path: Path = PROJECT_ROOT / ".env") -> None:
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# 샘플 뉴스 JSONL 기반 fallback 검색
def _retrieve_news_documents_from_sample(
    parsed_query: dict[str, Any],
    news_path: str | Path,
    top_k: int,
    query: str | None = None,
    use_hybrid: bool = True,
) -> list[dict[str, Any]]:
    news_items = load_jsonl(news_path)
    region = parsed_query.get("region")
    policy_type = parsed_query.get("policy_type")

    matched = [
        news
        for news in news_items
        if _matches_region_tag(news, region)
        and (policy_type is None or policy_type in news.get("policy_tags", []))
    ]
    if use_hybrid:
        return rerank_hybrid_results(
            query=query or _build_news_query(parsed_query),
            items=matched,
            parsed_query=parsed_query,
            text_fields=("title", "summary", "region_tags", "policy_tags", "market_signal"),
            id_field="news_id",
            top_k=top_k,
        )
    return matched[:top_k]


# 뉴스 검색 결과 메타데이터 필터링
def _filter_news_documents(
    news_items: list[dict[str, Any]],
    parsed_query: dict[str, Any],
) -> list[dict[str, Any]]:
    region = parsed_query.get("region")
    policy_type = parsed_query.get("policy_type")

    return [
        news
        for news in news_items
        if _matches_region_tag(news, region)
        and (policy_type is None or policy_type in news.get("policy_tags", []))
    ]


# 네이버 뉴스 검색 결과 필터링
def _filter_live_news_documents(
    news_items: list[dict[str, Any]],
    parsed_query: dict[str, Any],
) -> list[dict[str, Any]]:
    region = parsed_query.get("region")
    dong = parsed_query.get("dong")
    event_keyword = parsed_query.get("event_keyword")

    return [
        news
        for news in news_items
        if _contains_optional_keyword(news, region)
        and _contains_optional_keyword(news, dong)
        and _contains_optional_keyword(news, event_keyword)
    ]


# FAISS Document를 뉴스 dict로 변환
def _document_to_news(document: Document) -> dict[str, Any]:
    news = dict(document.metadata)
    news["content"] = document.page_content
    news.setdefault("summary", document.page_content)
    return news


# FAISS 유사도 검색과 점수 조회
def _similarity_search_with_scores(vector_store: Any, query: str, k: int) -> list[tuple[Document, float]]:
    if hasattr(vector_store, "similarity_search_with_relevance_scores"):
        try:
            return vector_store.similarity_search_with_relevance_scores(query, k=k)
        except Exception:
            pass
    if hasattr(vector_store, "similarity_search_with_score"):
        return [(document, _distance_to_similarity(score)) for document, score in vector_store.similarity_search_with_score(query, k=k)]
    return [(document, 1.0) for document in vector_store.similarity_search(query, k=k)]


# FAISS 거리 점수를 유사도 점수로 변환
def _distance_to_similarity(score: float) -> float:
    return 1 / (1 + float(score))


# 뉴스 문서 벡터 점수 dict 생성
def _build_news_vector_scores(documents_with_scores: list[tuple[Document, float]]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for document, score in documents_with_scores:
        news_id = document.metadata.get("news_id")
        if news_id is not None:
            scores[str(news_id)] = float(score)
    return scores


# 지역 태그 포함 여부 확인
def _matches_region_tag(item: dict[str, Any], region: str | None) -> bool:
    if region is None:
        return True
    return region in item.get("region_tags", [])


# 뉴스 텍스트에 선택 키워드 포함 여부 확인
def _contains_optional_keyword(news: dict[str, Any], keyword: str | None) -> bool:
    if keyword is None:
        return True
    text = f"{news.get('title', '')} {news.get('summary', '')}"
    return keyword in text


# 분석기 주거유형 값을 한국어 검색어로 변환
def _to_korean_property_type(property_type: str | None) -> str | None:
    mapping = {
        "apartment": "아파트",
        "officetel": "오피스텔",
        "villa": "빌라",
    }
    return mapping.get(property_type, property_type)


# 분석기 거래유형 값을 한국어 검색어로 변환
def _to_korean_transaction_type(transaction_type: str | None) -> str | None:
    mapping = {
        "sale": "매매",
        "jeonse": "전세",
        "monthly_rent": "월세",
    }
    return mapping.get(transaction_type, transaction_type)
