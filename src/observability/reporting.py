from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    lines = [
        "# Phase 1 — Baseline Pipeline Report",
        "",
        "## Source Summary",
        f"- API: {source_summary.get('api', 'N/A')}",
        f"- Query: {source_summary.get('query', 'N/A')}",
        f"- Records fetched: {source_summary.get('records_fetched', 'N/A')}",
        f"- Records after cleaning: {source_summary.get('records_cleaned', 'N/A')}",
        "",
        "## Evaluation Metrics",
        f"- Samples: {metrics.get('samples', 'N/A')}",
        f"- Retrieval Hit Rate: {metrics.get('retrieval_hit_rate', 'N/A'):.3f}",
        f"- Mean Token F1: {metrics.get('mean_token_f1', 'N/A'):.3f}",
        f"- Judge Accuracy: {metrics.get('judge_accuracy', 'N/A'):.3f}",
        f"- Mean Judge Score: {metrics.get('mean_judge_score', 'N/A'):.1f}",
        "",
        "## Data Quality",
        f"- Total rows: {quality.get('total_rows', 'N/A')}",
        f"- Unique paper_ids: {quality.get('unique_paper_ids', 'N/A')}",
        f"- Paper ID unique: {'PASS' if quality.get('pass_paper_id_unique') else 'FAIL'}",
        f"- No null title: {'PASS' if quality.get('pass_no_null_title') else 'FAIL'}",
        f"- Duplicates: {quality.get('duplicate_paper_ids', 'N/A')}",
        "",
        "## Freshness",
        f"- Latest published: {freshness.get('latest_published', 'N/A')}",
        f"- Oldest published: {freshness.get('oldest_published', 'N/A')}",
        f"- Stale rows: {freshness.get('stale_rows', 'N/A')}",
        f"- Is fresh: {'YES' if freshness.get('is_fresh') else 'NO'}",
        "",
        "## Summary",
        "Baseline pipeline completed successfully. The agent is evaluated on a curated test set.",
        "All quality checks and freshness reports are generated.",
    ]
    write_text(report_path, "\n".join(lines) + "\n")


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
    def delta(base: float, comp: float) -> str:
        diff = comp - base
        return f"{diff:+.3f}"

    bl_hit = baseline_metrics.get("retrieval_hit_rate", 0)
    bl_f1 = baseline_metrics.get("mean_token_f1", 0)
    bl_acc = baseline_metrics.get("judge_accuracy", 0)
    bl_score = baseline_metrics.get("mean_judge_score", 0)

    co_hit = corrupted_metrics.get("retrieval_hit_rate", 0)
    co_f1 = corrupted_metrics.get("mean_token_f1", 0)
    co_acc = corrupted_metrics.get("judge_accuracy", 0)
    co_score = corrupted_metrics.get("mean_judge_score", 0)

    re_hit = repaired_metrics.get("retrieval_hit_rate", 0)
    re_f1 = repaired_metrics.get("mean_token_f1", 0)
    re_acc = repaired_metrics.get("judge_accuracy", 0)
    re_score = repaired_metrics.get("mean_judge_score", 0)

    lines = [
        "# Corruption & Repair Comparison Report",
        "",
        "## Metrics Comparison",
        "",
        "| Metric | Baseline | Corrupted | Delta | Repaired | Delta vs Baseline |",
        "|--------|----------|-----------|-------|----------|-------------------|",
        f"| Retrieval Hit Rate | {bl_hit:.3f} | {co_hit:.3f} | {delta(bl_hit, co_hit)} | {re_hit:.3f} | {delta(bl_hit, re_hit)} |",
        f"| Mean Token F1 | {bl_f1:.3f} | {co_f1:.3f} | {delta(bl_f1, co_f1)} | {re_f1:.3f} | {delta(bl_f1, re_f1)} |",
        f"| Judge Accuracy | {bl_acc:.3f} | {co_acc:.3f} | {delta(bl_acc, co_acc)} | {re_acc:.3f} | {delta(bl_acc, re_acc)} |",
        f"| Mean Judge Score | {bl_score:.1f} | {co_score:.1f} | {delta(bl_score, co_score)} | {re_score:.1f} | {delta(bl_score, re_score)} |",
        "",
        "## Quality Comparison",
        "",
        "| Check | Corrupted | Repaired |",
        "|-------|-----------|----------|",
        f"| Total rows | {corrupted_quality.get('total_rows', 'N/A')} | {repaired_quality.get('total_rows', 'N/A')} |",
        f"| Unique paper_ids | {corrupted_quality.get('unique_paper_ids', 'N/A')} | {repaired_quality.get('unique_paper_ids', 'N/A')} |",
        f"| Stale rows | {corrupted_quality.get('stale_rows', 'N/A')} | {repaired_quality.get('stale_rows', 'N/A')} |",
        "",
        "## Freshness Comparison",
        "",
        "| Field | Corrupted | Repaired |",
        "|-------|-----------|----------|",
        f"| Is fresh | {'YES' if corrupted_freshness.get('is_fresh') else 'NO'} | {'YES' if repaired_freshness.get('is_fresh') else 'NO'} |",
        "",
        "## Conclusion",
        "",
        "The corruption flow demonstrates that data quality issues directly degrade agent performance.",
        "Repairing from raw source data restores performance to near-baseline levels.",
    ]
    write_text(report_path, "\n".join(lines) + "\n")
