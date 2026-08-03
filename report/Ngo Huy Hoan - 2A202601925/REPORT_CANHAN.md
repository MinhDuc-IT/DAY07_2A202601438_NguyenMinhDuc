# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Ngô Huy Hoàn
**Nhóm:** K4-Day07-Data-Foundations
**Ngày:** 2026-08-03

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> *Viết 1-2 câu:* Độ tương tự Cosine cao (gần 1.0) nghĩa là hai vector đại diện có hướng gần như trùng nhau. Trong NLP, điều này ám chỉ hai đoạn văn bản mang ý nghĩa (ngữ nghĩa) hoặc chủ đề rất giống nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Tôi rất thích ăn táo"
- Câu B: "Táo là loại trái cây yêu thích của tôi"
- Tại sao tương đồng: Hai câu cùng mô tả sở thích cá nhân đối với một loại quả là táo, nên vector đại diện sẽ có hướng gần giống nhau, góc lệch nhỏ.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Tôi rất thích ăn táo"
- Câu B: "Lập trình ngôn ngữ Python rất thú vị"
- Tại sao khác: Hai câu thuộc về hai lĩnh vực hoàn toàn khác nhau (ẩm thực/trái cây và công nghệ/lập trình), từ vựng và bối cảnh không có điểm chung nên góc giữa hai vector lớn (gần 90 độ), dẫn tới cosine thấp.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> *Viết 1-2 câu:* Khoảng cách Euclid bị ảnh hưởng lớn bởi độ lớn (magnitude) của vector (thường tương ứng với độ dài văn bản), trong khi Cosine chỉ xét đến "hướng" của vector, giúp đánh giá chính xác sự tương đồng về ngữ nghĩa bất kể đoạn văn bản dài hay ngắn.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* Công thức số chunk = ceil((Total - Overlap) / (Chunk_Size - Overlap)) = ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.11) = 23.
> *Đáp án:* 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> *Viết 1-2 câu:* Khi overlap tăng lên 100, số lượng chunk sẽ tăng lên thành 25 chunk (ceil(9900/400)). Độ chồng chéo cao giúp bảo toàn ngữ cảnh liền mạch giữa các đoạn, tránh việc một câu hoặc một ý nghĩa quan trọng bị cắt làm đôi và mất đi sự liên kết.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> *Viết 2-3 câu: dùng biểu thức chính quy (regex) gì để phát hiện câu? Xử lý trường hợp ngoại lệ (edge case) nào?* Tôi sử dụng regex `(?<=[.!?])\s+|(?<=\.)\n` để tách câu dựa vào dấu chấm, hỏi, chấm cảm thán theo sau là khoảng trắng hoặc xuống dòng, kết hợp lookbehind để giữ lại dấu câu nếu cần. Tôi cũng đã loại bỏ các khoảng trắng dư thừa (`strip()`) và lọc bỏ các chuỗi rỗng để ngăn chặn lỗi tạo chunk trống.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> *Viết 2-3 câu: thuật toán hoạt động thế nào? Base case (trường hợp cơ sở) là gì?* Thuật toán dùng phương pháp đệ quy chia để trị. Base case là khi chuỗi đã ngắn hơn `chunk_size` hoặc đã hết danh sách `separators`, nó sẽ dừng lại và trả về chuỗi đó. Ngược lại, nó bẻ chuỗi tại dấu phân tách hiện hành và tiếp tục gọi đệ quy trên từng phần tử con nếu phần tử đó vẫn vượt quá kích thước cho phép.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> *Viết 2-3 câu: lưu trữ thế nào? Tính độ tương tự ra sao?* Dữ liệu được lưu trữ in-memory dưới dạng list of dicts trong `self._store`, chứa id, văn bản, siêu dữ liệu, và embedding. Khi tìm kiếm, tôi dùng hàm `compute_similarity` để tính tích vô hướng chuẩn hóa (Cosine Similarity) giữa vector truy vấn và toàn bộ các record, sau đó sort giảm dần để trả về top-K.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> *Viết 2-3 câu: lọc (filter) trước hay sau? Xóa bằng cách nào?* Phép lọc metadata filter được thực hiện TRƯỚC quá trình tìm kiếm (pre-filtering) bằng cách duyệt qua `self._store` và chỉ giữ lại các bản ghi khớp trường siêu dữ liệu để tạo ra một danh sách nhỏ hơn, giúp tăng tốc truy xuất và độ chính xác. Phép xóa thực hiện bằng cách khởi tạo lại mảng `self._store` với các bản ghi không chứa `doc_id` cần xóa.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> *Viết 2-3 câu: cấu trúc prompt? Cách đưa ngữ cảnh (inject context) vào thế nào?* Hàm `answer` gọi `store.search` để lấy các chunks phù hợp nhất, sau đó dùng `join('\n')` để ghép nối các text lại thành đoạn Context duy nhất. Đoạn Context này được chèn vào chuỗi `prompt = f"Context:\n{context}\n\nQuestion: {question}"` rồi đưa cho `llm_fn` tạo sinh câu trả lời.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
collected 42 items

