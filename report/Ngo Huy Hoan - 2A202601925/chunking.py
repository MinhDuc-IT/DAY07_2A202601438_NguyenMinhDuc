from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        # split on ". ", "! ", "? " or ".\n"
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|(?<=\.)\n', text) if s.strip()]
        chunks = []
        for i in range(0, len(sentences), self.max_sentences_per_chunk):
            chunks.append(" ".join(sentences[i:i+self.max_sentences_per_chunk]))
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if not current_text:
            return []
        if len(current_text) <= self.chunk_size or not remaining_separators:
            return [current_text]

        sep = remaining_separators[0]
        if sep == "":
            # fallback: split by character limit
            return [current_text[i:i+self.chunk_size] for i in range(0, len(current_text), self.chunk_size)]
        
        parts = current_text.split(sep)
        chunks = []
        current_chunk = ""
        
        for part in parts:
            if len(part) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                chunks.extend(self._split(part, remaining_separators[1:]))
            else:
                if len(current_chunk) + len(sep) + len(part) <= self.chunk_size:
                    current_chunk = (current_chunk + sep + part) if current_chunk else part
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = part
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    dot_prod = _dot(vec_a, vec_b)
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_prod / (norm_a * norm_b)


class SemanticChunker:
    def __init__(self, embedding_fn, similarity_threshold: float = 0.8) -> None:
        self.embedding_fn = embedding_fn
        self.similarity_threshold = similarity_threshold

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|(?<=\.)\n', text) if s.strip()]
        if not sentences:
            return []
            
        embeddings = [self.embedding_fn(s) for s in sentences]
        chunks = []
        current_chunk = [sentences[0]]
        
        for i in range(1, len(sentences)):
            sim = compute_similarity(embeddings[i-1], embeddings[i])
            if sim >= self.similarity_threshold:
                current_chunk.append(sentences[i])
            else:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentences[i]]
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks


class DocumentStructureChunker:
    def __init__(self) -> None:
        pass

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        parts = re.split(r'(?m)^(#+\s+.*)', text)
        chunks = []
        current_chunk = ""
        for p in parts:
            if not p.strip():
                continue
            if re.match(r'^#+\s+', p):
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = p
            else:
                current_chunk += "\n" + p
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            
        if not chunks:
            return [text]
        return chunks


class AgenticChunker:
    def __init__(self, llm_fn) -> None:
        self.llm_fn = llm_fn

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        prompt = f"Please split the following text into logical chunks. Separate each chunk with a special token '<CHUNK>'.\n\nText:\n{text}"
        response = self.llm_fn(prompt)
        chunks = [c.strip() for c in response.split('<CHUNK>') if c.strip()]
        if not chunks:
            return [text]
        return chunks


class ChunkingStrategyComparator:
    def __init__(self, embedding_fn=None, llm_fn=None) -> None:
        self.embedding_fn = embedding_fn or (lambda x: [0.1, 0.2, 0.3])
        self.llm_fn = llm_fn or (lambda x: str(x) + " <CHUNK> mock chunk")

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "semantic": SemanticChunker(embedding_fn=self.embedding_fn).chunk(text),
            "document_structure": DocumentStructureChunker().chunk(text),
            "agentic": AgenticChunker(llm_fn=self.llm_fn).chunk(text)
        }
        result = {}
        for name, chunks in strategies.items():
            result[name] = {
                "count": len(chunks),
                "avg_length": sum(len(c) for c in chunks) / len(chunks) if chunks else 0,
                "chunks": chunks
            }
        return result
