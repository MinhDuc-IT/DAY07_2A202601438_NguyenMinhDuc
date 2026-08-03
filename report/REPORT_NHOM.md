# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Chậm Deadline  
**Thành viên:**

- Nguyễn Minh Đức — 2A202601438 (Leader)
- Ngô Huy Hoàn — 2A202601925
- Ngô Văn Kiệt — 2A202601524
- Phạm Văn Vinh — 2A202601988

**Ngày:** 2026-08-03

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Phạm vi bộ tài liệu (Scope)

**Chủ đề (cố định theo lớp K4):** Chính sách thương mại điện tử / hỗ trợ khách hàng (thanh toán, đổi trả, giao hàng, quyền riêng tư, điều kiện người bán…).

**Phạm vi cụ thể nhóm tập trung:**

> Chính sách trả hàng/hoàn tiền, vận chuyển, đăng bán (seller), thanh toán FAQ và bảo mật thông tin khách hàng trên Shopee + Tiki.

### Danh sách tài liệu (Data Inventory)


| #   | Tên tài liệu                              | Nguồn (Source URL)                                                                             | Ngày lấy / Phiên bản    | Số ký tự | Metadata đã gán                                                                                                                                  |
| --- | ----------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Shopee Đảm Bảo là gì                      | [https://help.shopee.vn/portal/4/article/79314](https://help.shopee.vn/portal/4/article/79314) | 2026-08-03 / not-stated | 1344     | `doc_id`, `customer_role=buyer`, `category=buyer-protection`, `platform=shopee`, `language=vi`, `source_url`, `retrieved_at`, `document_version` |
| 2   | Tổng hợp FAQ thanh toán Shopee            | [https://help.shopee.vn/portal/4/article/79526](https://help.shopee.vn/portal/4/article/79526) | 2026-08-03 / not-stated | 3794     | `customer_role=buyer`, `category=payment-faq`, `platform=shopee`, …                                                                              |
| 3   | Chính sách bảo mật Shopee                 | [https://help.shopee.vn/portal/4/article/77244](https://help.shopee.vn/portal/4/article/77244) | 2026-08-03 / not-stated | 43112    | `customer_role=both`, `category=privacy-policy`, `platform=shopee`, …                                                                            |
| 4   | Chính sách trả hàng và hoàn tiền Shopee   | [https://help.shopee.vn/portal/4/article/77251](https://help.shopee.vn/portal/4/article/77251) | 2026-08-03 / not-stated | 19616    | `customer_role=buyer`, `category=returns-policy`, `platform=shopee`, …                                                                           |
| 5   | Quy định đăng bán sản phẩm trên Shopee    | [https://help.shopee.vn/portal/4/article/77246](https://help.shopee.vn/portal/4/article/77246) | 2026-08-03 / not-stated | 21532    | `customer_role=seller`, `category=seller-listing`, `platform=shopee`, …                                                                          |
| 6   | Chính sách vận chuyển Shopee              | [https://help.shopee.vn/portal/4/article/77250](https://help.shopee.vn/portal/4/article/77250) | 2026-08-03 / not-stated | 24561    | `customer_role=both`, `category=shipping-policy`, `platform=shopee`, …                                                                           |
| 7   | Chính sách bảo mật thông tin cá nhân Tiki | [https://tiki.vn/thong-tin/privacy-policy](https://tiki.vn/thong-tin/privacy-policy)           | 2026-08-03 / not-stated | 9487     | `customer_role=both`, `category=privacy-policy`, `platform=tiki`, …                                                                              |


**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**

- Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)


| Trường metadata    | Kiểu   | Ví dụ giá trị                       | Tại sao hữu ích cho truy xuất (retrieval)?                      |
| ------------------ | ------ | ----------------------------------- | --------------------------------------------------------------- |
| `doc_id`           | string | `shopee-returns-refunds`            | Định danh ổn định; dùng khi `delete_document` / truy vết chunk. |
| `customer_role`    | string | `buyer` / `seller` / `both`         | Lọc theo đối tượng (yêu cầu K4); giảm nhiễu buyer↔seller.       |
| `category`         | string | `returns-policy`, `shipping-policy` | Lọc theo chủ đề chính sách.                                     |
| `platform`         | string | `shopee`, `tiki`                    | Tách nguồn sàn khi từ khóa trùng (vd. bảo mật).                 |
| `language`         | string | `vi`                                | Hữu ích nếu corpus đa ngữ.                                      |
| `source_url`       | string | URL gốc                             | Trích dẫn / kiểm chứng.                                         |
| `retrieved_at`     | string | `2026-08-03`                        | Theo dõi độ mới của dữ liệu.                                    |
| `document_version` | string | `not-stated`                        | Ghi phiên bản/ngày hiệu lực nếu nguồn có nêu.                   |


---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2–3 tài liệu (ví dụ `shopee-returns-refunds`, `shopee-shipping-policy`):


| Tài liệu           | Chiến lược (Strategy)            | Số lượng Chunk        | Độ dài trung bình | Giữ được ngữ cảnh không?                    |
| ------------------ | -------------------------------- | --------------------- | ----------------- | ------------------------------------------- |
| returns / shipping | FixedSizeChunker (`fixed_size`)  | nhiều                 | ~chunk_size       | Không ổn định (dễ cắt ngang câu/điều khoản) |
| returns / shipping | SentenceChunker (`by_sentences`) | nhiều hơn             | ngắn–trung bình   | Có ở mức câu; dễ mất ngữ cảnh đoạn          |
| returns / shipping | RecursiveChunker (`recursive`)   | ít hơn Fixed/Sentence | gần chunk_size    | Tốt hơn (ưu tiên `\n\n`, `\n`, `.` )        |


> *Ghi chú:* số liệu chi tiết từng máy có thể lệch nhẹ theo tham số; nhóm thống nhất so sánh định tính + top-3 trên cùng 5 câu hỏi.

### Chiến lược của từng thành viên

**Thành viên 1 — Nguyễn Minh Đức (2A202601438)**

- **Loại chiến lược:** RecursiveChunker (`chunk_size=500`)
- **Mô tả & lý do chọn cho chủ đề này:** Chính sách TMĐT có cấu trúc đoạn/điều khoản; cắt đệ quy theo separator giúp giữ khối ý hoàn chỉnh hơn FixedSize, phù hợp câu hỏi cần ngữ cảnh (đổi trả, vận chuyển, xử phạt seller).

**Thành viên 2 — Ngô Huy Hoàn (2A202601925)**

- **Loại chiến lược:** SentenceChunker
- **Mô tả & lý do chọn:** Cắt theo ranh giới câu để tránh đứt giữa chừng; phù hợp FAQ / câu hỏi ngắn cần khớp một ý cụ thể.

**Thành viên 3 — Ngô Văn Kiệt (2A202601524)**

- **Loại chiến lược:** FixedSizeChunker (`chunk_size=300`, `overlap=50`)
- **Mô tả & lý do chọn:** Độ dài ổn định, dễ kiểm soát token; overlap giúp giảm mất thông tin ở biên chunk.

**Thành viên 4 — Phạm Văn Vinh (2A202601988)**

- **Loại chiến lược:** Custom — chia theo tiêu đề / cặp FAQ (heading / FAQ-pair) khi tài liệu có cấu trúc mục lục câu hỏi
- **Mô tả & lý do chọn:** K4 khuyến khích thử chunk theo heading/FAQ; hữu ích với `shopee-payment-faq` và các mục đánh số trong chính sách.

### So Sánh Giữa Các Thành Viên


| Thành viên      | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh                                        | Điểm yếu                                                             |
| --------------- | --------------------- | -------------------- | ------------------------------------------------ | -------------------------------------------------------------------- |
| Nguyễn Minh Đức | RecursiveChunker      | 8                    | Giữ đoạn/điều khoản; top-3 ổn trên corpus 7 file | Top-1 đôi khi là điều kiện/ngoại lệ thay vì câu trả lời trực tiếp    |
| Ngô Huy Hoàn    | SentenceChunker       | 7                    | Khớp câu ngắn / FAQ tốt                          | Dễ mất ngữ cảnh bao quát                                             |
| Ngô Văn Kiệt    | FixedSizeChunker      | 6–7                  | Đều kích thước, có overlap                       | Vẫn cắt ngang câu/ý                                                  |
| Phạm Văn Vinh   | Heading / FAQ-pair    | 7–8                  | Tốt với FAQ & mục có tiêu đề                     | Phụ thuộc cấu trúc tài liệu; tài liệu “điều khoản liền mạch” kém hơn |


**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**

> Với corpus chính sách dài (returns, shipping, seller-listing), **RecursiveChunker** thường cân bằng tốt hơn giữa độ dài chunk và ranh giới ngữ nghĩa. Sentence phù hợp câu hỏi cực ngắn; Fixed dễ cắt đứt điều khoản; custom heading/FAQ mạnh khi nguồn có cấu trúc mục lục rõ.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.


| #   | Câu hỏi (Query)                                  | Câu trả lời chuẩn (Gold Answer)                                                                                                                                                                           | Chunk nào chứa thông tin?                                                      |
| --- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 1   | Làm sao để trả hàng trên Shopee?                 | Người mua gửi yêu cầu Trả hàng/Hoàn tiền trên Shopee trong thời hạn quy định (thường 15 ngày kể từ giao thành công theo Shopee Đảm Bảo / chính sách trả hàng).                                            | `shopee-returns-refunds`, `shopee-buyer-protection`                            |
| 2   | Thời gian xử lý hoàn tiền của Shopee là bao lâu? | Thời hạn/cách nhận hoàn tiền được quy định trong chính sách trả hàng & bảo vệ người mua (ví dụ phản hồi/xử lý theo quy trình Shopee; hoàn về phương thức thanh toán hoặc Số dư TK Shopee tùy trường hợp). | `shopee-returns-refunds`, `shopee-buyer-protection`                            |
| 3   | Tiki thu thập thông tin khách hàng để làm gì?    | Theo chính sách bảo mật Tiki: phục vụ giao dịch/mua sắm, vận hành dịch vụ và các mục đích được nêu trong chính sách (cần trích đúng mục “Mục đích thu thập” trên tài liệu Tiki).                          | `tiki-privacy-policy` — nên kèm `metadata_filter={"platform":"tiki"}`          |
| 4   | Hàng dễ vỡ có được vận chuyển không?             | Chính sách vận chuyển Shopee nêu danh mục hàng dễ vỡ/dễ hư hại và quy định đóng gói/xử lý khi vận chuyển; không phải mọi hàng đều được vận chuyển bình thường nếu thuộc nhóm hạn chế/đặc biệt.            | `shopee-shipping-policy`                                                       |
| 5   | Đăng bán hàng giả có bị phạt không?              | Có — người bán vi phạm quy định đăng bán (gồm hàng giả/nhái tùy mức độ) có thể bị xóa/khóa/ẩn sản phẩm và các biện pháp xử lý khác theo quy định Shopee.                                                  | `shopee-seller-listing` — nên kèm `metadata_filter={"customer_role":"seller"}` |


### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).


| #   | Câu hỏi                | Chiến lược tốt nhất cho câu này               | Có chunk liên quan trong top-3? | Ghi chú                                                                                                               |
| --- | ---------------------- | --------------------------------------------- | ------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| 1   | Làm sao để trả hàng... | RecursiveChunker                              | Có                              | Doc đúng `shopee-returns-refunds`; top-1 có thể lệch sang điều kiện liên kết phương thức hoàn tiền. Score ví dụ ~0.69 |
| 2   | Thời gian hoàn tiền... | RecursiveChunker                              | Có (một phần)                   | Dễ trả về chunk “hoàn tiền khi đơn chưa chuẩn bị” thay vì timeline xử lý chi tiết. Score ví dụ ~0.64                  |
| 3   | Tiki thu thập...       | Sentence / Recursive + filter `platform=tiki` | Có                              | Filter metadata quan trọng để tránh lẫn privacy Shopee. Score ví dụ ~0.68                                             |
| 4   | Hàng dễ vỡ...          | RecursiveChunker                              | Có                              | Top-3 có chunk danh mục dễ vỡ trong `shopee-shipping-policy`. Score ví dụ ~0.61                                       |
| 5   | Bán hàng giả...        | Recursive + filter `customer_role=seller`     | Có                              | Filter seller giúp tập trung `shopee-seller-listing`. Score ví dụ ~0.59                                               |


**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**

> Có — đặc biệt câu **3** (`platform=tiki`) để tránh lẫn chính sách bảo mật Shopee, và câu **5** (`customer_role=seller`) để ưu tiên quy định đăng bán thay vì tài liệu buyer.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**

> - Embedding thật (`text-embedding-3-small`) khác hẳn mock khi so sánh chiến lược chunking trên tiếng Việt.
> - Metadata K4 (`customer_role`, `platform`) cải thiện precision trên câu hỏi đa sàn / đa vai trò.
> - Top-1 score cao chưa đồng nghĩa “đúng gold answer” — cần đọc top-3 và grounding.

**Bài học rút ra khi so sánh trong nhóm:**

> Cùng corpus 7 tài liệu, Recursive thường ổn cho điều khoản dài; Sentence/FAQ tốt cho câu hỏi ngắn; Fixed đơn giản nhưng dễ cắt ý. Ít nhất một thành viên thử heading/FAQ giúp nhóm thấy giới hạn của chunk “một kiểu cho mọi tài liệu”.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**

> Làm sạch thêm boilerplate UI khi crawl; bổ sung FAQ trả hàng đầy đủ nội dung (tránh trang mục lục); gắn `category`/`topic` mịn hơn; viết gold answer sát đoạn văn gốc từng file.

---

## Tự Đánh Giá (Phần Nhóm)


| Tiêu chí                                 | Điểm tự đánh giá |
| ---------------------------------------- | ---------------- |
| Lựa chọn tài liệu (Document Set Quality) | 9 / 10           |
| Thiết kế chiến lược (Strategy Design)    | 13 / 15          |
| Chất lượng truy xuất (Retrieval Quality) | 8 / 10           |
| Thuyết trình (Demo)                      | 4 / 5            |
| **Tổng phần nhóm**                       | **34 / 40**      |


