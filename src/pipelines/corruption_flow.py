from __future__ import annotations

from datetime import UTC, datetime
import json

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from observability.visualization import generate_metrics_svg
from retrieval.index import LocalEmbeddingIndex


def _records_for_json(df: pd.DataFrame):
    return json.loads(df.to_json(orient="records", force_ascii=False))

def main() -> None:
    """Measure corruption impact, then rebuild from raw and measure recovery."""
    settings = load_settings()
    required = [
        settings.paths.clean_csv,
        settings.paths.raw_records_json,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(
            "Baseline artifacts are required before corruption flow. Missing: " + ", ".join(missing)
        )
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_df = pd.read_csv(settings.paths.clean_csv, keep_default_na=False)

    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, _records_for_json(corrupted_df))
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, settings.paths.corrupted_embeddings_json
    )
    corrupted_eval = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness.json"
    )

    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date=datetime.now(UTC))
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, _records_for_json(repaired_df))
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, settings.paths.repaired_embeddings_json
    )
    repaired_eval = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness.json"
    )
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_eval.summary,
        repaired_eval.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    generate_metrics_svg(
        settings.paths.comparison_report.parent / "metrics_comparison.svg",
        baseline_metrics,
        corrupted_eval.summary,
        repaired_eval.summary,
    )
    write_json(
        settings.paths.corrupted_metrics.parent / "comparison_metrics.json",
        {
            "baseline": baseline_metrics,
            "corrupted": corrupted_eval.summary,
            "repaired": repaired_eval.summary,
            "quality": {
                "corrupted": corrupted_quality,
                "repaired": repaired_quality,
            },
            "freshness": {
                "corrupted": corrupted_freshness,
                "repaired": repaired_freshness,
            },
        },
    )
    print(
        "Corruption flow complete: "
        f"hit-rate {baseline_metrics['retrieval_hit_rate']:.3f} -> "
        f"{corrupted_eval.summary['retrieval_hit_rate']:.3f} -> "
        f"{repaired_eval.summary['retrieval_hit_rate']:.3f}"
    )
