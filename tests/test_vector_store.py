from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding

from src.embeddings.vector_store import create_vector_store, load_vector_store, save_vector_store


# FAISS 인덱스 코사인 유사도 설정 검증
def test_creates_vector_store_with_cosine_similarity():
    vector_store = create_vector_store(
        [Document(page_content="성동구 금리 인상")],
        DeterministicFakeEmbedding(size=16),
    )

    assert vector_store.distance_strategy == DistanceStrategy.COSINE


# FAISS 인덱스 코사인 유사도 설정 저장/로드 검증
def test_loads_vector_store_with_cosine_similarity(tmp_path):
    embeddings = DeterministicFakeEmbedding(size=16)
    index_dir = tmp_path / "faiss"
    vector_store = create_vector_store([Document(page_content="성동구 금리 인상")], embeddings)
    save_vector_store(vector_store, index_dir)

    loaded_store = load_vector_store(index_dir, embeddings)

    assert loaded_store.distance_strategy == DistanceStrategy.COSINE
