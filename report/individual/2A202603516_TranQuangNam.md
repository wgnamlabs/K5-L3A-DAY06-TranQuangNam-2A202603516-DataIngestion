# Báo cáo cá nhân — Day 6

**Học viên:** Trần Quang Nam · **MSSV:** 2A202603516 · **Lớp:** L3A

**Repo:** [K5-L3A-DAY06-TranQuangNam-2A202603516-DataIngestion](https://github.com/wgnamlabs/K5-L3A-DAY06-TranQuangNam-2A202603516-DataIngestion)

**Lần chạy được báo cáo:** 13/11/2026 khoảng 19:13 (UTC+07), trên Windows với RTX 5060 Laptop GPU.

## Dữ liệu và pipeline

- **Chủ đề và nguồn:** năng lực AI trong giáo dục, gồm hai bản dịch tiếng Việt của khung UNESCO dành cho [giáo viên](https://zenodo.org/records/14897590) và [học sinh](https://zenodo.org/records/14903158). Hai file có **167 trang vật lý**, tính **134 trang nội dung**: giáo viên 57 trang (vật lý 14–70), học sinh 77 trang (14–90). Bìa, mục lục, phần đầu, trang chỉ có tài liệu tham khảo và bìa sau không được tính. [Manifest](../../data/manifest.json) ghi ID, quyết định tính/loại và số ký tự của từng trang.
- **Quyền và cách cung cấp corpus:** trang 3 của PDF ghi văn bản theo CC BY-SA 3.0 IGO; Zenodo hiển thị metadata giấy phép CC BY-SA 4.0. Hình ảnh đánh dấu sao trong PDF không nằm trong giấy phép văn bản. Vì vậy repo chỉ nộp manifest, URL nguồn và [script tải có đối chiếu MD5/SHA-256](../../scripts/fetch_corpus.py); PDF được giữ local. Khi dùng nội dung cần ghi công UNESCO, tác phẩm gốc và người dịch Lê Trung Nghĩa. Chi tiết ở [data/README.md](../../data/README.md).
- **Đọc và chuẩn hóa:** `pypdf` trích text theo trang vật lý, chuẩn hóa Unicode NFKC, bỏ đường kẻ và đầu/chân trang lặp, nối dòng PDF và giữ ranh giới đoạn/heading. Cả 134 trang được chọn đều trích được text, chưa cần OCR. Bảng nhiều cột có thể bị đổi thứ tự đọc; đây là giới hạn của phép trích text. SHA-256 của file được kiểm tra trước khi nạp. Không có trang được chọn bị rỗng hay lỗi trong lần chạy này.
- **Model và store:** `google/embeddinggemma-2`, revision `f9972ac22e696a105c482202646979e33e4b5a1e`, vector **768 chiều**, chạy local bằng Sentence Transformers 6.3.0 / Transformers 5.20.2 / PyTorch 2.14.1+cu130, CUDA `bfloat16`. Document được mã hóa với `title: ... | text: ...`; query dùng prompt `QuestionAnswering`; vector chuẩn hóa L2. PostgreSQL **16.16** + pgvector **0.8.7**, bảng `public.ingestion_chunks`, tìm kiếm exact cosine. Cả ba cấu hình dùng cùng model, store, corpus và benchmark. Chi phí API embedding **0**; điện năng/GPU và mạng tải model không được quy thành tiền.
- **Metadata:** mỗi chunk có `document_id`, `source`, `page` vật lý, `page_id`, `title`, `version`, `source_sha256` và `audience`. Hai giá trị `audience=teachers|students` lấy từ nhan đề tài liệu. Trường này giúp lọc phạm vi khi câu hỏi nêu rõ đối tượng trước truy xuất; `source` và `page` giúp mở đúng PDF để kiểm chứng. Giới hạn: `audience` chỉ có hai giá trị ở cấp tài liệu, không phân biệt mục/chương trong một tài liệu.

## Cấu hình và benchmark

- **A:** cửa sổ cố định 500 ký tự, overlap 50; lưu 794 chunk, không filter.
- **B:** theo đoạn/heading, tối đa 800 ký tự; lưu 614 chunk, không filter.
- **C:** cùng đúng 614 chunk và vector của B; chỉ thêm filter SQL theo `audience` cho câu đã có filter. Không tạo index/vector riêng cho C.
- **Benchmark:** [20 câu hỏi và gold](../../benchmark/questions.json) được tách trước chạy thành **15 dev / 5 test**, có câu trực tiếp, diễn đạt lại, điều kiện và ngoại lệ. `q02`, `q11` (dev) và `q18` (test) có filter do câu hỏi cung cấp. [Validator](../../scripts/validate_benchmark.py) xác minh từng evidence nằm trên trang gold sau chuẩn hóa; [audit](../../results/manual_audit.json) ghi lý do đáp án được hỗ trợ cho cả 20 câu. Gold hiện có một đoạn chính cho mỗi câu; bằng chứng tương đương ở nơi khác có thể khiến chỉ số khớp nguyên văn đánh giá thấp kết quả.
- **Quy tắc chọn đã chốt trước test:** ưu tiên Evidence Hit@3 trên dev, tiếp đến Hit@1 trên dev, rồi thời gian ingest. Script chạy dev và ghi lựa chọn trước khi truy vấn test. B và C hòa cả hai chỉ số dev; do C dùng lại B nên không có chi phí ingest riêng, script chọn B theo thứ tự cấu hình. Điều này **không chứng minh B tốt hơn C**.

## Kết quả truy xuất

Một evidence hit đòi hỏi chunk thuộc nguồn/trang gold và chứa **đủ đoạn evidence** đã ghi sau chuẩn hóa khoảng trắng. Chỉ số này đo truy xuất bằng chứng, không đo độ đúng câu trả lời LLM.

| Cấu hình | Tập | Hit@1 | Evidence Hit@3 | Số chunk logic | Ingest (giây) | Chi phí API |
|---|---|---:|---:|---:|---:|---:|
| A | dev | 1/15 | 2/15 | 794 | 12,112 | 0 |
| A | test | 1/5 | 2/5 | 794 | 12,112 | 0 |
| B | dev | 2/15 | 5/15 | 614 | 7,808 | 0 |
| B | test | 2/5 | 3/5 | 614 | 7,808 | 0 |
| C | dev | 2/15 | 5/15 | 614 | 0 thêm (dùng B) | 0 |
| C | test | 2/5 | 3/5 | 614 | 0 thêm (dùng B) | 0 |

Thời gian ingest trên là lần chạy local đã có model cache, gồm tạo vector và upsert; không bao gồm tải model lần đầu. A xử lý 366.054 ký tự chunk / 106.658 token đầu vào model; B/C 332.501 ký tự / 94.507 token. Nạp lại cùng dữ liệu cho đúng 794 dòng A và 614 dòng B, checksum danh sách chunk ID không đổi; chunk cũ được loại khi thay snapshot của một cấu hình. Chi tiết trong [metrics.json](../../results/metrics.json), [trace dev](../../results/traces_dev.jsonl) và [trace test](../../results/traces_test.jsonl).

## Audit năm khía cạnh

**Cách chấm.** Mẫu coherence gồm 5 trang nội dung đầu của mỗi PDF, lấy vị trí giữa trang. Mỗi vị trí được đọc ở cả A, B và C. Điểm 0 khi ý chính bị cắt hoặc thiếu chủ thể; 1 khi chỉ hiểu được một phần; 2 khi chunk tự đủ ngữ cảnh. Với 5 câu test, mỗi hit trong top-3 được đối chiếu tên PDF, trang vật lý và `audience`. Grounding nhận điểm 0 khi không có bằng chứng, 1 khi bằng chứng liên quan nhưng thiếu điều kiện, 2 khi đủ để trả lời và truy nguồn. Mỗi nhãn có lý do; điểm similarity không dùng để chấm. Chi tiết nằm trong [manual_audit.json](../../results/manual_audit.json).

**Nguồn nhãn.** Codex đọc PDF và trace để gán nhãn. Việc đã biết gold và kết quả truy xuất có thể ảnh hưởng đến nhận định; đây là giới hạn của bản audit.

| Cấu hình | Coherence trung bình /2 (10 vị trí) | Metadata đúng/đủ trên test top-3 | Filter test tuân thủ | Grounding test: số nhãn 0/1/2; trung bình /2 |
|---|---:|---:|---:|---|
| A | 1,0 | 15/15 | 1/1 quan sát; không áp filter | 1/2/2; 1,2 |
| B | 1,9 | 15/15 | 1/1 quan sát; không áp filter | 1/1/3; 1,4 |
| C | 1,9 | 15/15 | 1/1 có áp filter | 1/1/3; 1,4 |

- **Coherence:** [30 nhãn và lý do từng vị trí](../../results/manual_audit.json). A thường mở/kết giữa từ hoặc câu nên hiểu được một phần. B/C giữ trọn ý ở 9/10 vị trí; riêng trang giáo viên 18 mở bằng đại từ “Họ” thiếu chủ thể trong chunk.
- **Metadata:** [45 bản ghi kiểm tra](../../results/metadata_audit.json) so sánh `source`, trang, `audience`, tiêu đề, phiên bản, hash và đoạn text với PDF SHA-256 đã xác minh. Nhan đề và số trang của 16 trang xuất hiện trong top-3 test cũng được xem trên bản PDF hiển thị. Cả 15 hit test của mỗi cấu hình đều khớp; từng hit có nhãn trong [bản audit](../../results/manual_audit.json).
- **Filter:** C áp filter cho 2/2 câu dev và 1/1 câu test có yêu cầu; cả ba top-3 đều đúng đối tượng. A/B tình cờ cũng trả đúng đối tượng ở ba câu đó dù không dùng filter, nên bộ benchmark đã chốt không cho thấy lợi ích định lượng của C. Trong [thử riêng sau thí nghiệm trên câu dev `q05`](../../results/filter_diagnostic_q05.json), ngữ cảnh người dùng cho biết đang xem khung giáo viên trước truy xuất: top-3 B không lọc có 1 chunk thuộc khung học sinh, còn cùng vector với SQL filter `audience=teachers` có 0 chunk sai đối tượng. Thử riêng này chứng minh cơ chế lọc có tác dụng trong tình huống đó; không được cộng vào chỉ số benchmark, không dùng để chọn B/C và không thay tập test.
- **Grounding:** [15 nhãn và lý do từng câu](../../results/manual_audit.json). `q18` cho thấy A chỉ có phần mô tả mức “Áp dụng” ở trang 26, B/C lấy được mục tiêu đầy đủ ở trang 44. Grounding cao hơn Evidence Hit@3 không phải điểm trả lời LLM; thang này xem cả bằng chứng liên quan nhưng chưa đủ.
- **Tác động chiến lược:** A→B giảm 180 chunk (22,7%), giảm khoảng 11,4% token đầu vào model và tăng Evidence Hit@3 từ 2/15 lên 5/15 trên dev, 2/5 lên 3/5 trên test. Điểm coherence tăng từ 1,0 lên 1,9/2. B→C chỉ thay filter; các chỉ số truy xuất và grounding bằng nhau trong bộ câu hỏi hiện tại. Không suy rộng kết quả từ 5 câu test sang tài liệu khác.

## Phân tích lỗi và kết luận

- **`q09` (giáo viên, gold trang 62):** cả A và B/C đều không đưa đoạn nêu rõ “định nghĩa năng lực là điều kiện cần nhưng chưa đủ” vào top-3. A lấy trang 18/21/46; B lấy 33/42/26. Đây là lỗi chọn bằng chứng, không phải thiếu trang trong corpus.
- **`q20` (học sinh, gold trang 90):** top-3 lấy các trang 16/18/74 liên quan đến đạo đức và bền vững, nhưng bỏ lỡ kết luận về ngành giáo dục phải chủ động định hình AI. Nhãn grounding 1 phản ánh nội dung liên quan nhưng chưa đủ điều kiện của câu hỏi.
- **`q18` (học sinh, gold trang 44):** A chỉ lấy trang 26 nên thiếu mô tả mục tiêu chung; B/C có đoạn đầy đủ ở hạng 2 trang 44. Ví dụ này cho thấy hiệu ứng của ranh giới chunk và xếp hạng.

**Chọn B** theo tiêu chí dev đã công bố; C không cải thiện kết quả trong corpus và bộ câu hỏi này nhưng vẫn hữu ích nếu top-3 không lọc lẫn sang tài liệu khác. Hạn chế chính gồm test chỉ 5 câu, một cặp tài liệu cùng chủ đề, gold hiện chủ yếu là một vị trí, PDF bảng nhiều cột, thời gian GPU đo một lần sau tải model và audit do Codex chấm sau khi đã thấy gold/trace. Vì test này đã được xem, mọi lần chỉnh pipeline theo kết quả hiện tại phải dùng tập test mới.

**Tái lập:** xem [lệnh setup/chạy](../../docs/RUN_LAB.md), [experiment log](../../artifacts/experiment_log.csv), manifest, benchmark và trace. Không cần API key; `.env`, model cache và hai PDF local không được đưa vào repo.
