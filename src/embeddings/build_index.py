import argparse
import os
from pathlib import Path

from langchain_openai import OpenAIEmbeddings

from src.data.loaders import load_news_documents, load_policy_documents
from src.embeddings.vector_store import create_vector_store, save_vector_store


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_SOURCE = PROJECT_ROOT / "data" / "sample" / "policies.jsonl"
NEWS_SOURCE = PROJECT_ROOT / "data" / "sample" / "news.jsonl"
POLICY_INDEX_DIR = PROJECT_ROOT / "data" / "indexes" / "policy_faiss"
NEWS_INDEX_DIR = PROJECT_ROOT / "data" / "indexes" / "news_faiss"


def load_env(env_path: Path = PROJECT_ROOT / ".env") -> None:
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def build_indexes(dry_run: bool = False) -> None:
    policy_documents = load_policy_documents(POLICY_SOURCE)
    news_documents = load_news_documents(NEWS_SOURCE)

    print(f"💾 Policy documents: {len(policy_documents)}")
    print(f"💾 News documents: {len(news_documents)}")

    if dry_run:
        print("Dry run only. FAISS indexes were not created.")
        return

    load_env()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "sk-proj-xxxxxxxx":
        raise ValueError("Set a real OPENAI_API_KEY in .env before building FAISS indexes.")

    embeddings = OpenAIEmbeddings(api_key=api_key)

    policy_store = create_vector_store(policy_documents, embeddings)
    save_vector_store(policy_store, POLICY_INDEX_DIR)

    news_store = create_vector_store(news_documents, embeddings)
    save_vector_store(news_store, NEWS_INDEX_DIR)

    print(f"💾 Policy FAISS index saved to: {POLICY_INDEX_DIR}")
    print(f"💾 News FAISS index saved to: {NEWS_INDEX_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build separate FAISS indexes for sample policy and news data.")
    parser.add_argument("--dry-run", action="store_true", help="Load documents and print counts without OpenAI calls.")
    args = parser.parse_args()

    build_indexes(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
