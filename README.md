# Day 06 · Data Ingestion Engineering

**Bài làm cá nhân:** Trần Quang Nam · 2A202603516 · L3A

Pipeline đọc hai bản dịch tiếng Việt của khung năng lực AI UNESCO, tạo embedding, lưu trên PostgreSQL với pgvector và so sánh ba cách truy xuất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Dữ liệu và cách chạy

- [Manifest](data/manifest.json) chọn 134 trang nội dung từ hai PDF, ghi nguồn, giấy phép, số trang và số ký tự. PDF nằm local trong `data/corpus/`; [script tải](scripts/fetch_corpus.py) lấy đúng bản từ Zenodo và kiểm tra hash.
- [Benchmark](benchmark/questions.json) có 20 câu hỏi: 15 dev, 5 test. Ba câu có filter `audience`.
- Mã nguồn nằm trong [`starter/src/`](starter/src/). A chia 500 ký tự, overlap 50; B chia theo đoạn tối đa 800 ký tự; C dùng chunk của B và lọc `audience` khi câu hỏi cung cấp đối tượng.
- Embedding dùng `google/embeddinggemma-2` 768 chiều; vector lưu trong bảng `public.ingestion_chunks` của PostgreSQL local.

Trên Windows PowerShell, chạy từ thư mục gốc repo:

```powershell
cd .\starter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

Máy có NVIDIA GPU có thể cài PyTorch CUDA sau `requirements.txt` và trước `python -m src.run`:

```powershell
python -m pip install --no-deps --force-reinstall torch==2.14.1+cu130 torchvision==0.29.1+cu130 --index-url https://download.pytorch.org/whl/cu130
```

Sau khi cài đặt, chạy pipeline từ thư mục `starter/`:

```powershell
python ..\scripts\fetch_corpus.py
python ..\scripts\validate_benchmark.py
python -m src.run
python ..\scripts\audit_metadata.py
```

Không có CUDA, pipeline dùng CPU và chạy chậm hơn. `.env`, môi trường ảo, model cache và PDF không được đưa lên Git. Xem [RUN_LAB.md](docs/RUN_LAB.md) để biết cách tạo lại manifest và đường dẫn kết quả.

Kết quả gồm [metrics](results/metrics.json), [trace dev](results/traces_dev.jsonl), [trace test](results/traces_test.jsonl), [audit từng trường hợp](results/manual_audit.json), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và [báo cáo cá nhân](report/individual/2A202603516_TranQuangNam.md).

## Pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Mỗi chunk giữ ID tài liệu, đường dẫn nguồn, trang vật lý và `audience`. Hai PDF chỉ được tải về máy để chạy pipeline; repo nộp manifest và script lấy dữ liệu.

## So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Ba cấu hình dùng cùng corpus, model và bộ câu hỏi. Kết quả dev quyết định cấu hình được chọn trước khi chạy test. Mỗi câu có đáp án, đoạn bằng chứng và trang nguồn theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## File bài nộp

1. [Thông tin học viên](STUDENT.md), [manifest](data/manifest.json), [benchmark](benchmark/questions.json) và mã nguồn trong `starter/src/`.
2. [Nhật ký thí nghiệm](artifacts/experiment_log.csv), [trace và metrics](results/) cùng [audit](results/manual_audit.json).
3. [Báo cáo cá nhân](report/individual/2A202603516_TranQuangNam.md) và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| PostgreSQL + pgvector và lệnh chạy chi tiết | [docs/RUN_LAB.md](docs/RUN_LAB.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) là file mẫu của đề. Corpus thực tế và quy tắc tính trang nằm trong [data/manifest.json](data/manifest.json).
