from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding

from src.embeddings.vector_store import create_vector_store, save_vector_store
from src.retrieval.policy_retriever import _build_korea_policy_news_search_keyword, retrieve_policy_documents


# FAISS 정책 인덱스 검색 검증
def test_retrieves_policy_documents_from_faiss(tmp_path):
    embeddings = DeterministicFakeEmbedding(size=16)
    documents = [
        Document(
            page_content="금리 인상 주택담보대출 부담 증가",
            metadata={
                "policy_id": "policy_test_001",
                "title": "기준금리 인상",
                "published_date": "2024-01-15",
                "effective_date": "2024-01-15",
                "policy_type": "interest_rate",
                "region_tags": ["성동구"],
                "keywords": ["금리"],
            },
        ),
        Document(
            page_content="대출 규제 DSR 강화",
            metadata={
                "policy_id": "policy_test_002",
                "title": "DSR 규제 강화",
                "published_date": "2024-03-01",
                "effective_date": "2024-04-01",
                "policy_type": "loan_regulation",
                "region_tags": ["강남구"],
                "keywords": ["DSR"],
            },
        ),
    ]
    index_dir = tmp_path / "policy_faiss"
    save_vector_store(create_vector_store(documents, embeddings), index_dir)

    results = retrieve_policy_documents(
        parsed_query={"region": "성동구", "event_keyword": "금리 인상", "policy_type": "interest_rate"},
        index_dir=index_dir,
        top_k=2,
        embeddings=embeddings,
        use_live_api=False,
    )

    assert len(results) == 1
    assert results[0]["policy_id"] == "policy_test_001"
    assert "content" in results[0]


# OpenAI 키가 없을 때 샘플 정책 fallback 검색 검증
def test_retrieves_policy_documents_from_sample_fallback():
    results = retrieve_policy_documents(
        parsed_query={"region": "성동구", "event_keyword": "금리 인상", "policy_type": "interest_rate"},
        top_k=1,
        embeddings=None,
        use_faiss=False,
        use_live_api=False,
    )

    assert [result["policy_id"] for result in results] == ["policy_001"]


# 정책브리핑 정책뉴스 검색어 생성 검증
def test_builds_korea_policy_news_search_keyword():
    keyword = _build_korea_policy_news_search_keyword(
        {
            "region": "강서구",
            "dong": None,
            "event_keyword": "대출 규제",
            "policy_type": "loan_regulation",
        }
    )

    assert keyword == "대출 규제 강서구"


# 정책 이벤트 없는 지역 질문 검색어 생성 검증
def test_builds_korea_policy_news_search_keyword_with_real_estate_fallback():
    keyword = _build_korea_policy_news_search_keyword(
        {
            "region": "강남구",
            "dong": None,
            "event_keyword": None,
            "policy_type": None,
        }
    )

    assert keyword == "강남구 부동산"
