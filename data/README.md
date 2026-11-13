# Bộ dữ liệu UNESCO về năng lực AI trong giáo dục

Corpus gồm hai bản dịch tiếng Việt của Lê Trung Nghĩa, lưu trong `data/corpus/` tính từ thư mục gốc repo:

- `corpus/391104eng_Vi-03022025.pdf`: *Khung năng lực AI cho giáo viên*, bản dịch hoàn thành ngày 03/02/2025. [Bản dịch trên Zenodo](https://zenodo.org/records/14897590); [bản gốc UNESCO năm 2024](https://unesdoc.unesco.org/ark:/48223/pf0000391104).
- `corpus/391105eng_Vi-10022025.pdf`: *Khung năng lực AI cho học sinh*, bản dịch hoàn thành ngày 10/02/2025. [Bản dịch trên Zenodo](https://zenodo.org/records/14903158); [bản gốc UNESCO năm 2024](https://unesdoc.unesco.org/ark:/48223/pf0000391105).

Mã MD5 của hai PDF tại máy khớp bản v1 trên Zenodo. `manifest.json` ghi thêm SHA-256 để nhận diện chính xác bản local đã dùng. Trường `source_path_or_url` là đường dẫn tương đối tính từ thư mục gốc repo.

## Quy tắc tính trang

Hai PDF có tổng cộng **167 trang vật lý**. Corpus tính **134 trang nội dung hữu ích**: 57 trang của bản giáo viên (trang vật lý 14–70) và 77 trang của bản học sinh (trang vật lý 14–90). Không tính bìa, giới thiệu nhà xuất bản, thông tin xuất bản, tóm tắt đầu tài liệu, lời nói đầu, lời thừa nhận, mục lục, danh sách bảng/từ viết tắt, trang phân cách, các trang chỉ có tài liệu tham khảo, chú giải cuối tài liệu và bìa sau. Mỗi trang vật lý đều có ID, số ký tự sau chuẩn hóa, quyết định tính/loại và lý do loại trong `manifest.json`.

Số ký tự được đo từ text trích xuất bằng `pypdf` sau khi chuẩn hóa Unicode NFKC, bỏ đường kẻ và đầu/chân trang lặp lại, rồi gộp khoảng trắng. Các trang được tính đều trích xuất được text; chưa cần OCR. Các bảng dàn nhiều cột có thể không giữ đúng thứ tự đọc khi trích text, nên cần kiểm tra trực quan các đoạn dùng làm evidence. ID trang dùng số trang vật lý bắt đầu từ 1, ví dụ `unesco-ai-cft-vi-2025:p014`. Dùng số này cho `DocumentPage.page`, metadata chunk và `gold_page` trong benchmark.

Tạo lại manifest từ thư mục gốc repo:

```powershell
.\starter\.venv\Scripts\python.exe .\scripts\build_manifest.py
```

## Nguồn, quyền sử dụng và metadata lọc

Trang 3 của **cả hai PDF** ghi văn bản được phát hành theo giấy phép **CC BY-SA 3.0 IGO**. Khi sử dụng hoặc phân phối, cần ghi công UNESCO, tác phẩm gốc và người dịch; tác phẩm phái sinh phải tuân thủ điều kiện chia sẻ tương tự. Hình ảnh được đánh dấu sao (*) không thuộc giấy phép này; [điều khoản truy cập mở của UNESCO](https://www.unesco.org/en/open-access/cc-sa) cũng nêu giới hạn đối với hình ảnh, biểu đồ và tài liệu không rõ quyền. Benchmark chỉ trích dẫn text. Manifest ghi nguồn và giấy phép riêng cho từng PDF.

Trường metadata `audience` có hai giá trị `teachers` và `students`, lấy trực tiếp từ nhan đề tài liệu. Chỉ áp dụng filter khi câu hỏi hoặc ngữ cảnh đã nói rõ đang hỏi khung cho giáo viên hay học sinh **trước khi truy xuất**; không tạo filter từ đáp án hoặc trang gold. Hai bản có chủ đề liên quan nên một số câu có thể có bằng chứng tương đương ở nhiều nơi; việc chấm cần xem xét các nguồn hợp lệ đã ghi trong benchmark.
