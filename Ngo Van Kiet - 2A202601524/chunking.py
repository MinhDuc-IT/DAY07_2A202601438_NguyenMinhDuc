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
        # TODO: split into sentences, group into chunks
        if not text:
            return []
        
        sentences_raw = re.split(r'(\.\s+|\!\s+|\?\s+|\.\n)', text)
        sentences = []
        for i in range(0, len(sentences_raw), 2):
            s = sentences_raw[i]
            if i + 1 < len(sentences_raw):
                s += sentences_raw[i+1]
            if s.strip():
                sentences.append(s.strip())
                
        chunks = []
        for i in range(0, len(sentences), self.max_sentences_per_chunk):
            chunk = " ".join(sentences[i:i+self.max_sentences_per_chunk])
            chunks.append(chunk)
            
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
        # TODO: implement recursive splitting strategy
        if not text:
            return []
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        # TODO: recursive helper used by RecursiveChunker.chunk
        if len(current_text) <= self.chunk_size:
            return [current_text]
            
        if not remaining_separators:
            return [current_text]
            
        separator = remaining_separators[0]
        splits = current_text.split(separator)
        
        chunks = []
        current_chunk = ""
        
        for i, s in enumerate(splits):
            part = s + (separator if i < len(splits) - 1 else "")
            
            if len(current_chunk) + len(part) <= self.chunk_size:
                current_chunk += part
            else:
                if current_chunk:
                    chunks.extend(self._split(current_chunk, remaining_separators[1:]))
                current_chunk = part
                
        if current_chunk:
            chunks.extend(self._split(current_chunk, remaining_separators[1:]))
            
        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    # TODO: implement cosine similarity formula
    mag_a = math.sqrt(sum(x*x for x in vec_a))
    mag_b = math.sqrt(sum(x*x for x in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return _dot(vec_a, vec_b) / (mag_a * mag_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        # TODO: call each chunker, compute stats, return comparison dict
        fixed = FixedSizeChunker(chunk_size=chunk_size, overlap=20).chunk(text)
        sentences = SentenceChunker(max_sentences_per_chunk=3).chunk(text)
        recursive = RecursiveChunker(chunk_size=chunk_size).chunk(text)
        
        return {
            'fixed_size': {
                'count': len(fixed),
                'avg_length': sum(len(c) for c in fixed) / max(1, len(fixed)),
                'chunks': fixed
            },
            'by_sentences': {
                'count': len(sentences),
                'avg_length': sum(len(c) for c in sentences) / max(1, len(sentences)),
                'chunks': sentences
            },
            'recursive': {
                'count': len(recursive),
                'avg_length': sum(len(c) for c in recursive) / max(1, len(recursive)),
                'chunks': recursive
            }
        }
