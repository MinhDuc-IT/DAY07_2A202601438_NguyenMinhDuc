from __future__ import annotations

import hashlib
import math

# Multilingual model suitable for the Vietnamese corpora used in this Lab.
# The local backend remains optional; required checkpoints use MockEmbedder.
LOCAL_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_PROVIDER_ENV = "EMBEDDING_PROVIDER"


class MockEmbedder:
    """Deterministic embedding backend used by tests and default classroom runs."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim
        self._backend_name = "mock embeddings fallback"

    def __call__(self, text: str) -> list[float]:
        digest = hashlib.md5(text.encode()).hexdigest()
        seed = int(digest, 16)
        vector = []
        for _ in range(self.dim):
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            vector.append((seed / 0xFFFFFFFF) * 2 - 1)
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self(text) for text in texts]


class LocalEmbedder:
    """Sentence Transformers-backed local embedder."""

    def __init__(self, model_name: str = LOCAL_EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._backend_name = model_name
        self.model = SentenceTransformer(model_name)

    def __call__(self, text: str) -> list[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        if hasattr(embedding, "tolist"):
            return embedding.tolist()
        return [float(value) for value in embedding]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        if hasattr(embeddings, "tolist"):
            return embeddings.tolist()
        return [[float(value) for value in row] for row in embeddings]


class OpenAIEmbedder:
    """OpenAI embeddings API-backed embedder."""

    def __init__(self, model_name: str = OPENAI_EMBEDDING_MODEL, batch_size: int = 64) -> None:
        from openai import OpenAI

        self.model_name = model_name
        self._backend_name = model_name
        self.batch_size = max(1, batch_size)
        self.client = OpenAI()

    def __call__(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed many texts in fewer API calls (much faster for ingest)."""
        if not texts:
            return []

        vectors: list[list[float]] = []
        total = len(texts)
        for start in range(0, total, self.batch_size):
            batch = texts[start : start + self.batch_size]
            # OpenAI rejects empty strings; keep alignment with placeholders.
            safe_batch = [text if text.strip() else " " for text in batch]
            response = self.client.embeddings.create(model=self.model_name, input=safe_batch)
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend([list(map(float, item.embedding)) for item in ordered])
            end = min(start + self.batch_size, total)
            print(f"  Embedded {end}/{total} chunks...", flush=True)
        return vectors


_mock_embed = MockEmbedder()
