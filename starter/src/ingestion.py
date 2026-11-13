"""Extract selected physical PDF pages while retaining source provenance."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .models import DocumentPage


_SEPARATOR = re.compile(r"[-–—_ ]{20,}")
_FOOTER = re.compile(r"Tr\.\s*\d+/\d+")
_HEADING = re.compile(r"(?:Chương\s+\d+\b|\d+(?:\.\d+)*\s+\S|Mức\s+\d+\s*:|[•▪●]\s+|[-–]\s+)", re.I)


def normalize_text(text: str) -> str:
    """Normalize Unicode and PDF line wraps, retaining likely paragraph boundaries."""
    blocks: list[str] = []
    current = ""
    for raw_line in unicodedata.normalize("NFKC", text).splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or _SEPARATOR.fullmatch(line):
            continue
        starts_block = bool(_HEADING.match(line))
        if current and (starts_block or current.endswith((".", "!", "?", ":", ";"))):
            blocks.append(current)
            current = line
        else:
            current = f"{current} {line}" if current else line
    if current:
        blocks.append(current)
    return "\n\n".join(blocks)


def load_pdf(
    path: Path,
    document_id: str,
    source: str,
    *,
    included_pages: set[int] | None = None,
    metadata: dict[str, Any] | None = None,
    repeated_title: str | None = None,
) -> list[DocumentPage]:
    """Read requested 1-based physical pages; fail on missing or unreadable pages."""
    if not path.is_file():
        raise FileNotFoundError(path)
    reader = PdfReader(path)
    selected = set(range(1, len(reader.pages) + 1)) if included_pages is None else set(included_pages)
    if not selected or min(selected) < 1 or max(selected) > len(reader.pages):
        raise ValueError(f"Invalid physical page selection for {path}")
    pages: list[DocumentPage] = []
    for page_number in sorted(selected):
        raw = reader.pages[page_number - 1].extract_text() or ""
        lines = []
        for line in unicodedata.normalize("NFKC", raw).splitlines():
            stripped = line.strip()
            if repeated_title and stripped == repeated_title:
                continue
            if stripped.startswith("Viện Nghiên cứu, Đào tạo") and _FOOTER.search(stripped):
                continue
            lines.append(line)
        normalized = normalize_text("\n".join(lines))
        if not normalized:
            raise ValueError(f"No extractable text: {path}, physical page {page_number}; OCR required")
        page_metadata = dict(metadata or {})
        page_metadata["page_id"] = f"{document_id}:p{page_number:03d}"
        pages.append(DocumentPage(document_id, source, page_number, normalized, page_metadata))
    return pages
