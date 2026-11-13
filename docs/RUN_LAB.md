# Cách chạy lại bài lab cá nhân

File này ghi cấu hình và lệnh chạy lại bài làm. Tiêu chí chấm và quy định nộp bài vẫn theo `GUIDE.md` và `SUBMISSION.md` ở gốc repo.

## Vị trí file nộp

- `data/corpus/`: hai PDF tiếng Việt về khung năng lực AI cho giáo viên và học sinh.
- PDF chỉ lưu local; repo nộp manifest và script tải vì giấy phép văn bản không bao phủ mọi hình ảnh trong PDF.
- `data/manifest.json`: nguồn, quyền, trang được tính và metadata `audience`.
- `benchmark/questions.json`: 20 câu hỏi và gold evidence đã chốt.
- `scripts/build_manifest.py`, `scripts/validate_benchmark.py`: tạo lại manifest và kiểm tra benchmark.
- `starter/src/`: mã pipeline; `starter/requirements.txt`: dependencies.
- `results/`: metrics, trace dev/test, kiểm tra metadata và bản audit đã chấm từng trường hợp.
- `artifacts/experiment_log.csv`: cấu hình và kết quả A/B/C.
- `report/individual/2A202603516_TranQuangNam.md`: báo cáo cá nhân theo mẫu.

## Setup trên Windows

Từ thư mục gốc repo, dùng môi trường ảo của `starter/`:

```powershell
cd .\starter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

Nếu máy có NVIDIA GPU, cài PyTorch CUDA sau lệnh `pip install -r requirements.txt`, trước khi chạy pipeline:

```powershell
python -m pip install --no-deps --force-reinstall torch==2.14.1+cu130 torchvision==0.29.1+cu130 --index-url https://download.pytorch.org/whl/cu130
```

Kiểm tra thiết bị sau khi cài PyTorch:

```powershell
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

CUDA in `True` sẽ dùng GPU; `False` dùng CPU `float32` và chạy chậm hơn. `starter/.env` chứa kết nối PostgreSQL local, không đưa vào repo. Model `google/embeddinggemma-2` (revision `f9972ac22e696a105c482202646979e33e4b5a1e`) tự tải lần đầu vào `starter/.model_cache/`; cần đủ dung lượng trống.

## Kiểm tra dữ liệu và chạy pipeline

Từ `starter/`:

```powershell
python ..\scripts\fetch_corpus.py
python ..\scripts\validate_benchmark.py
python -m src.run
python ..\scripts\audit_metadata.py
python ..\scripts\filter_diagnostic.py
```

Chỉ tạo lại manifest nếu corpus thay đổi; lúc đó cần kiểm tra lại gold và không dùng kết quả test cũ như holdout độc lập:

```powershell
python ..\scripts\build_manifest.py
```

Script nạp đúng 134 trang nội dung. A dùng chunk 500 ký tự, overlap 50; B dùng đoạn tối đa 800 ký tự; C dùng vector B và filter `audience` khi câu hỏi có filter. Mọi cấu hình dùng EmbeddingGemma 2 local 768 chiều và pgvector exact cosine. Chọn cấu hình bằng dev trước khi truy vấn test.

Kết quả xuất ở `../results/metrics.json`, `../results/traces_dev.jsonl`, `../results/traces_test.jsonl`, `../results/manual_audit.json`, `../results/metadata_audit.json` và `../results/filter_diagnostic_q05.json`. Bảng PostgreSQL là `public.ingestion_chunks`; chỉ A và B có dòng riêng vì C dùng lại B. `manual_audit.json` có 30 nhãn coherence, 15 nhãn grounding, kiểm tra metadata 45 hit và lý do từng trường hợp. Codex là người chấm bằng cách đọc trực tiếp PDF và trace; phương pháp và nguy cơ thiên lệch được ghi trong file audit. Chạy lại pipeline giữ bản audit đã hoàn thành nếu mẫu chunk và top-3 không đổi; nếu chúng đổi, lệnh báo lỗi để tránh dùng nhãn cũ. Filter diagnostic là thử riêng sau thí nghiệm trên câu dev, không thay benchmark hoặc điểm test.
