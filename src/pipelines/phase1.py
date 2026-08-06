from __future__ import annotations

from datetime import datetime, UTC

from core.config import load_settings
from core.utils import write_csv, write_json
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report


def main() -> None:
    settings = load_settings()
    run_date = datetime.now(UTC)

    paths = settings.paths

    if settings.refresh_source or not paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(paths.raw_records_json)

    df = build_clean_dataframe(records, run_date)

    write_csv(df, paths.clean_csv)
    write_json(paths.clean_json, df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(df, settings, paths.embeddings_json)

    test_set = build_test_set(df, paths.eval_testset)

    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )

    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, paths.freshness_report)

    generate_phase1_report(
        report_path=paths.baseline_report,
        source_summary={
            "api": settings.source_api,
            "query": settings.source_query,
            "records_fetched": len(records),
            "records_cleaned": len(df),
        },
        metrics=eval_bundle.summary,
        quality=quality,
        freshness=freshness,
    )

    print("Phase 1 baseline complete.")
    print(f"  Records: {len(records)} raw -> {len(df)} clean")
    print(f"  Test set: {len(test_set)} questions")
    print(f"  Hit rate: {eval_bundle.summary['retrieval_hit_rate']:.3f}")
    print(f"  Report: {paths.baseline_report}")


if __name__ == "__main__":
    main()
