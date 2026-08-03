#!/usr/bin/env python3
"""Chạy 5 câu hỏi Competition Results để điền REPORT_CANHAN.md — Phần 5.

Cách dùng (từ thư mục gốc, đã kích hoạt .venv):
    python scripts/competition_results.py

Cấu hình:
    - Embedder theo .env (EMBEDDING_PROVIDER=openai|local|mock)
    - Dữ liệu mặc định: data/k4_ecommerce
    - Chunker mặc định: RecursiveChunker (đổi trong CHUNKER bên dưới)
    - Sửa BENCHMARK_QUERIES cho khớp bộ câu hỏi nhóm (REPORT_NHOM.md)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(dotenv_path=ROOT / ".env", override=False)

from ingest import build_knowledge_base, chunk_document, load_documents
from src import (
    EMBEDDING_PROVIDER_ENV,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    KnowledgeBaseAgent,
    LocalEmbedder,
    MockEmbedder,
    OpenAIEmbedder,
    RecursiveChunker,
)
DATA_DIR = ROOT / "data" / "k4_ecommerce"
TOP_K = 3

# Đổi chiến lược chunking của bạn tại đây.
CHUNKER = RecursiveChunker(chunk_size=500)

# Bộ 5 câu hỏi đánh giá (thống nhất nhóm).
# Ít nhất 1 câu có metadata_filter (yêu cầu K4).
BENCHMARK_QUERIES: list[dict] = [
    {
        "query": "Làm sao để trả hàng trên Shopee?",
        "metadata_filter": None,
        "notes": "buyer / returns",
    },
    {
        "query": "Thời gian xử lý hoàn tiền của Shopee là bao lâu?",
        "metadata_filter": None,
        "notes": "buyer / refund timeline",
    },
    {
        "query": "Tiki thu thập thông tin khách hàng để làm gì?",
        "metadata_filter": {"platform": "tiki"},
        "notes": "privacy / Tiki",
    },
    {
        "query": "Hàng dễ vỡ có được vận chuyển không?",
        "metadata_filter": None,
        "notes": "shipping",
    },
    {
        "query": "Đăng bán hàng giả có bị phạt không?",
        "metadata_filter": {"customer_role": "seller"},
        "notes": "K4: seller listing",
    },
]


def load_embedder():
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "openai").strip().lower()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or api_key == "your-key-here":
            raise SystemExit("OPENAI_API_KEY chưa hợp lệ trong .env")
        model_name = os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)
        embedder = OpenAIEmbedder(model_name=model_name)
        print(f"Embedder: {embedder._backend_name} (provider=openai)")
        return embedder

    if provider == "local":
        try:
            model_name = os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL)
            embedder = LocalEmbedder(model_name=model_name)
            print(f"Embedder: {embedder._backend_name} (provider=local)")
            return embedder
        except Exception as error:
            print(f"Local lỗi ({error}); fallback mock.")
            embedder = MockEmbedder()
            print(f"Embedder: {embedder._backend_name}")
            return embedder

    embedder = MockEmbedder()
    print(f"Embedder: {embedder._backend_name} (provider=mock)")
    print("Cảnh báo: mock không phản ánh ngữ nghĩa — không dùng để kết luận retrieval.")
    return embedder


def summarize(text: str, limit: int = 160) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def demo_llm(prompt: str) -> str:
    """LLM demo: trích đoạn context đầu làm 'câu trả lời' để điền báo cáo."""
    marker = "Context:\n"
    if marker not in prompt:
        return "[DEMO LLM] Không có context."
    context = prompt.split(marker, 1)[1]
    context = context.split("\n\nQuestion:", 1)[0].strip()
    first_chunk = context.split("\n\n", 1)[0]
    return summarize(first_chunk, limit=220)


def print_query_result(index: int, item: dict, store, agent) -> bool:
    query = item["query"]
    metadata_filter = item.get("metadata_filter")

    if metadata_filter:
        results = store.search_with_filter(query, top_k=TOP_K, metadata_filter=metadata_filter)
        mode = f"search_with_filter({metadata_filter})"
    else:
        results = store.search(query, top_k=TOP_K)
        mode = "search"

    answer = agent.answer(query, top_k=TOP_K)
    top1 = results[0] if results else None
    relevant_top3 = len(results) > 0  # người dùng tự đánh giá lại khi điền report

    print(f"Câu hỏi {index}")
    print(f"  Query: {query}")
    print(f"  Mode: {mode}")
    print(f"  Notes: {item.get('notes', '')}")
    if top1:
        meta = top1.get("metadata") or {}
        print(f"  Top-1 score: {top1['score']:.4f}")
        print(f"  Top-1 doc_id: {meta.get('doc_id', '')}")
        print(f"  Top-1 customer_role: {meta.get('customer_role', '')}")
        print(f"  Top-1 tóm tắt: {summarize(top1.get('content', ''))}")
    else:
        print("  Top-1: (không có kết quả)")
    print("  Top-3:")
    for rank, result in enumerate(results, start=1):
        meta = result.get("metadata") or {}
        print(
            f"    {rank}. score={result['score']:.4f} "
            f"doc_id={meta.get('doc_id', '')} "
            f"role={meta.get('customer_role', '')} "
            f"| {summarize(result.get('content', ''), 100)}"
        )
    print(f"  Agent (tóm tắt): {summarize(answer, 220)}")
    print(f"  Gợi ý Relevant (tự kiểm lại): {'Có' if relevant_top3 else 'Không'}")
    print()
    return bool(results)


def main() -> int:
    if not DATA_DIR.exists():
        raise SystemExit(f"Không tìm thấy thư mục dữ liệu: {DATA_DIR}")

    embedder = load_embedder()
    chunker_name = type(CHUNKER).__name__
    docs = load_documents(DATA_DIR)
    chunk_count = sum(len(chunk_document(doc, CHUNKER)) for doc in docs)
    print(f"Data: {DATA_DIR}")
    print(f"Chunker: {chunker_name}")
    print(f"Tài liệu: {len(docs)} | Chunk dự kiến: {chunk_count}")
    print("Đang nạp knowledge base (batch embed)...")
    store = build_knowledge_base(DATA_DIR, embedding_fn=embedder, chunker=CHUNKER)
    print(f"Đã nạp {store.get_collection_size()} chunk\n")

    agent = KnowledgeBaseAgent(store=store, llm_fn=demo_llm)

    print("Điền vào REPORT_CANHAN.md — Phần 5 (Competition Results)")
    print("-" * 72)

    hits = 0
    for index, item in enumerate(BENCHMARK_QUERIES, start=1):
        if print_query_result(index, item, store, agent):
            hits += 1

    print(f"Số câu có kết quả top-3: {hits} / {len(BENCHMARK_QUERIES)}")
    print("Nhắc: cột Relevant phải tự đánh giá theo gold answer của nhóm.")
    print("Nếu nhóm đã chốt 5 câu hỏi, sửa BENCHMARK_QUERIES trong script cho trùng REPORT_NHOM.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
