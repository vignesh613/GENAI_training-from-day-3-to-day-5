import os
import chromadb
from utils.logger import get_logger

logger = get_logger(__name__)

_collection = None


def get_collection():
    global _collection
    if _collection is None:
        persist_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "chroma_data")
        )
        os.makedirs(persist_dir, exist_ok=True)
        client = chromadb.PersistentClient(path=persist_dir)
        _collection = client.get_or_create_collection(
            name="research_docs",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"ChromaDB ready at {persist_dir}. Documents: {_collection.count()}"
        )
    return _collection


def store_document(doc_id: str, content: str, metadata: dict, embedding: list):
    collection = get_collection()
    collection.upsert(
        ids=[doc_id],
        documents=[content],
        metadatas=[metadata],
        embeddings=[embedding],
    )
    logger.info(f"Stored document {doc_id[:8]}... in ChromaDB")


def query_documents(query_embedding: list, n_results: int = 3) -> list:
    collection = get_collection()
    count = collection.count()
    if count == 0:
        logger.info("ChromaDB is empty — no prior context retrieved")
        return []
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, count),
    )
    docs = results.get("documents", [[]])[0]
    logger.info(f"Retrieved {len(docs)} documents from ChromaDB")
    return docs
