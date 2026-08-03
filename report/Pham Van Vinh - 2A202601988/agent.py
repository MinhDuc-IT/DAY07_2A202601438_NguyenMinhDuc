from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(
        self,
        store: EmbeddingStore,
        llm_fn: Callable[[str], str],
    ) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        if not question or not question.strip():
            raise ValueError("question must not be empty")

        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        results = self.store.search(
            query=question.strip(),
            top_k=top_k,
        )

        if not results:
            return (
                "Không tìm thấy thông tin liên quan trong cơ sở tri thức "
                "để trả lời câu hỏi này."
            )

        context_parts: list[str] = []

        for index, result in enumerate(results, start=1):
            content = result.get("content", "").strip()
            metadata = result.get("metadata", {})
            score = result.get("score")

            if not content:
                continue

            source = (
                metadata.get("source")
                or metadata.get("channel")
                or metadata.get("doc_id")
                or "không xác định"
            )

            score_text = (
                f"{float(score):.4f}"
                if isinstance(score, (int, float))
                else "N/A"
            )

            context_parts.append(
                f"[Nguồn {index}]\n"
                f"Nguồn: {source}\n"
                f"Độ liên quan: {score_text}\n"
                f"Nội dung: {content}"
            )

        if not context_parts:
            return (
                "Không tìm thấy thông tin có nội dung hợp lệ "
                "trong cơ sở tri thức."
            )

        context = "\n\n".join(context_parts)

        prompt = f"""
Bạn là trợ lý trả lời câu hỏi dựa trên cơ sở tri thức được cung cấp.

Yêu cầu:
- Chỉ sử dụng thông tin trong phần NGỮ CẢNH.
- Không tự bổ sung thông tin không có căn cứ.
- Nếu ngữ cảnh không đủ để trả lời, hãy nói rõ rằng chưa có đủ thông tin.
- Nếu các nguồn có ý kiến khác nhau, hãy tổng hợp các ý kiến và nêu rõ sự khác biệt.
- Trả lời ngắn gọn, trực tiếp và bằng tiếng Việt.
- Khi có thể, hãy dẫn nguồn bằng dạng [Nguồn 1], [Nguồn 2].

NGỮ CẢNH:
{context}

CÂU HỎI:
{question.strip()}

CÂU TRẢ LỜI:
""".strip()

        answer = self.llm_fn(prompt)

        if not isinstance(answer, str):
            raise TypeError("llm_fn must return a string")

        return answer.strip()