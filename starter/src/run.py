"""Reproducible ingestion and frozen dev/test retrieval experiment."""

from __future__ import annotations

import hashlib
import json
import os
import statistics
import time
import re
import unicodedata
from importlib.metadata import version
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf
from .models import Chunk, DocumentPage
from .store import PgVectorStore


ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "starter"
RESULTS = ROOT / "results"
MODEL = "google/embeddinggemma-2"
MODEL_REVISION = "f9972ac22e696a105c482202646979e33e4b5a1e"
DIMENSIONS = 768
FIXED_SIZE = 500
FIXED_OVERLAP = 50
PARAGRAPH_MAX = 800


def _load_inputs() -> tuple[dict[str, Any], list[dict[str, Any]], list[DocumentPage]]:
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    questions = json.loads((ROOT / "benchmark" / "questions.json").read_text(encoding="utf-8"))
    if manifest["total_content_pages"] < 30 or len(questions) < 20:
        raise ValueError("Corpus or benchmark is below the lab minimum")
    if sum(q["split"] == "dev" for q in questions) < 15 or sum(q["split"] == "test" for q in questions) < 5:
        raise ValueError("Benchmark dev/test split is below the lab minimum")
    pages: list[DocumentPage] = []
    for document in manifest["documents"]:
        source = document["source_path_or_url"]
        path = ROOT / source
        if hashlib.sha256(path.read_bytes()).hexdigest() != document["sha256"]:
            raise ValueError(f"PDF changed since manifest creation: {source}")
        included = {p["physical_page"] for p in document["pages"] if p["included"]}
        loaded = load_pdf(
            path, document["source_id"], source, included_pages=included,
            repeated_title=document["title"],
            metadata={"audience": document["audience"], "title": document["title"],
                      "version": document["version"], "source_sha256": document["sha256"],
                      "corpus_id": manifest["corpus_id"]},
        )
        if len(loaded) != document["content_page_count"]:
            raise ValueError(f"Page count mismatch: {source}")
        pages.extend(loaded)
    if len(pages) != manifest["total_content_pages"]:
        raise ValueError("Manifest total content page count mismatch")
    page_index = {(page.document_id, page.page): page for page in pages}
    for question in questions:
        page = page_index.get((question["gold_source_id"], question["gold_page"]))
        if page is None:
            raise ValueError(f"Gold page is not included: {question['id']}")
        fold = lambda value: re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()
        if fold(question["evidence_quote"]) not in fold(page.text):
            raise ValueError(f"Gold evidence missing after ingestion: {question['id']}")
    return manifest, questions, pages


def _make_chunks(pages: list[DocumentPage]) -> tuple[list[Chunk], list[Chunk]]:
    fixed = [chunk for page in pages for chunk in fixed_size(page, FIXED_SIZE, FIXED_OVERLAP)]
    paragraph = [chunk for page in pages for chunk in by_paragraph(page, PARAGRAPH_MAX)]
    return fixed, paragraph


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for value in values:
            file.write(json.dumps(value, ensure_ascii=False) + "\n")


def _chunk_stats(chunks: list[Chunk]) -> dict[str, Any]:
    lengths = sorted(len(chunk.text) for chunk in chunks)
    if not lengths:
        raise ValueError("No chunks generated")
    return {"count": len(lengths), "total_characters": sum(lengths),
            "min_characters": lengths[0], "median_characters": statistics.median(lengths),
            "mean_characters": round(statistics.mean(lengths), 1),
            "p90_characters": lengths[int(0.9 * (len(lengths) - 1))],
            "max_characters": lengths[-1]}


def _token_stats(chunks: list[Chunk], tokenizer: Any) -> dict[str, Any]:
    inputs = [f"title: {chunk.metadata['title']} | text: {chunk.text}" for chunk in chunks]
    lengths = sorted(len(ids) for ids in tokenizer(inputs, add_special_tokens=True,
                                                   truncation=False)["input_ids"])
    return {"count": len(lengths), "total_model_input_tokens": sum(lengths),
            "median_model_input_tokens": statistics.median(lengths),
            "max_model_input_tokens": lengths[-1]}


