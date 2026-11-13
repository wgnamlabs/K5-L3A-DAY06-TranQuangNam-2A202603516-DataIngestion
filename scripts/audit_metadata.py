"""Verify every test top-3 trace record against the PDF snapshot and manifest."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))

from src.run import _load_inputs  # noqa: E402


def main() -> None:
    manifest, questions, pages = _load_inputs()
    documents = {item["source_id"]: item for item in manifest["documents"]}
    page_index = {(page.document_id, page.page): page for page in pages}
    trace_path = ROOT / "results" / "traces_test.jsonl"
    traces = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    if len(traces) != 3 * sum(item["split"] == "test" for item in questions):
        raise ValueError("Unexpected number of test traces")

    records = []
    for trace in traces:
        if len(trace["hits"]) != 3:
            raise ValueError(f"Expected top-3 for {trace['id']} {trace['strategy']}")
        for hit in trace["hits"]:
            document = documents.get(hit["document_id"])
            page = page_index.get((hit["document_id"], hit["page"]))
            meta = hit["metadata"]
            start, end = meta.get("start_char"), meta.get("end_char")
            checks = {
                "source_matches_manifest": bool(document and hit["source"] == document["source_path_or_url"]),
                "page_is_included": page is not None,
                "audience_matches_manifest": bool(document and hit["audience"] == document["audience"]
                                                  and meta.get("audience") == document["audience"]),
                "page_id_matches": bool(page and meta.get("page_id") == page.metadata["page_id"]),
                "title_version_hash_match": bool(document and meta.get("title") == document["title"]
                                                 and meta.get("version") == document["version"]
                                                 and meta.get("source_sha256") == document["sha256"]),
                "chunk_text_matches_pdf_page": bool(page and isinstance(start, int) and isinstance(end, int)
                                                    and 0 <= start < end <= len(page.text)
                                                    and page.text[start:end].strip() == hit["text"]),
            }
            records.append({"question_id": trace["id"], "strategy": trace["strategy"],
                            "rank": hit["rank"], "chunk_id": hit["chunk_id"],
                            "source": hit["source"], "page": hit["page"],
                            "audience": hit["audience"], "checks": checks,
                            "valid": all(checks.values())})

    total = Counter(record["strategy"] for record in records)
    valid = Counter(record["strategy"] for record in records if record["valid"])
    result = {
        "method": "Deterministic audit: SHA-256-verified PDFs are re-extracted; source, page, audience, provenance and exact chunk span are compared with each test top-3 trace record.",
        "limitations": "This deterministic check verifies metadata and trace provenance; the case-by-case coherence and grounding judgments are recorded separately in manual_audit.json.",
        "summary": {strategy: {"valid": valid[strategy], "total": total[strategy]}
                    for strategy in ("A", "B", "C")},
        "records": records,
    }
    output = ROOT / "results" / "metadata_audit.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Metadata audit:", result["summary"])
    if not all(record["valid"] for record in records):
        raise SystemExit("Some metadata records did not match their PDF page")


if __name__ == "__main__":
    main()
