# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Minh Đức
**Nhóm:** Chậm Deadline  
**Ngày:** 2026-08-03

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**

> Hai đoạn văn bản có vector embedding hướng gần giống nhau trong không gian vector, nên nội dung/ý nghĩa của chúng thường liên quan hoặc gần nhau về ngữ nghĩa. Điểm cosine càng gần 1 thì mức độ tương đồng càng cao.

**Ví dụ có độ tương tự CAO:**

- Câu A: Người mua có thể yêu cầu trả hàng và hoàn tiền trong vòng 15 ngày.
- Câu B: Shopee cho phép gửi yêu cầu hoàn trả sản phẩm trong 15 ngày kể từ khi giao thành công.
- Tại sao tương đồng: Cùng nói về chính sách trả hàng/hoàn tiền và cùng nêu thời hạn 15 ngày.

**Ví dụ có độ tương tự THẤP:**

- Câu A: Người mua có thể yêu cầu trả hàng và hoàn tiền trong vòng 15 ngày.
- Câu B: Người bán phải khai báo đúng khối lượng sản phẩm khi đăng bán trên sàn.
- Tại sao khác: Một câu về quyền đổi trả của người mua, câu còn lại về quy định đăng bán của người bán — chủ đề khác nhau.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**

> Cosine đo góc giữa hai vector nên ít bị ảnh hưởng bởi độ dài/magnitude của embedding (văn bản dài/ngắn), trong khi khoảng cách Euclid nhạy với độ lớn vector. Với text embeddings, hướng (ý nghĩa) thường quan trọng hơn độ dài tuyệt đối.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

> *Trình bày phép tính:* `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.111...) = 23`
> *Đáp án:* **23 chunks**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**

> Với overlap=100: `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = ceil(24.75) = 25` → số chunk tăng (23 → 25) vì bước nhảy nhỏ hơn. Tăng overlap giúp giữ ngữ cảnh liền mạch giữa các chunk, giảm nguy cơ cắt đứt ý giữa hai đoạn khi truy xuất.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

`**SentenceChunker.chunk`** — hướng tiếp cận:

> Dùng `re.split(r"(\. |\! |\? |\.\n)", text)` để tách câu theo đúng các ranh giới đề bài, đồng thời giữ lại dấu câu gắn với từng câu. Sau đó chuẩn hóa khoảng trắng bằng `" ".join(...split())`, rồi nhóm tối đa `max_sentences_per_chunk` câu thành một chunk. Edge case: text rỗng/chỉ khoảng trắng trả về `[]`; nếu không tách được câu nào thì trả về một chunk đã làm sạch.

