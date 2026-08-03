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
            chunk = text[start: start + self.chunk_size]
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
        if not text or not text.strip():
            return []

        # Tách sau:
        # - ".", "!" hoặc "?" nếu theo sau là khoảng trắng
        # - "." nếu theo sau là xuống dòng
        sentences = re.split(
            r"(?<=[.!?])[ \t]+|(?<=\.)\n+",
            text.strip(),
        )

        # Xóa khoảng trắng thừa và loại bỏ phần tử rỗng
        sentences = [
            re.sub(r"\s+", " ", sentence).strip()
            for sentence in sentences
            if sentence.strip()
        ]

        chunks: list[str] = []

        for start in range(
                0,
                len(sentences),
                self.max_sentences_per_chunk,
        ):
            sentence_group = sentences[
                start: start + self.max_sentences_per_chunk
            ]
            chunks.append(" ".join(sentence_group))

        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]

    The chunker first tries larger semantic separators. If a resulting
    section is still larger than chunk_size, it continues with the next
    separator. The empty separator performs a hard character split.
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(
            self,
            separators: list[str] | None = None,
            chunk_size: int = 500,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        self.separators = (
            self.DEFAULT_SEPARATORS.copy()
            if separators is None
            else list(separators)
        )
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        return self._split(text, self.separators)

    def _split(
            self,
            current_text: str,
            remaining_separators: list[str],
    ) -> list[str]:
        if not current_text:
            return []

        if len(current_text) <= self.chunk_size:
            return [current_text]

        # Không còn separator thì cắt cứng theo số ký tự.
        if not remaining_separators:
            return [
                current_text[start: start + self.chunk_size]
                for start in range(0, len(current_text), self.chunk_size)
            ]

        separator = remaining_separators[0]
        next_separators = remaining_separators[1:]

        # Separator rỗng biểu thị cắt cứng theo ký tự.
        if separator == "":
            return [
                current_text[start: start + self.chunk_size]
                for start in range(0, len(current_text), self.chunk_size)
            ]

        # Nếu separator hiện tại không tồn tại, thử separator tiếp theo.
        if separator not in current_text:
            return self._split(current_text, next_separators)

        raw_parts = current_text.split(separator)

        # Gắn lại separator để không làm mất nội dung gốc.
        parts = [
            part + separator if index < len(raw_parts) - 1 else part
            for index, part in enumerate(raw_parts)
        ]

        chunks: list[str] = []
        current_chunk = ""

        for part in parts:
            if not part:
                continue

            # Phần hiện tại quá lớn: xử lý đệ quy bằng separator tiếp theo.
            if len(part) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                chunks.extend(self._split(part, next_separators))
                continue

            # Ghép part vào chunk hiện tại nếu vẫn không vượt giới hạn.
            if len(current_chunk) + len(part) <= self.chunk_size:
                current_chunk += part
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
    if len(vec_a) != len(vec_b):
        raise ValueError("Vectors must have the same dimension")

    magnitude_a = math.sqrt(_dot(vec_a, vec_a))
    magnitude_b = math.sqrt(_dot(vec_b, vec_b))

    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0

    return _dot(vec_a, vec_b) / (magnitude_a * magnitude_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        # Đảm bảo overlap luôn nhỏ hơn chunk_size.
        overlap = min(50, chunk_size - 1)

        strategies = {
            "fixed_size": FixedSizeChunker(
                chunk_size=chunk_size,
                overlap=overlap,
            ),
            "by_sentences": SentenceChunker(
                max_sentences_per_chunk=3,
            ),
            "recursive": RecursiveChunker(
                chunk_size=chunk_size,
            ),
        }

        comparison: dict = {}

        for strategy_name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            lengths = [len(chunk) for chunk in chunks]

            comparison[strategy_name] = {
                "count": len(chunks),
                "avg_length": (
                    sum(lengths) / len(lengths)
                    if lengths
                    else 0.0
                ),
                "chunks": chunks,
                "chunk_count": len(chunks),
                "min_chunk_length": min(lengths, default=0),
                "max_chunk_length": max(lengths, default=0),
                "average_chunk_length": (
                    sum(lengths) / len(lengths)
                    if lengths
                    else 0.0
                ),
                "total_characters": sum(lengths),
            }

        return comparison
