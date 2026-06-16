import os
from pathlib import Path
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from src.data.loaders import load_jsonl
from src.embeddings.vector_store import load_vector_store


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_INDEX_DIR = PROJECT_ROOT / "data" / "indexes" / "policy_faiss"
DEFAULT_POLICY_SOURCE = PROJECT_ROOT / "data" / "sample" / "policies.jsonl"


# FAISS 인덱스 기반 관련 정책 검색
def retrieve_policy_documents(
    parsed_query: dict[str, Any],
    query: str | None = None,
    index_dir: str | Path = DEFAULT_POLICY_INDEX_DIR,
    top_k: int = 3,
    embeddings: Embeddings | None = None,
    fallback_path: str | Path = DEFAULT_POLICY_SOURCE,
    use_faiss: bool = True,
) -> list[dict[str, Any]]:
    if not use_faiss:
        return _retrieve_policy_documents_from_sample(parsed_query, fallback_path, top_k)

    query_text = query or _build_policy_query(parsed_query)
    embeddings = embeddings or _load_openai_embeddings()

    if embeddings is None:
        return _retrieve_policy_documents_from_sample(parsed_query, fallback_path, top_k)

    vector_store = load_vector_store(index_dir, embeddings)
    documents = vector_store.similarity_search(query_text, k=max(top_k * 4, top_k))
    policies = [_document_to_policy(document) for document in documents]
    filtered_policies = _filter_policy_documents(policies, parsed_query)
    return (filtered_policies or policies)[:top_k]


# 질문 분석 결과 기반 정책 검색어 생성
def _build_policy_query(parsed_query: dict[str, Any]) -> str:
    values = [
        parsed_query.get("region"),
        parsed_query.get("event_keyword"),
        parsed_query.get("policy_type"),
    ]
    return " ".join(str(value) for value in values if value)


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


# 샘플 정책 JSONL 기반 fallback 검색
def _retrieve_policy_documents_from_sample(
    parsed_query: dict[str, Any],
    policy_path: str | Path,
    top_k: int,
) -> list[dict[str, Any]]:
    policies = load_jsonl(policy_path)
    region = parsed_query.get("region")
    policy_type = parsed_query.get("policy_type")
    event_keyword = parsed_query.get("event_keyword")

    matched = [
        policy
        for policy in policies
        if _matches_region_tag(policy, region)
        and (
            policy_type is None
            or policy.get("policy_type") == policy_type
            or _contains_keyword(policy.get("keywords", []), event_keyword)
        )
    ]
    return matched[:top_k]


# 정책 검색 결과 메타데이터 필터링
def _filter_policy_documents(
    policies: list[dict[str, Any]],
    parsed_query: dict[str, Any],
) -> list[dict[str, Any]]:
    region = parsed_query.get("region")
    policy_type = parsed_query.get("policy_type")
    event_keyword = parsed_query.get("event_keyword")

    return [
        policy
        for policy in policies
        if _matches_region_tag(policy, region)
        and (
            policy_type is None
            or policy.get("policy_type") == policy_type
            or _contains_keyword(policy.get("keywords", []), event_keyword)
        )
    ]


# FAISS Document를 정책 dict로 변환
def _document_to_policy(document: Document) -> dict[str, Any]:
    policy = dict(document.metadata)
    policy["content"] = document.page_content
    policy.setdefault("summary", document.page_content)
    return policy


# 지역 태그 포함 여부 확인
def _matches_region_tag(item: dict[str, Any], region: str | None) -> bool:
    if region is None:
        return True
    return region in item.get("region_tags", [])


# 키워드 포함 여부 확인
def _contains_keyword(keywords: list[str], keyword: str | None) -> bool:
    if keyword is None:
        return False
    return any(keyword in value or value in keyword for value in keywords)