def _manual_template(pages: list[DocumentPage], chunks_a: list[Chunk],
                     chunks_b: list[Chunk], traces: list[dict[str, Any]]) -> dict[str, Any]:
    # Freeze five positions per document by source order, independently of scores.
    chosen: list[DocumentPage] = []
    for document_id in sorted({page.document_id for page in pages}):
        chosen.extend(sorted((page for page in pages if page.document_id == document_id),
                             key=lambda page: page.page)[:5])
    coherence = []
    for page in chosen:
        offset = len(page.text) // 2
        for strategy, chunks in (("A", chunks_a), ("B", chunks_b), ("C", chunks_b)):
            matches = [chunk for chunk in chunks if chunk.document_id == page.document_id
                       and chunk.page == page.page
                       and chunk.metadata["start_char"] <= offset < chunk.metadata["end_char"]]
            coherence.append({"strategy": strategy, "page_id": page.metadata["page_id"],
                              "source_offset": offset, "chunk_id": matches[0].chunk_id if matches else None,
                              "chunk_text": matches[0].text if matches else None,
                              "coherence_label_0_to_2": None, "reason": None})
    test = [{"strategy": trace["strategy"], "question_id": trace["id"],
             "hits": [{"rank": hit["rank"], "chunk_id": hit["chunk_id"],
                       "document_id": hit["document_id"], "source": hit["source"],
                       "page": hit["page"], "audience": hit["audience"]}
                      for hit in trace["hits"]],
             "metadata_correct_count_out_of_3": None,
             "grounding_label_0_to_2": None, "reason": None}
            for trace in traces if trace["split"] == "test"]
    return {"review_status": "unreviewed",
            "coherence_sample_rule": "First five included physical pages per document; midpoint character on each page.",
            "coherence": coherence, "test_review": test}


def _save_audit_sample(sample: dict[str, Any]) -> None:
    """Keep a completed audit only while it matches the newly generated results."""
    path = RESULTS / "manual_audit.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("review_status") == "complete":
            for field in ("coherence", "test_review"):
                old = existing[field]
                new = sample[field]
                if len(old) != len(new):
                    raise RuntimeError(f"Completed audit no longer matches {field} count")
                for previous, current in zip(old, new):
                    keys = ("strategy", "page_id", "source_offset", "chunk_id", "chunk_text") if field == "coherence" else ("strategy", "question_id", "hits")
                    for key in keys:
                        if key == "hits":
                            if [{k: hit[k] for k in ("rank", "chunk_id", "document_id", "source", "page", "audience")}
                                for hit in previous[key]] != current[key]:
                                raise RuntimeError("Completed audit no longer matches test top-3 hits")
                        elif previous[key] != current[key]:
                            raise RuntimeError(f"Completed audit no longer matches {field}: {key}")
            return
    _write_json(path, sample)


