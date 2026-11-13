"""Tạo lại manifest cho hai bản dịch tiếng Việt của khung năng lực AI UNESCO."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date
from importlib.metadata import version
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "manifest.json"
CORPUS = Path("data") / "corpus"
LICENSE_URL = "https://www.unesco.org/en/open-access/cc-sa"
LICENSE_NOTE = (
    "Văn bản trong PDF ghi CC BY-SA 3.0 IGO: ghi công UNESCO, bản gốc và người dịch; "
    "bản phái sinh phải chia sẻ tương tự. Hình ảnh đánh dấu (*) không thuộc giấy phép này."
)

SOURCES = [
    {
        "source_id": "unesco-ai-cft-vi-2025",
        "title": "Khung năng lực AI cho giáo viên",
        "filename": "391104eng_Vi-03022025.pdf",
        "audience": "teachers",
        "source_url": "https://zenodo.org/records/14897590",
        "original_url": "https://unesdoc.unesco.org/ark:/48223/pf0000391104",
        "translator": "Lê Trung Nghĩa",
        "translation_completed_at": "2025-02-03",
        "version": "Bản dịch tiếng Việt v1 (Zenodo); bản gốc UNESCO 2024",
        "zenodo_md5": "b8cad4187f9fde6d9f475519161930b7",
        "first_content_page": 14,
        "last_content_page": 70,
        "excluded_pages": {
            1: "bìa",
            2: "giới thiệu UNESCO, ngoài nội dung chính của khung",
            3: "thông tin giấy phép và xuất bản",
            4: "tóm tắt đầu tài liệu, không tính trùng với phần nội dung chính",
            5: "trang phân cách",
            6: "lời nói đầu",
            7: "lời nói đầu",
            8: "lời thừa nhận",
            9: "lời thừa nhận",
            10: "mục lục",
            11: "mục lục",
            12: "danh sách bảng và hộp",
            13: "danh sách từ viết tắt",
            71: "chỉ có tài liệu tham khảo",
            72: "chỉ có tài liệu tham khảo",
            73: "bìa sau",
        },
    },
    {
        "source_id": "unesco-ai-cfs-vi-2025",
        "title": "Khung năng lực AI cho học sinh",
        "filename": "391105eng_Vi-10022025.pdf",
        "audience": "students",
        "source_url": "https://zenodo.org/records/14903158",
        "original_url": "https://unesdoc.unesco.org/ark:/48223/pf0000391105",
        "translator": "Lê Trung Nghĩa",
        "translation_completed_at": "2025-02-10",
        "version": "Bản dịch tiếng Việt v1 (Zenodo); bản gốc UNESCO 2024",
        "zenodo_md5": "a1c8c5bd89de7dd87940f3815d335983",
        "first_content_page": 14,
        "last_content_page": 90,
        "excluded_pages": {
            1: "bìa",
            2: "giới thiệu UNESCO, ngoài nội dung chính của khung",
            3: "thông tin giấy phép và xuất bản",
            4: "tóm tắt đầu tài liệu, không tính trùng với phần nội dung chính",
            5: "trang phân cách",
            6: "lời nói đầu",
            7: "lời nói đầu",
            8: "lời thừa nhận",
            9: "lời thừa nhận",
            10: "mục lục",
            11: "mục lục",
            12: "danh sách bảng",
            13: "danh sách từ viết tắt",
            91: "chỉ có tài liệu tham khảo",
            92: "chỉ có tài liệu tham khảo",
            93: "chú giải cuối tài liệu, ngoài phần nội dung chính",
            94: "bìa sau",
        },
    },
]


def normalize_page_text(text: str, repeated_title: str) -> str:
    """Đếm ký tự nội dung sau khi bỏ đường kẻ và đầu/chân trang lặp lại."""
    lines = []
    for line in unicodedata.normalize("NFKC", text).splitlines():
        stripped = line.strip()
        if not stripped or re.fullmatch(r"[-–—_ ]{20,}", stripped):
            continue
        if stripped == repeated_title:
            continue
        if stripped.startswith("Viện Nghiên cứu, Đào tạo") and re.search(r"Tr\.\s*\d+/\d+", stripped):
            continue
        lines.append(stripped)
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def build_document(spec: dict) -> dict:
    relative_path = CORPUS / spec["filename"]
    path = ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(path)
    file_bytes = path.read_bytes()
    if hashlib.md5(file_bytes).hexdigest() != spec["zenodo_md5"]:
        raise ValueError(f"File không khớp bản Zenodo: {path.name}")
    reader = PdfReader(path)
    if len(reader.pages) != max(spec["last_content_page"], *spec["excluded_pages"]):
        raise ValueError(f"Số trang thay đổi: {path.name}")

    pages = []
    for physical_page, pdf_page in enumerate(reader.pages, start=1):
        text = normalize_page_text(pdf_page.extract_text() or "", spec["title"])
        reason = spec["excluded_pages"].get(physical_page)
        included = reason is None
        if included and not spec["first_content_page"] <= physical_page <= spec["last_content_page"]:
            raise ValueError(f"Trang chưa phân loại: {path.name}, trang {physical_page}")
        if included and not text:
            raise ValueError(f"Trang được tính nhưng không trích xuất được: {path.name}, trang {physical_page}")
        page = {
            "page_id": f"{spec['source_id']}:p{physical_page:03d}",
            "physical_page": physical_page,
            "normalized_char_count": len(text),
            "included": included,
        }
        if reason:
            page["exclusion_reason"] = reason
        pages.append(page)

    content_pages = [page for page in pages if page["included"]]
    return {
        "source_id": spec["source_id"],
        "title": spec["title"],
        "source_path_or_url": relative_path.as_posix(),
        "source_url": spec["source_url"],
        "original_url": spec["original_url"],
        "license_or_permission": LICENSE_NOTE,
        "license_url": LICENSE_URL,
        "accessed_at": "2026-11-13",
        "translator": spec["translator"],
        "translation_completed_at": spec["translation_completed_at"],
        "version": spec["version"],
        "audience": spec["audience"],
        "sha256": hashlib.sha256(file_bytes).hexdigest(),
        "zenodo_md5": spec["zenodo_md5"],
        "physical_page_count": len(pages),
        "content_page_count": len(content_pages),
        "content_normalized_char_count": sum(page["normalized_char_count"] for page in content_pages),
        "content_page_ids": [page["page_id"] for page in content_pages],
        "pages": pages,
    }


def main() -> None:
    documents = [build_document(spec) for spec in SOURCES]
    manifest = {
        "corpus_id": "unesco-ai-competency-frameworks-vi-2025",
        "topic": "Khung năng lực AI trong giáo dục cho giáo viên và học sinh",
        "created_at": date.today().isoformat(),
        "page_id_rule": "Trang vật lý PDF bắt đầu từ 1: <source_id>:pNNN.",
        "normalization_for_count": "pypdf; Unicode NFKC; bỏ đường kẻ và đầu/chân trang lặp lại; gộp khoảng trắng",
        "counting_rule": "Chỉ tính các trang nội dung chính từ Chương 1 đến kết luận; loại bìa, phần đầu, mục lục, trang phân cách, tài liệu tham khảo và bìa sau. Lý do loại ghi ở từng trang.",
        "filter_metadata": {
            "field": "audience",
            "values": ["teachers", "students"],
            "source": "Nhan đề trên bìa của từng bản dịch",
            "use": "Chỉ lọc khi câu hỏi hoặc ngữ cảnh xác định rõ đối tượng giáo viên hoặc học sinh trước khi truy xuất.",
        },
        "extractor": {"name": "pypdf", "version": version("pypdf")},
        "total_physical_pages": sum(doc["physical_page_count"] for doc in documents),
        "total_content_pages": sum(doc["content_page_count"] for doc in documents),
        "total_content_normalized_char_count": sum(doc["content_normalized_char_count"] for doc in documents),
        "documents": documents,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã ghi {OUTPUT.relative_to(ROOT)}")
    for document in documents:
        print(f"{document['source_id']}: {document['content_page_count']}/{document['physical_page_count']} trang nội dung")
    print(f"Tổng: {manifest['total_content_pages']} trang nội dung")


if __name__ == "__main__":
    main()
