from __future__ import annotations

from datetime import UTC, datetime
import logging

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from pipelines.common import dataframe_records, ensure_output_directories, run_stage
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    """Run baseline from Crossref/raw snapshot through report generation."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    run_stage("create output directories", ensure_output_directories, settings.paths)
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        records = run_stage("load raw snapshot", load_raw_records, settings.paths.raw_records_json)
        source_mode = "cached raw snapshot"
    else:
        records = run_stage("fetch Crossref", fetch_source_records, settings)
        source_mode = "live Crossref fetch"
    clean_df = run_stage("clean data", build_clean_dataframe, records, datetime.now(UTC))
    run_stage("save clean CSV", write_csv, clean_df, settings.paths.clean_csv)
    run_stage("save clean JSON", write_json, settings.paths.clean_json, dataframe_records(clean_df))
    index = run_stage(
        "build baseline Chroma collection",
        LocalEmbeddingIndex.build, clean_df, settings, settings.paths.embeddings_json,
    )
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        test_set = run_stage("load evaluation set", read_json, settings.paths.eval_testset)
        if not isinstance(test_set, list) or not test_set:
            raise RuntimeError("Existing evaluation set is empty or invalid; set REFRESH_TEST_SET=true.")
    else:
        test_set = run_stage("build evaluation set", build_test_set, clean_df, settings.paths.eval_testset)
    evaluation = run_stage(
        "evaluate baseline", evaluate_pipeline, settings, index, settings.paths.eval_testset,
        settings.paths.baseline_metrics, settings.paths.baseline_answers,
    )
    quality = run_stage(
        "baseline data quality", run_data_quality_checks, clean_df, settings, "baseline_quality"
    )
    freshness = run_stage(
        "baseline freshness", build_freshness_report, clean_df, settings, settings.paths.freshness_report
    )
    demo_answers = []
    for item in test_set[:3]:
        answer = answer_question(item["question"], settings, index)
        demo_answers.append({
            "question": item["question"], "answer": answer.answer,
            "retrieved_doc_ids": answer.retrieved_doc_ids,
        })
    run_stage("save QA demo", write_json, settings.paths.demo_answers, demo_answers)
    source_summary = {
        "source": settings.source_api,
        "endpoint": settings.source_url,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "mode": source_mode,
        "embedding_backend": index.embedding_backend,
        "collection": index.collection_name,
    }
    run_stage(
        "generate baseline report", generate_phase1_report, settings.paths.baseline_report,
        source_summary, evaluation.summary, quality, freshness,
    )
    print("\nBaseline pipeline PASS")
    print(f"  raw/clean rows: {len(records)}/{len(clean_df)}")
    print(f"  embedding backend: {index.embedding_backend}")
    print(f"  retrieval hit rate: {evaluation.summary['retrieval_hit_rate']:.4f}")
    print(f"  quality/freshness: {quality['status']}/{freshness['status']}")