def main() -> None:
    load_dotenv(STARTER / ".env")
    os.environ.setdefault("HF_HOME", str(STARTER / ".model_cache"))
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL missing from starter/.env")
    RESULTS.mkdir(parents=True, exist_ok=True)
    manifest, questions, pages = _load_inputs()
    chunks_a, chunks_b = _make_chunks(pages)
    print(f"Loaded {len(pages)} content pages; A={len(chunks_a)} chunks, B/C={len(chunks_b)} chunks", flush=True)

    embedder = MyEmbedder(MODEL, DIMENSIONS, revision=MODEL_REVISION)
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=MODEL_REVISION,
                                              local_files_only=True)
    token_stats_a = _token_stats(chunks_a, tokenizer)
    token_stats_b = _token_stats(chunks_b, tokenizer)
    store = PgVectorStore(database_url, DIMENSIONS, MODEL)
    store.create_schema()
    ingest_seconds: dict[str, float] = {}
    for strategy, chunks in (("A", chunks_a), ("B", chunks_b)):
        started = time.perf_counter()
        vectors = embedder.embed_documents([chunk.text for chunk in chunks],
                                           [str(chunk.metadata["title"]) for chunk in chunks])
        store.upsert(strategy, chunks, vectors)
        ingest_seconds[strategy] = round(time.perf_counter() - started, 3)
        if store.count(strategy) != len(chunks):
            raise RuntimeError(f"Database row count mismatch for {strategy}")
        print(f"Ingested {strategy}: {len(chunks)} rows in {ingest_seconds[strategy]}s", flush=True)

    traces: list[dict[str, Any]] = []
    for split in ("dev", "test"):
        # Select on dev before running any test query, using the frozen rule.
        if split == "test":
            dev_metrics = summarize(traces)
            chosen = max(("A", "B", "C"),
                         key=lambda name: (dev_metrics[f"{name}:dev"]["evidence_hit_at_3"],
                                           dev_metrics[f"{name}:dev"]["hit_at_1"],
                                           -ingest_seconds["B" if name == "C" else name]))
            print(f"Selected on dev: {chosen}; now evaluating frozen test", flush=True)
        split_traces = []
        for question in (item for item in questions if item["split"] == split):
            query_vector = embedder.embed_query(question["question"])
            for strategy in ("A", "B", "C"):
                applied_filter = question.get("filter") if strategy == "C" else None
                hits = store.search("B" if strategy == "C" else strategy,
                                    query_vector, top_k=3, filters=applied_filter)
                trace = evaluate_query(question, hits)
                trace["strategy"] = strategy
                trace["applied_filter"] = applied_filter
                split_traces.append(trace)
        traces.extend(split_traces)
        _write_jsonl(RESULTS / f"traces_{split}.jsonl", split_traces)
        print(f"Wrote {len(split_traces)} {split} traces", flush=True)

    metrics = summarize(traces)
    filter_compliance: dict[str, dict[str, int]] = {}
    for trace in traces:
        required = trace["filter"]
        if required:
            key = f"{trace['strategy']}:{trace['split']}"
            counts = filter_compliance.setdefault(key, {"compliant": 0, "questions": 0})
            counts["questions"] += 1
            counts["compliant"] += int(len(trace["hits"]) == 3 and all(
                hit["audience"] == required["audience"] for hit in trace["hits"]))
    _write_json(RESULTS / "metrics.json", {
        "corpus_id": manifest["corpus_id"], "model": MODEL,
        "model_revision": MODEL_REVISION, "dimensions": DIMENSIONS,
        "model_device": embedder.device, "model_dtype": embedder.dtype,
        "packages": {name: version(name) for name in ("sentence-transformers", "transformers", "torch", "psycopg", "pypdf")},
        "vector_store": "PostgreSQL + pgvector; exact cosine search",
        "chunking": {"A": {"size": FIXED_SIZE, "overlap": FIXED_OVERLAP},
                     "B": {"paragraph_max": PARAGRAPH_MAX},
                     "C": {"same_chunks_as": "B", "filter": "audience only when supplied"}},
        "chunk_counts": {"A": len(chunks_a), "B": len(chunks_b), "C": len(chunks_b)},
        "chunk_character_stats": {"A": _chunk_stats(chunks_a),
                                  "B": _chunk_stats(chunks_b),
                                  "C": _chunk_stats(chunks_b)},
        "chunk_token_stats": {"A": token_stats_a, "B": token_stats_b, "C": token_stats_b},
        "ingest_seconds": {**ingest_seconds, "C": 0.0},
        "embedding_api_cost": 0,
        "selection_rule": "dev Evidence Hit@3, then dev Hit@1, then ingest time",
        "selected_on_dev": chosen,
        "metrics": metrics,
        "filter_compliance": filter_compliance,
    })
    _save_audit_sample(_manual_template(pages, chunks_a, chunks_b, traces))
    print(json.dumps(metrics, ensure_ascii=False, indent=2), flush=True)
    print(f"Results saved in {RESULTS}", flush=True)


if __name__ == "__main__":
    main()
