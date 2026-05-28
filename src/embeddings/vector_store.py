from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings


def create_vector_store(documents: list[Document], embeddings: OpenAIEmbeddings) -> FAISS:
    if not documents:
        raise ValueError("Cannot create a FAISS index with no documents.")

    return FAISS.from_documents(documents, embeddings)


def save_vector_store(vector_store: FAISS, index_dir: str | Path) -> None:
    path = Path(index_dir)
    path.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(path))


def load_vector_store(index_dir: str | Path, embeddings: OpenAIEmbeddings) -> FAISS:
    return FAISS.load_local(
        str(index_dir),
        embeddings,
        allow_dangerous_deserialization=True,
    )
