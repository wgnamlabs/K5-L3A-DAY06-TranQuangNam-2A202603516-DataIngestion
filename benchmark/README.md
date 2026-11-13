# Benchmark cho hai khung năng lực AI của UNESCO

`questions.json` gồm **20 câu hỏi tiếng Việt** trên cùng corpus hai bản dịch của UNESCO: 10 câu về khung cho giáo viên và 10 câu về khung cho học sinh. Bộ câu hỏi được chia **15 dev / 5 test trước khi chạy thử retrieval**. Bản giáo viên có 8 dev và 2 test; bản học sinh có 7 dev và 3 test. Có câu hỏi trực tiếp, diễn đạt lại, điều kiện và ngoại lệ. `type` là nhãn phục vụ phân tích lỗi, không được đưa vào truy vấn.

Mỗi câu ghi `id`, `split`, `question`, `expected_answer`, `gold_source_id`, `gold_page` và đoạn `evidence_quote` đã đối chiếu với PDF. `gold_page` là **số trang vật lý bắt đầu từ 1**, tương ứng với `data/manifest.json`. Đoạn evidence được kiểm tra trên đúng trang sau khi chuẩn hóa Unicode NFKC và gộp khoảng trắng. Một số bảng PDF có thể đổi thứ tự chữ khi trích xuất; các câu hỏi đã ưu tiên đoạn văn đọc được.

Ba câu kiểm tra metadata filter là `q02`, `q11` (dev) và `q18` (test). Trường `audience` có giá trị `teachers` hoặc `students`, dựa trên nhan đề tài liệu. Cả ba câu đều nêu rõ đối tượng trước khi truy xuất. Các câu khác không có filter, kể cả khi chạy cấu hình C. Không dùng `gold_source_id`, `gold_page` hoặc đáp án để tạo filter hay sửa câu truy vấn.

Chạy lệnh sau từ thư mục gốc repo để kiểm tra SHA-256 của PDF, split, filter và sự tồn tại của từng evidence trên trang gold:

```powershell
.\starter\.venv\Scripts\python.exe .\scripts\validate_benchmark.py
```

Lệnh này xác minh vị trí đoạn trích, không thay cho kiểm tra thủ công ý nghĩa đáp án hoặc bằng chứng tương đương. Nếu có nhiều nguồn/trang hỗ trợ đúng một đáp án, cần bổ sung tất cả nguồn hợp lệ trong gold và cho phép một trong số đó được tính hit. Hai bản khung có chủ đề liên quan nên phải lưu ý khả năng trùng ý khi chấm.

**Tiêu chí chọn cấu hình được chốt trước khi xem test:** ưu tiên Evidence Hit@3 trên dev, tiếp đến Hit@1 trên dev, rồi thời gian/chi phí ingest nếu hai chỉ số truy xuất bằng nhau. Chỉ đánh giá test sau khi cố định cấu hình. Nếu xem test để chỉnh pipeline, phải ghi rõ và không báo kết quả đó như một holdout độc lập.
