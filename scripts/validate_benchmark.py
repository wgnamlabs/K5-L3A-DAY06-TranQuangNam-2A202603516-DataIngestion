"""Validate benchmark structure and check every gold quote against its PDF page."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "id",
    "split",
    "question",
    "expected_answer",
    "gold_source_id",
    "gold_page",
    "evidence_quote",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def main() -> None:
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    questions = json.loads((ROOT / "benchmark" / "questions.json").read_text(encoding="utf-8"))
    documents = {document["source_id"]: document for document in manifest["documents"]}
    readers = {}
    for source_id, document in documents.items():
        path = ROOT / document["source_path_or_url"]
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != document["sha256"]:
            raise ValueError(f"PDF differs from manifest snapshot: {path.name}")
        readers[source_id] = PdfReader(path)

    errors = []
    seen_ids = set()
    for question in questions:
        question_id = question.get("id", "<missing id>")
        missing = REQUIRED - question.keys()
        if missing:
            errors.append(f"{question_id}: missing {sorted(missing)}")
            continue
        if question_id in seen_ids:
            errors.append(f"{question_id}: duplicate ID")
        seen_ids.add(question_id)
        if question["split"] not in {"dev", "test"}:
            errors.append(f"{question_id}: invalid split")
        if not all(isinstance(question[key], str) and question[key].strip() for key in ("question", "expected_answer", "evidence_quote")):
            errors.append(f"{question_id}: empty question, answer, or evidence")
        document = documents.get(question["gold_source_id"])
        if document is None:
            errors.append(f"{question_id}: unknown source ID")
            continue
        page = question["gold_page"]
        if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= document["physical_page_count"]:
            errors.append(f"{question_id}: invalid physical page")
            continue
        if not document["pages"][page - 1]["included"]:
            errors.append(f"{question_id}: gold page excluded from corpus")
        page_text = normalize(readers[document["source_id"]].pages[page - 1].extract_text() or "")
        if normalize(question["evidence_quote"]) not in page_text:
            errors.append(f"{question_id}: evidence quote absent from PDF page {page}")
        if "filter" in question and question["filter"] != {"audience": document["audience"]}:
            errors.append(f"{question_id}: filter is not the documented source-backed audience")

    splits = Counter(question.get("split") for question in questions)
    if len(questions) < 20 or splits["dev"] < 15 or splits["test"] < 5:
        errors.append(f"need at least 20 questions, 15 dev and 5 test; got {dict(splits)}")
    filtered = [question for question in questions if "filter" in question]
    if len(filtered) < 3 or not any(question.get("split") == "test" for question in filtered):
        errors.append("need at least 3 filter questions, including 1 test question")

    if errors:
        raise SystemExit("Benchmark validation failed:\n- " + "\n- ".join(errors))
    print(f"Benchmark OK: {len(questions)} questions, {splits['dev']} dev, {splits['test']} test, {len(filtered)} filters; all gold quotes found on included PDF pages.")
    print("Case-by-case answer support is recorded in results/manual_audit.json; this validator checks quote presence only.")


if __name__ == "__main__":
    main()
