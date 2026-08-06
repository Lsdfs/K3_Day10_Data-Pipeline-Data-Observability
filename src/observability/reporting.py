from __future__ import annotations

from typing import Any

from core.utils import write_text


def _format(value: Any) -> str:
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def _metrics_rows(metrics: dict[str, Any]) -> str:
    names = ["samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score", "judge_mode"]
    return "\n".join(f"| `{name}` | {_format(metrics.get(name, 'N/A'))} |" for name in names)


def _quality_rows(quality: dict[str, Any]) -> str:
    return "\n".join(
        f"| {item['name']} | {item['dimension']} | {item['status']} | "
        f"{_format(item['observed'])} | {item['threshold']} |"
        for item in quality.get("checks", [])
    )


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    report = f"""# Báo cáo baseline pipeline

## Nguồn và cấu hình

| Thuộc tính | Giá trị |
| --- | --- |
| Source | {source_summary.get('source')} |
| Endpoint | {source_summary.get('endpoint')} |
| Query | {source_summary.get('query')} |
| Filter | {source_summary.get('filter')} |
| Raw/Clean rows | {source_summary.get('raw_records')} / {source_summary.get('clean_records')} |
| Source mode | {source_summary.get('mode')} |
| Embedding backend | {source_summary.get('embedding_backend')} |
| Collection | {source_summary.get('collection')} |

## Evaluation

| Metric | Giá trị |
| --- | ---: |
{_metrics_rows(metrics)}

Ragas: `{_format(metrics.get('ragas', 'N/A'))}`.

## Data quality

Overall: **{quality.get('status')}** — {quality.get('passed_checks')} pass, {quality.get('failed_checks')} fail.

| Check | Dimension | Status | Observed | Threshold |
| --- | --- | --- | --- | --- |
{_quality_rows(quality)}

## Freshness

| Signal | Giá trị |
| --- | --- |
| Latest / oldest | {freshness.get('latest_published')} / {freshness.get('oldest_published')} |
| Stale rows/rate | {freshness.get('stale_rows')} / {freshness.get('stale_rate')} |
| Median / max age | {freshness.get('median_age_days')} / {freshness.get('max_age_days')} ngày |
| Threshold | {freshness.get('threshold_days')} ngày |
| Status | **{freshness.get('status')}** |

Các số liệu được đọc trực tiếp từ output của lần chạy, không hard-code trong pipeline.
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
    names = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    rows = []
    for name in names:
        baseline = float(baseline_metrics[name])
        corrupted = float(corrupted_metrics[name])
        repaired = float(repaired_metrics[name])
        rows.append(
            f"| `{name}` | {baseline:.4f} | {corrupted:.4f} | {repaired:.4f} | "
            f"{corrupted - baseline:+.4f} | {repaired - corrupted:+.4f} |"
        )
    report = f"""# Báo cáo corruption và repair

## Metrics comparison

| Metric | Baseline | Corrupted | Repaired | Corruption Δ | Repair Δ |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

## Observability comparison

| State | Quality | Pass/Fail checks | Freshness | Stale rows/rate |
| --- | --- | ---: | --- | ---: |
| Corrupted | {corrupted_quality.get('status')} | {corrupted_quality.get('passed_checks')}/{corrupted_quality.get('failed_checks')} | {corrupted_freshness.get('status')} | {corrupted_freshness.get('stale_rows')}/{corrupted_freshness.get('stale_rate')} |
| Repaired | {repaired_quality.get('status')} | {repaired_quality.get('passed_checks')}/{repaired_quality.get('failed_checks')} | {repaired_freshness.get('status')} | {repaired_freshness.get('stale_rows')}/{repaired_freshness.get('stale_rate')} |

## Kết luận có bằng chứng

Corruption được đánh giá bằng cùng test-set hash với baseline; repair dựng lại dữ liệu từ raw snapshot rồi chạy lại cleaning, index, evaluation và observability. Chỉ những thay đổi thể hiện trong bảng metrics mới được dùng làm kết luận.
"""
    write_text(report_path, report)
