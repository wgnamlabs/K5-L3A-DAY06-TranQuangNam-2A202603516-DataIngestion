# Kết quả thí nghiệm

Thư mục này nằm ở gốc repo theo `SUBMISSION.md`. Chạy `python -m src.run` trong `starter/` để tạo lại các file sau từ manifest và benchmark đã chốt:

- `metrics.json`: model, cấu hình A/B/C, số chunk, token/ký tự, thời gian và chỉ số dev/test.
- `traces_dev.jsonl`, `traces_test.jsonl`: mỗi dòng là một câu hỏi × chiến lược với top-3 đầy đủ (ID, text, score, metadata, evidence hit).
- `manual_audit.json`: 10 vị trí cố định trên nguồn cho mỗi chiến lược và 5 câu test × 3 chiến lược, có đầy đủ nhãn 0–2, lý do, kiểm tra metadata và nhận xét gold của 20 câu. Người chấm được ghi rõ là Codex. Pipeline giữ nguyên bản audit hoàn tất khi chạy lại cùng dữ liệu và trace.
- `metadata_audit.json`: kiểm tra kỹ thuật 45 hit test với PDF đã xác minh hash.
- `filter_diagnostic_q05.json`: thử riêng trên câu dev `q05` với ngữ cảnh `audience=teachers` được cung cấp trước truy xuất; không tính vào benchmark hay chọn cấu hình.

Các file `*.log` chỉ là log chạy local và bị Git bỏ qua. Không sửa bộ test hoặc tham số dựa vào kết quả test; cấu hình được chọn từ dev trước khi chạy test.
