# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** [Ngô Văn Kiệt]
**Nhóm:** [Chậm Deadline]
**Ngày:** [3/8/2026]

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> *Viết 1-2 câu:*
Độ tương tự cosine cao nghĩa là hai vector có hướng gần giống nhau, tức là hai văn bản có nội dung hoặc ngữ nghĩa tương đồng. Giá trị cosine similarity càng gần 1 thì mức độ tương đồng càng cao.

**Ví dụ có độ tương tự CAO:**
- Câu A:Hôm nay trời rất đẹp và nắng.
- Câu B:Thời tiết hôm nay nhiều nắng và rất đẹp.
- Tại sao tương đồng: Hai câu diễn đạt cùng một ý nghĩa dù cách dùng từ hơi khác nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Tôi thích học trí tuệ nhân tạo.
- Câu B: Con mèo đang ngủ trên ghế sofa.
- Tại sao khác: Hai câu nói về hai chủ đề hoàn toàn khác nhau nên vector embedding sẽ ít giống nhau.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> *Viết 1-2 câu:* Cosine similarity chỉ so sánh hướng của các vector nên phản ánh tốt mức độ tương đồng về ngữ nghĩa. Trong khi đó, khoảng cách Euclid bị ảnh hưởng bởi độ lớn của vector, điều này thường không quan trọng đối với text embeddings.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:*
> *Đáp án:* Bước nhảy: 500 - 50 = 450
Số chunk : ((10000 - 500) / 450) + 1 = 23 

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> *Viết 1-2 câu:* Khi overlap tăng lên 100, bước nhảy giảm còn 500 − 100 = 400, nên số lượng chunk sẽ tăng (khoảng 25 chunks). Overlap lớn hơn giúp giữ được ngữ cảnh giữa các chunk, giảm tình trạng thông tin bị cắt rời ở ranh giới chunk, từ đó cải thiện chất lượng truy xuất trong RAG.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> *Viết 2-3 câu: dùng biểu thức chính quy (regex) gì để phát hiện câu? Xử lý trường hợp ngoại lệ (edge case) nào?*
Tôi sử dụng regex `r'(\.\s+|\!\s+|\?\s+|\.\n)'` để tách câu dựa trên các dấu phân cách phổ biến đồng thời giữ lại dấu câu. Sau đó, ghép lại các thành phần và lọc bỏ các khoảng trắng dư thừa, đảm bảo mỗi chunk được ghép từ tối đa `max_sentences_per_chunk` câu.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> *Viết 2-3 câu: thuật toán hoạt động thế nào? Base case (trường hợp cơ sở) là gì?*
Thuật toán đệ quy thử từng ký tự phân cách (separator) theo thứ tự ưu tiên. Base case là khi đoạn văn bản nhỏ hơn `chunk_size` hoặc không còn separator nào thì trả về luôn. Nếu có, đoạn văn bản sẽ được chia nhỏ, và các đoạn con lớn hơn `chunk_size` sẽ tiếp tục đệ quy.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> *Viết 2-3 câu: lưu trữ thế nào? Tính độ tương tự ra sao?*
Lưu trữ bằng cách chuyển các object `Document` thành từ điển (dictionary) chứa id, content, metadata và embedding (gọi hàm `_embedding_fn` để sinh vector). Khi tìm kiếm, tính toán độ tương tự cosine (cosine similarity) giữa query vector và vector của từng document trong store, sau đó sắp xếp giảm dần để trả về top K.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> *Viết 2-3 câu: lọc (filter) trước hay sau? Xóa bằng cách nào?*
Thực hiện lọc (filter) các chunk trong store trước khi tính độ tương tự để tối ưu tốc độ tìm kiếm. Hàm xóa (`delete_document`) sử dụng list comprehension để loại bỏ tất cả các bản ghi có ID khớp với `doc_id` truyền vào.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> *Viết 2-3 câu: cấu trúc prompt? Cách đưa ngữ cảnh (inject context) vào thế nào?*
Sử dụng kho lưu trữ để lấy top_k chunk phù hợp nhất với câu hỏi. Sau đó, nối các chunk này lại thành đoạn `Context:` và đính kèm vào trong cấu trúc prompt: "Context: ... Question: ... Answer:". Mô hình ngôn ngữ (LLM) sẽ dựa vào đây để sinh câu trả lời.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.11.4, pytest-9.1.1, pluggy-1.6.0 -- C:\ProgramData\Miniconda3\python.exe
cachedir: .pytest_cache
rootdir: D:\A_UET\Lab\K4-Day07-Data-Foundations-2A202601524
plugins: anyio-4.9.0, dash-3.0.0
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
...
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 4.24s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Tôi muốn đổi trả hàng | Làm sao để hoàn trả sản phẩm | cao | 0.6040 | Có |
| 2 | Bao lâu thì nhận được hàng? | Thời gian giao hàng là bao nhiêu ngày? | cao | 0.5291 | Có |
| 3 | Chính sách bảo mật thông tin | Làm thế nào để thanh toán bằng thẻ tín dụng? | thấp | 0.3636 | Có |
| 4 | Tôi muốn mua điện thoại iPhone | Cách liên hệ tổng đài chăm sóc khách hàng | thấp | 0.3562 | Có |
| 5 | Shopee có miễn phí vận chuyển không | Phí ship trên Shopee tính thế nào | cao | 0.6487 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> *Viết 2-3 câu:*
Kết quả hoàn toàn trùng khớp với dự đoán của em, không có kết quả nào quá bất ngờ. Điều này cho thấy mô hình `text-embedding-3-small` (thông qua OpenRouter) đã biểu diễn rất tốt ý nghĩa ngữ nghĩa (semantic meaning) của văn bản. Các câu dù dùng từ vựng khác nhau nhưng mang cùng ý nghĩa (cặp 1, 5) đều cho ra vector có độ tương tự cosine cao hơn hẳn so với các câu khác chủ đề.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Làm thế nào để đổi trả hàng trên Shopee? | Shopee cam kết bảo vệ thông tin cá nhân... Người mua có thể... | 0.5652 | Có | Dummy answer based on context |
| 2 | Tiki thu thập những thông tin cá nhân nào của khách hàng? | Tiki bảo mật thông tin người dùng... Tiki thu thập họ tên... | 0.6227 | Có | Dummy answer based on context |
| 3 | Quy định về thời gian giao hàng của Lazada là gì? | Thời gian giao hàng của Lazada phụ thuộc vào khu vực... | 0.7412 | Có | Dummy answer based on context |
| 4 | Shopee bảo vệ thông tin người dùng như thế nào? | Shopee cam kết bảo vệ thông tin cá nhân... | 0.7407 | Có | Dummy answer based on context |
| 5 | Tôi có thể thanh toán trên Tiki bằng những phương thức nào? | Tiki bảo mật thông tin người dùng... Bạn có thể thanh toán bằng... | 0.6813 | Có | Dummy answer based on context |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *Viết 2-3 câu:*
Khi sử dụng một mô hình embedding thực sự tốt như `text-embedding-3-small`, kết quả truy xuất (retrieval) đạt độ chính xác gần như tuyệt đối (5/5). Điều này cho thấy việc chọn đúng embedding model quyết định rất lớn đến chất lượng của toàn bộ hệ thống RAG.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
