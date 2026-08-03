# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Phạm Văn Vinh
**Nhóm:** Chậm Deadline
**Ngày:** 2026-08-03

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương đồng cosine cao nghĩa là hai vector biểu diễn văn bản có hướng gần giống nhau trong không gian embedding. Nói cách khác, hai đoạn văn bản có khả năng đang nói về ý nghĩa hoặc chủ đề gần nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: Khách hàng có thể đổi trả sản phẩm trong vòng 7 ngày.
- Câu B: Chính sách hoàn trả cho phép trả hàng trong vòng một tuần.
- Tại sao tương đồng: Hai câu cùng nói về quyền đổi/trả hàng trong một khoảng thời gian tương đương.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Người bán phải cung cấp thông tin sản phẩm chính xác.
- Câu B: Hôm nay thời tiết có mưa lớn.
- Tại sao khác: Hai câu thuộc hai chủ đề khác nhau, một câu nói về quy định bán hàng và một câu nói về thời tiết.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine similarity tập trung vào hướng của vector nên phù hợp để so sánh ý nghĩa giữa các văn bản. Euclidean distance phụ thuộc nhiều hơn vào độ lớn vector, trong khi với text embeddings điều quan trọng thường là hai vector có cùng hướng ngữ nghĩa hay không.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* số chunk = ceil((10,000 - 50) / (500 - 50)) = ceil(9,950 / 450) = ceil(22.11)
> *Đáp án:* 23 chunks

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi overlap tăng lên 100, số chunk = ceil((10,000 - 100) / (500 - 100)) = ceil(9,900 / 400) = 25 chunks, tức là tăng từ 23 lên 25. Overlap lớn hơn giúp giữ thêm ngữ cảnh giữa hai chunk liền nhau, nhưng đổi lại tạo ra nhiều chunk hơn và tốn thêm chi phí lưu trữ/tìm kiếm.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi dùng regex `(?<=[.!?])[ \t]+|(?<=\.)\n+` để tách câu sau dấu `.`, `!`, `?` khi có khoảng trắng hoặc sau dấu `.` khi xuống dòng. Sau khi tách, tôi chuẩn hóa khoảng trắng bằng `re.sub(r"\s+", " ", ...)`, loại bỏ chuỗi rỗng và nhóm các câu theo `max_sentences_per_chunk`. Trường hợp văn bản rỗng hoặc chỉ có khoảng trắng sẽ trả về danh sách rỗng.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Tôi triển khai chiến lược đệ quy theo thứ tự separator `["\n\n", "\n", ". ", " ", ""]`, ưu tiên chia theo ranh giới lớn trước rồi mới xuống ranh giới nhỏ hơn. Base case là văn bản rỗng thì trả về `[]`, còn đoạn có độ dài nhỏ hơn hoặc bằng `chunk_size` thì trả về chính đoạn đó. Nếu không còn separator hoặc gặp separator rỗng, hàm cắt cứng theo số ký tự để bảo đảm không bị kẹt ở đoạn quá dài.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Mỗi `Document` được chuẩn hóa thành record gồm `id`, `content`, `metadata` và `embedding`; metadata luôn có `doc_id` và `chunk_id` để truy vết chunk về tài liệu gốc. Nếu ChromaDB có sẵn thì store dùng collection của Chroma, còn nếu không có thì fallback sang danh sách in-memory. Khi search, truy vấn được embed rồi so sánh với từng embedding bằng dot product và sắp xếp giảm dần theo `score`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Với `search_with_filter`, tôi lọc metadata trước để chỉ giữ các record thỏa điều kiện, sau đó mới chạy similarity search trên tập đã lọc. Cách này giúp truy xuất tập trung hơn khi biết trước thuộc tính như phòng ban, ngôn ngữ hoặc `doc_id`. Với `delete_document`, tôi xóa toàn bộ record có `metadata["doc_id"]` trùng với tài liệu cần xóa và trả về `True` nếu số lượng record giảm.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Agent nhận câu hỏi, gọi `store.search()` để lấy top-k chunk liên quan, rồi đóng gói từng chunk thành phần ngữ cảnh gồm nguồn, score và nội dung. Prompt yêu cầu chỉ trả lời dựa trên phần NGỮ CẢNH, không tự bổ sung thông tin ngoài dữ liệu đã truy xuất và dẫn nguồn theo dạng `[Nguồn 1]`, `[Nguồn 2]` khi có thể. Cuối cùng agent truyền prompt cho `llm_fn` và kiểm tra kết quả trả về phải là chuỗi.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
$ conda run --no-capture-output -n py3.11 python -m pytest tests/ -q
..........................................                               [100%]
42 passed, 1 warning in 0.08s
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|-----|--------------|-------|
| 1 | Khách hàng có thể đổi trả sản phẩm trong vòng 7 ngày kể từ khi nhận hàng. | Người mua được phép gửi trả hàng trong 7 ngày sau khi giao thành công. | cao | 0.7340 | Có |
| 2 | Cửa hàng hỗ trợ thanh toán bằng thẻ ngân hàng và ví điện tử. | Khách hàng có thể trả tiền qua thẻ hoặc ví điện tử khi đặt hàng. | cao | 0.6509 | Có |
| 3 | Người bán phải mô tả đúng tình trạng và nguồn gốc sản phẩm. | Nhà bán hàng cần cung cấp thông tin sản phẩm chính xác và minh bạch. | cao | 0.6394 | Có |
| 4 | Đơn hàng được giao trong giờ hành chính từ thứ Hai đến thứ Sáu. | Chính sách bảo mật quy định cách thu thập và xử lý dữ liệu cá nhân. | thấp | 0.2446 | Có |
| 5 | Sản phẩm khuyến mãi có thể không áp dụng chính sách đổi trả thông thường. | Mèo đang ngủ trên ghế sofa trong phòng khách. | thấp | 0.2260 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Kết quả bất ngờ nhất là cặp 5 vẫn có điểm 0.2260 dù hai câu gần như không liên quan về mặt chủ đề. Điều này cho thấy embedding không phải lúc nào cũng đưa các câu khác chủ đề về đúng 0, mà vẫn có thể ghi nhận một mức tương đồng nền do cùng là câu tự nhiên có cấu trúc ngôn ngữ tương tự. Nhìn chung, các cặp cùng ý nghĩa về đổi trả, thanh toán và thông tin sản phẩm có điểm cao hơn rõ rệt so với các cặp khác chủ đề.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Làm sao để trả hàng trên Shopee? | Chính sách Trả hàng/Hoàn tiền Shopee: điều kiện thực hiện yêu cầu trả hàng, tài khoản nhận hoàn tiền và yêu cầu phải thực hiện trên tài khoản đã đặt đơn. | 0.6645 | Có | Người mua cần gửi yêu cầu Trả hàng/Hoàn tiền trên chính tài khoản Shopee đã đặt đơn; tài khoản cần liên kết phương thức nhận hoàn tiền hợp lệ và Shopee sẽ xem xét yêu cầu theo chính sách. |
| 2 | Thời gian xử lý hoàn tiền của Shopee là bao lâu? | Chính sách Trả hàng/Hoàn tiền Shopee: Shopee hoàn tiền khi người mua đã gửi trả sản phẩm, đơn vị vận chuyển xác nhận đã nhận hàng hoàn trả; có trường hợp hoàn ngay hoặc tự động nếu người bán không phản hồi. | 0.6302 | Có một phần | Top-3 có thông tin về điều kiện hoàn tiền nhưng không nêu một thời hạn xử lý hoàn tiền cố định. Câu trả lời phù hợp nhất là thời gian phụ thuộc từng trường hợp; Shopee có thể hoàn ngay hoặc tự động hoàn nếu người bán không phản hồi trong thời gian quy định. |
| 3 | Tiki thu thập thông tin khách hàng để làm gì? | Chính sách bảo mật Tiki: phạm vi thu thập thông tin cá nhân từ thông tin khách hàng cung cấp, tương tác trên sàn và các nguồn hợp pháp khác. | 0.7346 | Có | Tiki thu thập thông tin để xử lý đơn hàng, duy trì tài khoản, chăm sóc khách hàng, cá nhân hóa/cải thiện trải nghiệm và phục vụ giới thiệu, quảng cáo hoặc dịch vụ phù hợp hơn. |
| 4 | Hàng dễ vỡ có được vận chuyển không? | Chính sách vận chuyển Shopee: hàng có rủi ro hư hại/tổn thất cao có thể bị đơn vị vận chuyển từ chối nếu không đáp ứng điều kiện vận chuyển hoặc không có chế độ cảnh báo/vận chuyển riêng. | 0.5983 | Có | Hàng dễ vỡ hoặc có rủi ro cao có thể được hỗ trợ trong một số trường hợp, nhưng đơn vị vận chuyển có quyền từ chối. Nếu vẫn vận chuyển, người bán phải đóng gói đúng quy cách và chịu rủi ro khi hàng bị hư hỏng/tổn thất. |
| 5 | Đăng bán hàng giả có bị phạt không? | Quy định đăng bán Shopee: phần xử lý vi phạm nêu các biện pháp như xóa/khóa/tạm ẩn sản phẩm, giới hạn/khóa tài khoản, yêu cầu bồi thường, cấn trừ tiền hoặc cung cấp thông tin cho cơ quan có thẩm quyền. | 0.5926 | Có | Có. Người bán vi phạm quy định đăng bán có thể bị Shopee xử lý bằng nhiều biện pháp, bao gồm xóa hoặc khóa sản phẩm, giới hạn/khóa tài khoản, yêu cầu bồi thường, cấn trừ tiền, khóa rút tiền hoặc chuyển thông tin cho cơ quan có thẩm quyền. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Điều tôi rút ra rõ nhất là chất lượng retrieval không chỉ phụ thuộc embedding mà còn phụ thuộc cách chunk và độ sạch của dữ liệu. Một số câu hỏi như thời gian hoàn tiền trả về đúng nhóm tài liệu nhưng chưa có câu trả lời cụ thể ở top-1, cho thấy cần thiết kế benchmark query và gold answer bám sát nội dung thật trong corpus. Metadata như `customer_role` và `category` cũng hữu ích để lọc bớt nhiễu khi câu hỏi đã biết rõ thuộc nhóm người mua, người bán hoặc chính sách cụ thể.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 9 / 10 |
| **Tổng phần cá nhân** | **59 / 60** |
