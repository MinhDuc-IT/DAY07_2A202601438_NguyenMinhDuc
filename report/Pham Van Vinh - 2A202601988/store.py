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

            # Dùng inner product để phù hợp với cách tính _dot
            # ở backend in-memory.
            self._collection = client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "ip"},
            )
            self._use_chroma = True

        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        """
        Convert a Document into the normalized internal record format.

        Record format:
            {
                "id": str,
                "content": str,
                "metadata": dict,
                "embedding": list[float],
            }
        """
        content = getattr(doc, "content", None)

        if content is None:
            raise ValueError("Document must have a 'content' field")

        if not isinstance(content, str):
            raise TypeError("Document content must be a string")

        metadata = dict(getattr(doc, "metadata", {}) or {})

        current_index = self._next_index
        self._next_index += 1

        # doc_id dùng để nhận diện tài liệu gốc.
        doc_id = (
            metadata.get("doc_id")
            or getattr(doc, "doc_id", None)
            or getattr(doc, "id", None)
            or f"document-{current_index}"
        )

        # Mỗi chunk phải có một id riêng để lưu vào ChromaDB.
        record_id = (
            metadata.get("chunk_id")
            or getattr(doc, "chunk_id", None)
            or getattr(doc, "id", None)
            or f"{doc_id}-chunk-{current_index}"
        )

        metadata.setdefault("doc_id", str(doc_id))
        metadata.setdefault("chunk_id", str(record_id))

        embedding = self._embedding_fn(content)

        return {
            "id": str(record_id),
            "content": content,
            "metadata": metadata,
            "embedding": embedding,
        }

    def _search_records(
        self,
        query: str,
        records: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        Run an in-memory inner-product similarity search.
        """
        if top_k <= 0 or not records:
            return []

        query_embedding = self._embedding_fn(query)
        scored_records: list[dict[str, Any]] = []

        for record in records:
            embedding = record["embedding"]

            if len(query_embedding) != len(embedding):
                raise ValueError(
                    "Query embedding and document embedding "
                    "must have the same dimension"
                )

            score = _dot(query_embedding, embedding)

            scored_records.append(
                {
                    "id": record["id"],
                    "content": record["content"],
                    "metadata": dict(record["metadata"]),
                    "score": score,
                }
            )

        scored_records.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return scored_records[:top_k]

    def _convert_chroma_results(
        self,
        raw_results: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Convert ChromaDB's nested query result into normalized records.
        """
        ids = raw_results.get("ids") or [[]]
        documents = raw_results.get("documents") or [[]]
        metadatas = raw_results.get("metadatas") or [[]]
        distances = raw_results.get("distances") or [[]]

        result_ids = ids[0] if ids else []
        result_documents = documents[0] if documents else []
        result_metadatas = metadatas[0] if metadatas else []
        result_distances = distances[0] if distances else []

        normalized_results: list[dict[str, Any]] = []

        for index, record_id in enumerate(result_ids):
            document = (
                result_documents[index]
                if index < len(result_documents)
                else ""
            )
            metadata = (
                result_metadatas[index]
                if index < len(result_metadatas)
                else {}
            )
            distance = (
                result_distances[index]
                if index < len(result_distances)
                else 1.0
            )

            # Với hnsw:space="ip":
            # distance = 1 - inner_product
            score = 1.0 - float(distance)

            normalized_results.append(
                {
                    "id": record_id,
                    "content": document,
                    "metadata": metadata or {},
                    "score": score,
                }
            )

        return normalized_results

    def _make_chroma_filter(
        self,
        metadata_filter: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert a simple key-value filter into ChromaDB where syntax.
        """
        conditions = [
            {key: value}
            for key, value in metadata_filter.items()
        ]

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(
            ids=[...],
            documents=[...],
            embeddings=[...],
            metadatas=[...],
        )

        For in-memory: append records to self._store.
        """
        if not docs:
            return

        records = [
            self._make_record(doc)
            for doc in docs
        ]

        if self._use_chroma and self._collection is not None:
            self._collection.add(
                ids=[
                    record["id"]
                    for record in records
                ],
                documents=[
                    record["content"]
                    for record in records
                ],
                embeddings=[
                    record["embedding"]
                    for record in records
                ],
                metadatas=[
                    record["metadata"]
                    for record in records
                ],
            )
            return

        self._store.extend(records)

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding
        versus all stored embeddings.
        """
        if top_k <= 0:
            return []

        if self._use_chroma and self._collection is not None:
            collection_size = self._collection.count()

            if collection_size == 0:
                return []

            query_embedding = self._embedding_fn(query)

            raw_results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection_size),
                include=[
                    "documents",
                    "metadatas",
                    "distances",
                ],
            )

            return self._convert_chroma_results(raw_results)

        return self._search_records(
            query=query,
            records=self._store,
            top_k=top_k,
        )

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        if self._use_chroma and self._collection is not None:
            return int(self._collection.count())

        return len(self._store)

    def search_with_filter(
        self,
        query: str,
        top_k: int = 3,
        metadata_filter: dict | None = None,
    ) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter,
        then run similarity search.
        """
        if top_k <= 0:
            return []

        if not metadata_filter:
            return self.search(query, top_k)

        if self._use_chroma and self._collection is not None:
            collection_size = self._collection.count()

            if collection_size == 0:
                return []

            query_embedding = self._embedding_fn(query)
            chroma_filter = self._make_chroma_filter(
                metadata_filter
            )

            raw_results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection_size),
                where=chroma_filter,
                include=[
                    "documents",
                    "metadatas",
                    "distances",
                ],
            )

            return self._convert_chroma_results(raw_results)

        filtered_records = [
            record
            for record in self._store
            if all(
                record["metadata"].get(key) == expected_value
                for key, expected_value in metadata_filter.items()
            )
        ]

        return self._search_records(
            query=query,
            records=filtered_records,
            top_k=top_k,
        )

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        if self._use_chroma and self._collection is not None:
            matching_records = self._collection.get(
                where={"doc_id": doc_id},
            )

            matching_ids = matching_records.get("ids") or []

            if not matching_ids:
                return False

            self._collection.delete(ids=matching_ids)
            return True

        original_size = len(self._store)

        self._store = [
            record
            for record in self._store
            if record["metadata"].get("doc_id") != doc_id
        ]

        return len(self._store) < original_size