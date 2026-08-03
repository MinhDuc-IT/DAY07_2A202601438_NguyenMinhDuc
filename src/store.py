from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        try:
            import chromadb

            client = chromadb.Client()
            self._collection = client.get_or_create_collection(name=collection_name)
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document, embedding: list[float] | None = None) -> dict[str, Any]:
        metadata = dict(doc.metadata or {})
        metadata.setdefault("doc_id", doc.id)
        record_id = f"{doc.id}_{self._next_index}"
        self._next_index += 1
        return {
            "id": record_id,
            "doc_id": doc.id,
            "content": doc.content,
            "metadata": metadata,
            "embedding": embedding if embedding is not None else self._embedding_fn(doc.content),
        }

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        embed_batch = getattr(self._embedding_fn, "embed_batch", None)
        if callable(embed_batch):
            return embed_batch(texts)
        return [self._embedding_fn(text) for text in texts]

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if not records or top_k <= 0:
            return []

        query_embedding = self._embedding_fn(query)
        scored: list[dict[str, Any]] = []
        for record in records:
            score = float(_dot(query_embedding, record["embedding"]))
            scored.append(
                {
                    "id": record.get("id"),
                    "content": record["content"],
                    "score": score,
                    "metadata": dict(record.get("metadata") or {}),
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        if not docs:
            return

        embeddings = self._embed_texts([doc.content for doc in docs])
        for doc, embedding in zip(docs, embeddings):
            record = self._make_record(doc, embedding=embedding)
            self._store.append(record)

            if self._use_chroma and self._collection is not None:
                chroma_metadata = {
                    key: value
                    for key, value in record["metadata"].items()
                    if isinstance(value, (str, int, float, bool))
                } or {"doc_id": record["doc_id"]}
                self._collection.add(
                    ids=[record["id"]],
                    documents=[record["content"]],
                    embeddings=[record["embedding"]],
                    metadatas=[chroma_metadata],
                )

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            return self.search(query, top_k=top_k)

        filtered = [
            record
            for record in self._store
            if all((record.get("metadata") or {}).get(key) == value for key, value in metadata_filter.items())
        ]
        return self._search_records(query, filtered, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        remaining: list[dict[str, Any]] = []
        removed_ids: list[str] = []
        for record in self._store:
            metadata = record.get("metadata") or {}
            belongs = record.get("doc_id") == doc_id or metadata.get("doc_id") == doc_id
            if belongs:
                removed_ids.append(record["id"])
            else:
                remaining.append(record)

        if not removed_ids:
            return False

        self._store = remaining
        if self._use_chroma and self._collection is not None:
            try:
                self._collection.delete(ids=removed_ids)
            except Exception:
                pass
        return True
