from __future__ import annotations

from typing import Any

from core.utils import write_text


METRIC_NAMES = ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def _format(value: Any, digits: int = 4) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}" if isinstance(value, float) else str(value)
    return "N/A" if value is None else str(value)


def _metric_rows(metrics: dict[str, Any]) -> str:
    return "\n".join(f"| `{name}` | {_format(metrics.get(name))} |" for name in METRIC_NAMES)


def _quality_rows(quality: dict[str, Any]) -> str:
    checks = quality.get("checks", [])
    if not checks:
        legacy_checks = (
            ("paper_id_unique", "uniqueness", quality.get("pass_paper_id_unique"), quality.get("duplicate_paper_ids")),
            ("paper_id_not_null", "completeness", quality.get("pass_no_null_paper_id"), quality.get("null_paper_ids", 0)),
            ("title_not_null", "completeness", quality.get("pass_no_null_title"), quality.get("null_titles", 0)),
            ("freshness_age_days", "timeliness", quality.get("pass_stale_check"), quality.get("stale_rows", 0)),
        )
        return "\n".join(
            f"| {name} | {dimension} | {'PASS' if passed else 'FAIL'} | {_format(observed)} |"
            for name, dimension, passed, observed in legacy_checks
        )
    return "\n".join(
        f"| {item['name']} | {item['dimension']} | {'PASS' if item['passed'] else 'FAIL'} | {_format(item['observed'])} |"
        for item in checks
    )


def _quality_summary(quality: dict[str, Any]) -> tuple[bool, int, int]:
    """Read both the current detailed artifact and the prior flat schema."""
    if "passed" in quality:
        return bool(quality["passed"]), int(quality.get("passed_checks", 0)), int(quality.get("failed_checks", 0))
    flags = [
        quality.get("pass_paper_id_unique"),
        quality.get("pass_no_null_paper_id"),
        quality.get("pass_no_null_title"),
        quality.get("pass_stale_check"),
        quality.get("pass_no_duplicates"),
    ]
    known_flags = [flag for flag in flags if flag is not None]
    passed_count = sum(bool(flag) for flag in known_flags)
    return bool(known_flags) and all(known_flags), passed_count, len(known_flags) - passed_count


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Generate a report exclusively from artifacts produced in this run."""
    quality_passed, passed_checks, failed_checks = _quality_summary(quality)
    report = f"""# Baseline Pipeline Report

## Source lineage

| Field | Value |
| --- | --- |
| API | {_format(source_summary.get('api'))} |
| Query | {_format(source_summary.get('query'))} |
| Raw records | {_format(source_summary.get('records_fetched'))} |
| Clean records | {_format(source_summary.get('records_cleaned'))} |

## Evaluation metrics

| Metric | Value |
| --- | ---: |
{_metric_rows(metrics)}

## Data quality

Overall: **{'PASS' if quality_passed else 'FAIL'}** — {passed_checks} passed, {failed_checks} failed.

| Check | Dimension | Status | Observed |
| --- | --- | --- | ---: |
{_quality_rows(quality)}

## Freshness

| Field | Value |
| --- | --- |
| Latest published | {_format(freshness.get('latest_published'))} |
| Oldest published | {_format(freshness.get('oldest_published'))} |
| Latest source update | {_format(freshness.get('latest_source_updated'))} |
| Stale rows | {_format(freshness.get('stale_rows'))} / {_format(freshness.get('total_rows'))} |
| Threshold | {_format(freshness.get('freshness_threshold_days'))} days |
| Status | **{_format(freshness.get('status'))}** |

## Evidence

The metrics above are calculated from the persisted test set, answer artifact, and baseline index. Quality and freshness values are calculated from the clean-data artifact of the same run.
"""
    write_text(report_path, report)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Compare baseline, corrupted, and repaired artifacts without overclaiming."""
    rows = []
    for metric in METRIC_NAMES[1:]:
        baseline = float(baseline_metrics.get(metric, 0.0))
        corrupted = float(corrupted_metrics.get(metric, 0.0))
        repaired = float(repaired_metrics.get(metric, 0.0))
        rows.append(
            f"| `{metric}` | {baseline:.4f} | {corrupted:.4f} | {repaired:.4f} | "
            f"{corrupted - baseline:+.4f} | {repaired - corrupted:+.4f} |"
        )
    retrieval_delta = float(corrupted_metrics.get("retrieval_hit_rate", 0.0)) - float(
        baseline_metrics.get("retrieval_hit_rate", 0.0)
    )
    conclusion = (
        "The corrupted run has lower retrieval hit rate than baseline; inspect the answer and corruption-log artifacts for affected cases."
        if retrieval_delta < 0
        else "The observed corruption did not lower retrieval hit rate on this fixed test set; do not claim degradation without supporting metrics."
    )
    corrupted_passed, corrupted_passed_checks, corrupted_failed_checks = _quality_summary(corrupted_quality)
    repaired_passed, repaired_passed_checks, repaired_failed_checks = _quality_summary(repaired_quality)
    report = f"""# Corruption and Repair Comparison Report

## Evaluation metrics

| Metric | Baseline | Corrupted | Repaired | Corruption Δ | Repair Δ |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

## Data observability

| Dataset | Quality | Passed / Failed | Freshness | Stale rows |
| --- | --- | ---: | --- | ---: |
| Corrupted | {'PASS' if corrupted_passed else 'FAIL'} | {corrupted_passed_checks} / {corrupted_failed_checks} | {_format(corrupted_freshness.get('status'))} | {_format(corrupted_freshness.get('stale_rows'))} |
| Repaired | {'PASS' if repaired_passed else 'FAIL'} | {repaired_passed_checks} / {repaired_failed_checks} | {_format(repaired_freshness.get('status'))} | {_format(repaired_freshness.get('stale_rows'))} |

## Interpretation

{conclusion}

Repair is evaluated from a freshly rebuilt index and the same fixed test set. The report should be read together with `corruption_log.json`, answer artifacts, and the three metrics JSON files.
"""
    write_text(report_path, report)
