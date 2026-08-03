#!/usr/bin/env python3
"""Chạy 5 cặp câu mẫu để điền bảng Similarity Predictions trong REPORT_CANHAN.md.

Cách dùng (từ thư mục gốc project):
    python scripts/similarity_predictions.py

Cấu hình embedder qua file .env (EMBEDDING_PROVIDER=openai|local|mock).
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

from src import (
    EMBEDDING_PROVIDER_ENV,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    LocalEmbedder,
    MockEmbedder,
    OpenAIEmbedder,
    compute_similarity,
)

# Sửa / thay các cặp này nếu muốn dùng câu của bạn.
PAIRS: list[tuple[str, str]] = [
    (
        "Người mua có thể yêu cầu trả hàng và hoàn tiền trong vòng 15 ngày.",
        "Shopee cho phép gửi yêu cầu hoàn trả sản phẩm trong 15 ngày kể từ khi giao thành công.",
    ),
    (
        "Người mua có thể yêu cầu trả hàng và hoàn tiền trong vòng 15 ngày.",
        "Người bán phải khai báo đúng khối lượng sản phẩm khi đăng bán.",
    ),
    (
        "Phí vận chuyển được tính theo khối lượng sau khi đóng gói.",
        "Cước giao hàng phụ thuộc vào cân nặng kiện hàng đã đóng gói.",
    ),
    (
        "Chính sách bảo mật giải thích cách thu thập và xử lý dữ liệu cá nhân.",
        "Bạn có thể thanh toán bằng COD, ShopeePay hoặc thẻ tín dụng.",
    ),
    (
        "Shopee Đảm Bảo bảo vệ quyền lợi người mua khi mua sắm trên sàn.",
        "Người mua được hỗ trợ trả hàng hoàn tiền nhờ chương trình Shopee Đảm Bảo.",
    ),
]


def load_embedder():
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "openai").strip().lower()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or api_key == "your-key-here":
            raise SystemExit(
                "OPENAI_API_KEY chưa được đặt trong .env. "
                "Mở file .env và thay your-key-here bằng API key thật."
            )
        try:
            model_name = os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)
            embedder = OpenAIEmbedder(model_name=model_name)
            print(f"Embedder: {embedder._backend_name} (provider=openai)")
            return embedder
        except Exception as error:
            raise SystemExit(f"Không khởi tạo được OpenAIEmbedder: {error}") from error

    if provider == "local":
        try:
            model_name = os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL)
            embedder = LocalEmbedder(model_name=model_name)
            print(f"Embedder: {embedder._backend_name} (provider=local)")
            return embedder
        except Exception as error:
            print(f"Local embedder không sẵn sàng ({error}); dùng mock.")
            embedder = MockEmbedder()
            print(f"Embedder: {embedder._backend_name} (provider=mock fallback)")
            return embedder

    embedder = MockEmbedder()
    print(f"Embedder: {embedder._backend_name} (provider=mock)")
    return embedder


def main() -> int:
    embedder = load_embedder()
    print()
    print("Điền vào REPORT_CANHAN.md — Phần 4 (Similarity Predictions)")
    print("-" * 72)

    for index, (sentence_a, sentence_b) in enumerate(PAIRS, start=1):
        score = compute_similarity(embedder(sentence_a), embedder(sentence_b))
        level = "cao" if score >= 0.5 else "thấp"
        print(f"Cặp {index}")
        print(f"  Câu A: {sentence_a}")
        print(f"  Câu B: {sentence_b}")
        print(f"  Điểm thực tế: {score:.4f}  (gợi ý mức: {level})")
        print()

    print("Nhắc: cột 'Dự đoán' phải ghi TRƯỚC khi nhìn điểm; cột 'Đúng?' so dự đoán với mức cao/thấp.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
