"""Fixed-window and paragraph-aware chunking on individual PDF pages."""

from __future__ import annotations

import hashlib
import re

from .models import Chunk, DocumentPage


def _chunk(page: DocumentPage, method: str, start: int, end: int) -> Chunk:
    text = page.text[start:end].strip()
    if not text:
        raise ValueError("Cannot create an empty chunk")
    digest = hashlib.sha256(
        f"{page.document_id}\0{page.page}\0{method}\0{start}\0{end}\0{text}".encode("utf-8")
    ).hexdigest()[:20]
    metadata = dict(page.metadata)
    metadata.update({"start_char": start, "end_char": end, "chunk_method": method})
    return Chunk(f"{page.document_id}:p{page.page:03d}:{method}:{digest}",
                 page.document_id, page.source, page.page, text, metadata)


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Split one page into character windows with deterministic overlap."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Require size > 0 and 0 <= overlap < size")
    if not page.text.strip():
        return []
    chunks: list[Chunk] = []
    start = 0
    while start < len(page.text):
        end = min(start + size, len(page.text))
        if page.text[start:end].strip():
            chunks.append(_chunk(page, "fixed", start, end))
        if end == len(page.text):
            break
        start += size - overlap
    return chunks


def _split_oversize(text: str, start: int, end: int, max_size: int) -> list[tuple[int, int]]:
    """Prefer sentence then word boundaries inside an oversized block."""
    pieces: list[tuple[int, int]] = []
    position = start
    while end - position > max_size:
        limit = position + max_size
        window = text[position:limit]
        sentence_ends = [m.end() for m in re.finditer(r"[.!?;:]\s+", window)]
        candidates = [position + offset for offset in sentence_ends if offset >= max_size // 2]
        if candidates:
            cut = candidates[-1]
        else:
            spaces = [m.start() for m in re.finditer(r"\s+", window) if m.start() >= max_size // 2]
            cut = position + spaces[-1] if spaces else limit
        if cut <= position:
            cut = limit
        pieces.append((position, cut))
        position = cut
        while position < end and text[position].isspace():
            position += 1
    if position < end:
        pieces.append((position, end))
    return pieces


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group source blocks up to max_size; split long blocks at readable boundaries."""
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    text = page.text
    blocks = [(m.start(), m.end()) for m in re.finditer(r"\S(?:.*?\S)?(?=\n\n|$)", text, re.S)]
    chunks: list[Chunk] = []
    group_start: int | None = None
    group_end = 0
    for start, end in blocks:
        if end - start > max_size:
            if group_start is not None:
                chunks.append(_chunk(page, "paragraph", group_start, group_end))
                group_start = None
            chunks.extend(_chunk(page, "paragraph", a, b)
                          for a, b in _split_oversize(text, start, end, max_size))
        elif group_start is not None and end - group_start <= max_size:
            group_end = end
        else:
            if group_start is not None:
                chunks.append(_chunk(page, "paragraph", group_start, group_end))
            group_start, group_end = start, end
    if group_start is not None:
        chunks.append(_chunk(page, "paragraph", group_start, group_end))
    return chunks