`**RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:

> Thử lần lượt các separator theo thứ tự ưu tiên (`\n\n` → `\n` → `.`  →  `` → `""`). Đoạn còn dài hơn `chunk_size` thì tách bằng separator hiện tại rồi đệ quy với các separator còn lại; các mảnh nhỏ được gộp lại miễn chưa vượt `chunk_size`. Base case: text ≤ `chunk_size` trả về nguyên đoạn; hết separator hoặc separator `""` thì hard-split theo kích thước cố định. Nếu danh sách separator rỗng, fallback luôn sang hard-split.

### Lớp EmbeddingStore

`**add_documents` + `search**` — hướng tiếp cận:

> Mỗi `Document` được `_make_record` thành dict gồm `id`, `doc_id`, `content`, `metadata` (tự gắn `doc_id` nếu thiếu) và `embedding` từ `embedding_fn`, rồi append vào `_store` in-memory (đồng thời add sang ChromaDB nếu khởi tạo được). `search` nhúng câu query rồi tính **dot product** với từng embedding đã lưu, sắp xếp điểm giảm dần và trả về tối đa `top_k` kết quả có khóa `content`, `score`, `metadata`.

`**search_with_filter` + `delete_document`** — hướng tiếp cận:

> Lọc **trước**, search **sau**: nếu có `metadata_filter` thì giữ các record khớp mọi cặp key-value, rồi mới chạy `_search_records` trên tập đã lọc; không filter thì gọi `search` bình thường. `delete_document` xóa mọi record có `doc_id` (trên field hoặc trong metadata) trùng `doc_id` truyền vào, trả về `True` nếu có xóa, đồng bộ xóa trên Chroma nếu đang dùng.

### Tác tử KnowledgeBaseAgent

`**answer`** — hướng tiếp cận:

> RAG 3 bước: gọi `store.search(question, top_k)` lấy chunk liên quan, ghép nội dung thành khối `Context` (cách nhau bằng dòng trống), rồi dựng prompt dạng “Use the following context… / Context / Question / Answer:”. Cuối cùng truyền nguyên prompt vào `llm_fn` và trả về chuỗi câu trả lời.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================ test session starts ============================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0 -- H:\MinhDuc\Coding\VinAI\Lab\Day07\DAY07_2A202601438_NguyenMinhDuc\.venv\Scripts\python.exe   
cachedir: .pytest_cache
rootdir: H:\MinhDuc\Coding\VinAI\Lab\Day07\DAY07_2A202601438_NguyenMinhDuc    
plugins: anyio-4.14.2
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_existP 
ASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED 
[ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED [ 23%] 
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 
28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED  [ 33%] 
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED [ 45%] 
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size 
PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k 
PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 
64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================ 42 passed in 0.23s =============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

> Embedder: `text-embedding-3-small` (OpenAI). Dự đoán ghi theo kỳ vọng ngữ nghĩa trước khi đối chiếu điểm.


| Cặp | Câu A                                                                 | Câu B                                                                                  | Dự đoán | Điểm thực tế | Đúng? |
| --- | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------- | ------------ | ----- |
| 1   | Người mua có thể yêu cầu trả hàng và hoàn tiền trong vòng 15 ngày.    | Shopee cho phép gửi yêu cầu hoàn trả sản phẩm trong 15 ngày kể từ khi giao thành công. | cao     | 0.7098       | Có    |
| 2   | Người mua có thể yêu cầu trả hàng và hoàn tiền trong vòng 15 ngày.    | Người bán phải khai báo đúng khối lượng sản phẩm khi đăng bán.                         | thấp    | 0.4906       | Có    |
| 3   | Phí vận chuyển được tính theo khối lượng sau khi đóng gói.            | Cước giao hàng phụ thuộc vào cân nặng kiện hàng đã đóng gói.                           | cao     | 0.6572       | Có    |
| 4   | Chính sách bảo mật giải thích cách thu thập và xử lý dữ liệu cá nhân. | Bạn có thể thanh toán bằng COD, ShopeePay hoặc thẻ tín dụng.                           | thấp    | 0.3249       | Có    |
| 5   | Shopee Đảm Bảo bảo vệ quyền lợi người mua khi mua sắm trên sàn.       | Người mua được hỗ trợ trả hàng hoàn tiền nhờ chương trình Shopee Đảm Bảo.              | cao     | 0.6328       | Có    |


**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**

> Cặp 2 chỉ đạt ~0.49 (sát ngưỡng cao/thấp) dù chủ đề buyer vs seller khác rõ — embedding vẫn bắt được ngữ cảnh chung “sàn TMĐT / sản phẩm” nên chưa tách hoàn toàn. Ngược lại, paraphrase gần nghĩa (cặp 1, 3, 5) vẫn đạt điểm cao dù diễn đạt khác; điều này cho thấy embedding ưu tiên ý nghĩa hơn trùng từ mặt chữ.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

> Cấu hình chạy: `RecursiveChunker(chunk_size=500)` + `text-embedding-3-small` (OpenAI), corpus `data/k4_ecommerce` (318 chunk).


| #   | Câu hỏi (Query)                                  | Top-1 Chunk truy xuất được (tóm tắt)                                                                                                    | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt)                                                                                                        |
| --- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Làm sao để trả hàng trên Shopee?                 | Điều kiện không thể yêu cầu Trả hàng/Hoàn tiền nếu tài khoản chưa liên kết phương thức nhận hoàn tiền (`shopee-returns-refunds`, buyer) | 0.6862     | Một phần                       | Agent nhắc điều kiện tài khoản phải liên kết phương thức hoàn tiền — liên quan chính sách trả hàng nhưng chưa mô tả quy trình thao tác |
| 2   | Thời gian xử lý hoàn tiền của Shopee là bao lâu? | Hoàn tiền khi đơn chưa chuẩn bị đúng hạn / hủy tự động (`shopee-buyer-protection`, buyer)                                               | 0.6372     | Một phần                       | Agent nói người mua được hoàn tiền theo hình thức thanh toán hoặc Số dư TK Shopee — chưa nêu rõ thời gian xử lý hoàn tiền              |
| 3   | Tiki thu thập thông tin khách hàng để làm gì?    | Hướng dẫn khách hàng vào Tài khoản Tiki để điều chỉnh thông tin (`tiki-privacy-policy`, filter `platform=tiki`)                         | 0.6816     | Một phần                       | Agent trả lời về cách chỉnh sửa thông tin tài khoản, chưa trực tiếp giải thích mục đích thu thập dữ liệu                               |
| 4   | Hàng dễ vỡ có được vận chuyển không?             | Quy định hàng cần bảo quản đặc biệt / thực phẩm tươi sống (`shopee-shipping-policy`, both)                                              | 0.6142     | Có                             | Top-3 có chunk “danh mục sản phẩm dễ vỡ”; agent tóm tắt nhóm hàng cần bảo quản đặc biệt khi vận chuyển                                 |
| 5   | Đăng bán hàng giả có bị phạt không?              | Shopee xử lý vi phạm đăng bán (xóa/khóa/ẩn sản phẩm, v.v.) theo mức độ (`shopee-seller-listing`, filter `customer_role=seller`)         | 0.5876     | Có                             | Agent nêu người bán vi phạm quy định đăng bán sẽ bị biện pháp xử lý tùy mức độ                                                         |


**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**

> Metadata filter (`platform=tiki`, `customer_role=seller`) giúp loại nhiễu khi câu hỏi nhắm đúng nguồn/đối tượng. Tuy nhiên top-1 đôi khi là đoạn điều kiện/ngoại lệ thay vì câu trả lời trực tiếp — cần đọc top-3 và cải thiện chunking hoặc gold answer mapping.

---

## Tự Đánh Giá (Phần Cá Nhân)


| Tiêu chí                                        | Điểm tự đánh giá |
| ----------------------------------------------- | ---------------- |
| Khởi động (Warm-up)                             | 5 / 5            |
| Hướng tiếp cận của tôi (My Approach)            | 10 / 10          |
| Hoàn thiện code (Core Implementation — tests)   | 30 / 30          |
| Dự đoán độ tương tự (Similarity Predictions)    | 5 / 5            |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10          |
| **Tổng phần cá nhân**                           | **60 / 60**      |


