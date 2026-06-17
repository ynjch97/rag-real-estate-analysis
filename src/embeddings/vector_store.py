from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


# 문서 임베딩을 코사인 유사도 기반 FAISS 인덱스로 생성
def create_vector_store(documents: list[Document], embeddings: Embeddings) -> FAISS:
    if not documents:
        raise ValueError("Cannot create a FAISS index with no documents.")

    return FAISS.from_documents(
        documents,
        embeddings,
        distance_strategy=DistanceStrategy.COSINE,
        normalize_L2=True,
    )


# FAISS 인덱스 로컬 저장
def save_vector_store(vector_store: FAISS, index_dir: str | Path) -> None:
    path = Path(index_dir)
    path.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(path))


# FAISS 인덱스 로컬 로드
def load_vector_store(index_dir: str | Path, embeddings: Embeddings) -> FAISS:
    return FAISS.load_local(
        str(index_dir),
        embeddings,
        allow_dangerous_deserialization=True,
        distance_strategy=DistanceStrategy.COSINE,
        normalize_L2=True,
    )
