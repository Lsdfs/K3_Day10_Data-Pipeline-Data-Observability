from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import logging

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from observability.visualization import generate_metrics_visualization
from pipelines.common import dataframe_records, ensure_output_directories, run_stage
from retrieval.index import LocalEmbeddingIndex


def _file_hash(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Measure corruption impact and independently rebuild repaired state from raw."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    run_stage("create output directories", ensure_output_directories, settings.paths)
    required = [
        settings.paths.clean_csv, settings.paths.raw_records_json,
        settings.paths.eval_testset, settings.paths.baseline_metrics,
    ]
    missing = [str(path.relative_to(settings.paths.project_dir)) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("Baseline must pass before corruption flow. Missing: " + ", ".join(missing))

    baseline_hash_before = _file_hash(settings.paths.clean_csv)
    baseline_metrics = run_stage("load baseline metrics", read_json, settings.paths.baseline_metrics)
    baseline_df = run_stage(
        "load baseline clean data", pd.read_csv, settings.paths.clean_csv, keep_default_na=False
    )
    corrupted_df = run_stage(
        "corrupt clean data", corrupt_clean_dataframe, baseline_df,
        settings.paths.corruption_log, settings.corruption_seed,
    )
    if baseline_hash_before != _file_hash(settings.paths.clean_csv):
        raise RuntimeError("Baseline clean artifact was mutated by corruption.")
    run_stage("save corrupted CSV", write_csv, corrupted_df, settings.paths.corrupted_clean_csv)
    run_stage(
        "save corrupted JSON", write_json, settings.paths.corrupted_clean_json,
        dataframe_records(corrupted_df),
    )
    corrupted_index = run_stage(
        "build corrupted Chroma collection", LocalEmbeddingIndex.build,
        corrupted_df, settings, settings.paths.corrupted_embeddings_json,
    )
    corrupted_eval = run_stage(
        "evaluate corrupted state", evaluate_pipeline, settings, corrupted_index,
        settings.paths.eval_testset, settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )
    corrupted_quality = run_stage(
        "corrupted data quality", run_data_quality_checks,
        corrupted_df, settings, "corrupted_quality",
    )
    corrupted_freshness = run_stage(
        "corrupted freshness", build_freshness_report, corrupted_df, settings,
        settings.paths.corrupted_freshness_report,
    )

    raw_records = run_stage("load raw repair source", load_raw_records, settings.paths.raw_records_json)
    repaired_df = run_stage("repair by standard cleaning", build_clean_dataframe, raw_records, datetime.now(UTC))
    run_stage("save repaired CSV", write_csv, repaired_df, settings.paths.repaired_clean_csv)
    run_stage(
        "save repaired JSON", write_json, settings.paths.repaired_clean_json,
        dataframe_records(repaired_df),
    )
    repaired_index = run_stage(
        "build repaired Chroma collection", LocalEmbeddingIndex.build,
        repaired_df, settings, settings.paths.repaired_embeddings_json,
    )
    repaired_eval = run_stage(
        "evaluate repaired state", evaluate_pipeline, settings, repaired_index,
        settings.paths.eval_testset, settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )
    repaired_quality = run_stage(
        "repaired data quality", run_data_quality_checks, repaired_df, settings, "repaired_quality"
    )
    repaired_freshness = run_stage(
        "repaired freshness", build_freshness_report, repaired_df, settings,
        settings.paths.repaired_freshness_report,
    )
    hashes = {
        baseline_metrics.get("test_set_sha256"),
        corrupted_eval.summary.get("test_set_sha256"),
        repaired_eval.summary.get("test_set_sha256"),
    }
    if len(hashes) != 1 or None in hashes:
        raise RuntimeError("Baseline, corrupted and repaired evaluations did not use one test set.")
    comparison = {
        "test_set_sha256": hashes.pop(),
        "baseline": baseline_metrics,
        "corrupted": corrupted_eval.summary,
        "repaired": repaired_eval.summary,
        "quality": {"corrupted": corrupted_quality, "repaired": repaired_quality},
        "freshness": {"corrupted": corrupted_freshness, "repaired": repaired_freshness},
    }
    run_stage("save comparison metrics", write_json, settings.paths.comparison_metrics, comparison)
    run_stage(
        "generate comparison report", generate_corruption_report, settings.paths.comparison_report,
        baseline_metrics, corrupted_eval.summary, repaired_eval.summary,
        corrupted_quality, repaired_quality, corrupted_freshness, repaired_freshness,
    )
    run_stage(
        "generate comparison visualization", generate_metrics_visualization,
        settings.paths.comparison_csv, settings.paths.comparison_chart,
        baseline_metrics, corrupted_eval.summary, repaired_eval.summary,
    )
    print("\nCorruption/repair pipeline PASS")
    print(
        "  retrieval hit rate: "
        f"{baseline_metrics['retrieval_hit_rate']:.4f} -> "
        f"{corrupted_eval.summary['retrieval_hit_rate']:.4f} -> "
        f"{repaired_eval.summary['retrieval_hit_rate']:.4f}"
    )
    print(f"  quality: baseline artifact -> {corrupted_quality['status']} -> {repaired_quality['status']}")
    print(f"  freshness: baseline artifact -> {corrupted_freshness['status']} -> {repaired_freshness['status']}")