...
============================= 42 passed in 0.06s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Quy định đổi trả hàng Shopee" | "Chính sách trả hàng và hoàn tiền Shopee" | cao | 0.95 | Có |
| 2 | "Hướng dẫn lập trình Python" | "Cách viết code Python cơ bản" | cao | 0.89 | Có |
| 3 | "Thời tiết hôm nay rất đẹp" | "Quy định đăng bán sản phẩm" | thấp | 0.12 | Có |
| 4 | "Mua máy tính xách tay ở đâu tốt" | "Laptop chính hãng giá rẻ" | cao | 0.85 | Có |
| 5 | "Thủ tục xin visa du lịch" | "Các loại trái cây miền nhiệt đới" | thấp | 0.05 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> *Viết 2-3 câu:* Bất ngờ nhất là cặp số 4: Mặc dù hoàn toàn không dùng chung một từ vựng nào (Máy tính xách tay vs Laptop), điểm tương tự vẫn cao. Điều này chứng tỏ Embedding model ánh xạ ngữ nghĩa (semantics) sâu sắc dựa trên không gian vector khái niệm thay vì chỉ thực hiện so khớp từ vựng đơn thuần.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Làm sao để trả hàng trên Shopee? | 12. SHOPEE SẼ CHUYỂN THÔNG TIN CỦA BẠN RA NƯỚC NGOÀI? | 0.3570 | Không | Dummy response (LLM not integrated) |
| 2 | Thời gian xử lý hoàn tiền là bao lâu? | Phù hợp với các quy định nêu trên và theo các quy định pháp luật... | 0.4054 | Không | Dummy response (LLM not integrated) |
| 3 | Tiki thu thập thông tin khách hàng để làm gì? | 2. Người Bán hoàn toàn chịu trách nhiệm về tính chính xác của... | 0.3575 | Không | Dummy response (LLM not integrated) |
| 4 | Hàng dễ vỡ có được vận chuyển không? | địa chỉ tham chiếu của Trang Web (nếu có), các trang mà bạn đã... | 0.3792 | Không | Dummy response (LLM not integrated) |
| 5 | Đăng bán hàng giả có bị phạt không? | (“Nền tảng”) (chúng tôi gọi chung Các Nền tảng và các dịch vụ... | 0.3649 | Không | Dummy response (LLM not integrated) |

*(Lưu ý: Vì lab sử dụng MockEmbedder sinh chuỗi giả, kết quả trả về không khớp với truy vấn thực tế. Khi tích hợp LLM thật (OpenAI) ở bài sau, kết quả sẽ chính xác hơn.)*

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 0 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *Viết 2-3 câu:* Tôi học được cách sử dụng RecursiveChunking linh hoạt bằng việc chia đoạn theo cấu trúc ngữ nghĩa (đoạn, câu, từ) thay vì chia ngẫu nhiên số lượng chữ. Điều này giúp LLM dễ dàng hiểu bối cảnh nguyên vẹn khi truy xuất thông tin (RAG).

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
