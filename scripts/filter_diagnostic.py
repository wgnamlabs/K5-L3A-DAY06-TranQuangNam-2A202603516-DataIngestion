"""Post-hoc dev-only demonstration of the audience SQL filter; not a benchmark score."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))

from src.embeddings import MyEmbedder  # noqa: E402
from src.run import DIMENSIONS, MODEL, MODEL_REVISION  # noqa: E402
from src.store import PgVectorStore  # noqa: E402


def main() -> None:
    load_dotenv(ROOT / "starter" / ".env")
    os.environ.setdefault("HF_HOME", str(ROOT / "starter" / ".model_cache"))
    questions = json.loads((ROOT / "benchmark" / "questions.json").read_text(encoding="utf-8"))
    question = next(item for item in questions if item["id"] == "q05")
    if question["split"] != "dev" or "AI CFT" not in question["question"]:
        raise ValueError("q05 is no longer an AI CFT dev question")
    store = PgVectorStore(os.environ["DATABASE_URL"], DIMENSIONS, MODEL)
    vector = MyEmbedder(MODEL, DIMENSIONS, revision=MODEL_REVISION).embed_query(question["question"])
    unfiltered = store.search("B", vector, top_k=3)
    filtered = store.search("B", vector, top_k=3, filters={"audience": "teachers"})
    if len(unfiltered) != 3 or len(filtered) != 3 or any(hit["audience"] != "teachers" for hit in filtered):
        raise RuntimeError("Filter diagnostic did not return three teacher chunks")

    def brief(hits: list[dict]) -> list[dict]:
        return [{"rank": rank, "chunk_id": hit["chunk_id"], "source": hit["source"],
                 "physical_page": hit["page"], "audience": hit["audience"],
                 "score": hit["score"]} for rank, hit in enumerate(hits, 1)]

    result = {
        "type": "post_hoc_dev_diagnostic",
        "benchmark_unchanged": True,
        "used_for_selection_or_test_metrics": False,
        "question_id": question["id"],
        "question": question["question"],
        "filter_source": "Diagnostic user context supplied before retrieval: đang xem Khung năng lực AI cho giáo viên (AI CFT). This context is not inferred from gold or retrieval results.",
        "filter": {"audience": "teachers"},
        "unfiltered_B_top3": brief(unfiltered),
        "filtered_B_top3": brief(filtered),
        "unfiltered_wrong_audience_count": sum(hit["audience"] != "teachers" for hit in unfiltered),
        "filtered_wrong_audience_count": sum(hit["audience"] != "teachers" for hit in filtered),
    }
    output = ROOT / "results" / "filter_diagnostic_q05.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Unfiltered wrong audience: {result['unfiltered_wrong_audience_count']}/3; "
          f"filtered: {result['filtered_wrong_audience_count']}/3")


if __name__ == "__main__":
    main()
