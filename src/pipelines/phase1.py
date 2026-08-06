from __future__ import annotations

from datetime import UTC, datetime
import json

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def _records_for_json(df):
    return json.loads(df.to_json(orient="records", force_ascii=False))

def main() -> None:
    """Run the reproducible clean-data baseline from source snapshot to report."""
    settings = load_settings()
    raw_path = settings.paths.raw_records_json
    if raw_path.exists() and not settings.refresh_source:
        records = load_raw_records(raw_path)
        source_mode = "cached raw snapshot"
    else:
        records = fetch_source_records(settings)
        source_mode = "live Crossref fetch"

    clean_df = build_clean_dataframe(records, run_date=datetime.now(UTC))
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, _records_for_json(clean_df))

    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        test_set = read_json(settings.paths.eval_testset)
    else:
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    if not test_set:
        raise RuntimeError("Evaluation test set is empty.")

    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings, "baseline_quality")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    demo = []
    for item in test_set[:3]:
        answer = answer_question(item["question"], settings, index)
        demo.append(
            {
                "question": item["question"],
                "answer": answer.answer,
                "retrieved_doc_ids": answer.retrieved_doc_ids,
            }
        )
    write_json(settings.paths.demo_answers, demo)
    generate_phase1_report(
        settings.paths.baseline_report,
        {
            "source": settings.source_api,
            "endpoint": settings.source_url,
            "query": settings.source_query,
            "filter": settings.source_filter,
            "records": len(records),
            "mode": source_mode,
        },
        evaluation.summary,
        quality,
        freshness,
    )
    print(
        f"Baseline complete: {len(clean_df)} clean rows, "
        f"retrieval_hit_rate={evaluation.summary['retrieval_hit_rate']:.3f}, "
        f"quality={'PASS' if quality['passed'] else 'FAIL'}"
    )
