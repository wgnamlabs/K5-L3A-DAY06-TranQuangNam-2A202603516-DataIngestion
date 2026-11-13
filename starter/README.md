# Starter · PostgreSQL + pgvector

Thư mục này chứa pipeline đã hoàn thành và PostgreSQL + pgvector chạy local bằng Docker Compose. Lệnh chạy đầy đủ và đường dẫn dữ liệu nằm trong [README ở gốc repo](../README.md) và [RUN_LAB.md](../docs/RUN_LAB.md).

## Cấu trúc

```text
starter/
├── docker-compose.yml     # PostgreSQL 16 + pgvector, chỉ mở cổng local
├── init.sql               # bật extension khi tạo database mới
├── requirements.txt       # thư viện PDF, embedding, PostgreSQL
├── .env.example           # cấu hình mẫu; copy thành .env
├── scripts/check_setup.py # kiểm tra kết nối và extension (đã chạy được)
├── src/
│   ├── models.py          # cấu trúc trang và chunk
│   ├── ingestion.py       # đọc và chuẩn hóa PDF
│   ├── chunking.py        # hai cách chia chunk
│   ├── embeddings.py      # EmbeddingGemma 2
│   ├── store.py           # pgvector và filter audience
│   ├── evaluation.py      # Hit@1 và Evidence Hit@3
│   └── run.py             # pipeline và trace dev/test
../data/                    # corpus local và manifest
../results/                 # metrics, trace và audit
```

## 1. Cài và kiểm tra database

Cần Docker Desktop hoặc Docker Engine + Compose, Python và mạng để tải image/dependencies lần đầu. Bài làm đã chạy trên Python 3.10.11 ở Windows. Các lệnh sau chạy từ thư mục `starter/`:

```bash
cd starter
python3 -m venv .venv
```

Kích hoạt `.venv`: macOS/Linux dùng `source .venv/bin/activate`; Windows PowerShell dùng `.venv\Scripts\Activate.ps1`. Sau đó:

```bash
python -m pip install -r requirements.txt
# macOS/Linux: cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

Kỳ vọng: hiện tên database, phiên bản PostgreSQL và pgvector, sau đó `Setup OK`. Đây **chỉ là kiểm tra hạ tầng**, không phải kết quả benchmark. Docker dùng cổng `127.0.0.1:55433` và mật khẩu cố định **chỉ dùng local cho lab**; nếu cổng bận, sửa đồng thời port trong `docker-compose.yml` và `DATABASE_URL` trong `.env`. `init.sql` chỉ chạy khi volume mới được tạo; nếu database sẵn có chưa bật extension, xem log Docker và kiểm tra cấu hình thay vì xóa volume chứa dữ liệu.

Dừng container nhưng giữ dữ liệu:

```bash
docker compose -p day6_student_starter stop
```

## 2. Embedding model

Pipeline dùng `google/embeddinggemma-2` local, vector 768 chiều, cùng model cho cả ba cấu hình và câu hỏi. Không cần API key. Nếu có NVIDIA GPU, dùng bản PyTorch CUDA theo [RUN_LAB.md](../docs/RUN_LAB.md); máy không có CUDA chạy trên CPU.

## 3. Chạy pipeline

Từ thư mục `starter/`, sau khi cài môi trường và chạy Docker:

```powershell
python ..\scripts\fetch_corpus.py
python ..\scripts\validate_benchmark.py
python -m src.run
python ..\scripts\audit_metadata.py
```

PDF được lưu local tại `../data/corpus/`; manifest, benchmark và kết quả nằm ở thư mục gốc repo. Xem [RUN_LAB.md](../docs/RUN_LAB.md) để biết cấu hình, lệnh chạy lại và giới hạn của kết quả.
