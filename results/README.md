# Kết quả thí nghiệm

Thư mục này nằm ở gốc repo theo `SUBMISSION.md`. Chạy `python -m src.run` trong `starter/` để tạo lại các file sau từ manifest và benchmark đã chốt:

- `metrics.json`: model, cấu hình A/B/C, số chunk, token/ký tự, thời gian và chỉ số dev/test.
- `traces_dev.jsonl`, `traces_test.jsonl`: mỗi dòng là một câu hỏi × chiến lược với top-3 đầy đủ (ID, text, score, metadata, evidence hit).
- `manual_review_template.json`: 10 vị trí cố định trên nguồn cho mỗi chiến lược và 5 câu test × 3 chiến lược; các nhãn thủ công để trống để người chấm đối chiếu PDF.

Các file `*.log` chỉ là log chạy local và bị Git bỏ qua. Không sửa bộ test hoặc tham số dựa vào kết quả test; cấu hình được chọn từ dev trước khi chạy test.
