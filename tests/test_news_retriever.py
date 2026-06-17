from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding

from src.embeddings.vector_store import create_vector_store, save_vector_store
from src.retrieval.news_retriever import retrieve_news_documents


# FAISS 뉴스 인덱스 검색 검증
def test_retrieves_news_documents_from_faiss(tmp_path):
    embeddings = DeterministicFakeEmbedding(size=16)
    documents = [
        Document(
            page_content="성동구 금리 인상 이후 매수 문의 감소",
            metadata={
                "news_id": "news_test_001",
                "title": "성동구 매수 문의 감소",
                "published_date": "2024-02-10",
                "news_site": "sample",
                "region_tags": ["성동구"],
                "policy_tags": ["interest_rate"],
                "sentiment_score": -0.35,
                "market_signal": "거래 위축",
            },
        ),
        Document(
            page_content="강남구 대출 규제 이후 신고가 유지",
            metadata={
                "news_id": "news_test_002",
                "title": "강남구 신고가 유지",
                "published_date": "2024-04-20",
                "news_site": "sample",
                "region_tags": ["강남구"],
                "policy_tags": ["loan_regulation"],
                "sentiment_score": 0.15,
                "market_signal": "신고가",
            },
        ),
    ]
    index_dir = tmp_path / "news_faiss"
    save_vector_store(create_vector_store(documents, embeddings), index_dir)

    results = retrieve_news_documents(
        parsed_query={"region": "성동구", "event_keyword": "금리 인상", "policy_type": "interest_rate"},
        index_dir=index_dir,
        top_k=2,
        embeddings=embeddings,
        use_live_api=False,
    )

    assert len(results) == 1
    assert results[0]["news_id"] == "news_test_001"
    assert "content" in results[0]


# OpenAI 키가 없을 때 샘플 뉴스 fallback 검색 검증
def test_retrieves_news_documents_from_sample_fallback():
    results = retrieve_news_documents(
        parsed_query={"region": "성동구", "event_keyword": "금리 인상", "policy_type": "interest_rate"},
        top_k=1,
        embeddings=None,
        use_faiss=False,
        use_live_api=False,
    )

    assert [result["news_id"] for result in results] == ["news_001"]
    assert results[0]["hybrid_score"] > 0
