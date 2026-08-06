from __future__ import annotations

from typing import Any

from core.utils import write_text


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _metric_rows(metrics: dict[str, Any]) -> str:
    names = ["samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    return "\n".join(f"| `{name}` | {_fmt(metrics.get(name, 'N/A'))} |" for name in names)


def _quality_rows(quality: dict[str, Any]) -> str:
    return "\n".join(
        f"| {check['name']} | {check['dimension']} | {'PASS' if check['passed'] else 'FAIL'} | "
        f"{_fmt(check['observed'])} | {check['expectation']} |"
        for check in quality.get("checks", [])
    )


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write an evidence-based baseline report from generated payloads."""
    report = f"""# Báo cáo baseline pipeline

## Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | {source_summary.get('source', 'N/A')} |
| Endpoint | {source_summary.get('endpoint', 'N/A')} |
| Query | {source_summary.get('query', 'N/A')} |
| Filter | {source_summary.get('filter', 'N/A')} |
| Raw records | {source_summary.get('records', 0)} |
| Chế độ | {source_summary.get('mode', 'N/A')} |

## Evaluation metrics

| Metric | Giá trị |
| --- | ---: |
{_metric_rows(metrics)}

Ragas: `{_fmt(metrics.get('ragas', 'N/A'))}`.

## Data quality

Trạng thái tổng thể: **{'PASS' if quality.get('passed') else 'FAIL'}** ({quality.get('passed_checks', 0)} pass, {quality.get('failed_checks', 0)} fail).

| Check | Dimension | Trạng thái | Observed | Expectation |
| --- | --- | --- | ---: | --- |
{_quality_rows(quality)}

## Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Latest published | {freshness.get('latest_published')} |
| Oldest published | {freshness.get('oldest_published')} |
| Stale rows | {freshness.get('stale_rows')} / {freshness.get('total_rows')} |
| Threshold | {freshness.get('freshness_threshold_days')} ngày |
| Status | **{freshness.get('status')}** |

## Kết luận

Baseline đã tạo đủ raw, clean, embedding/index, evaluation, quality, freshness và answer artifacts. Các số liệu trên được lấy trực tiếp từ artifact của lần chạy hiện tại.
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
    """Write the baseline/corrupted/repaired comparison report."""
    metric_names = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    rows = []
    for name in metric_names:
        baseline = float(baseline_metrics.get(name, 0.0))
        corrupted = float(corrupted_metrics.get(name, 0.0))
        repaired = float(repaired_metrics.get(name, 0.0))
        rows.append(
            f"| `{name}` | {baseline:.4f} | {corrupted:.4f} | {repaired:.4f} | "
            f"{corrupted - baseline:+.4f} | {repaired - corrupted:+.4f} |"
        )
    report = f"""# Báo cáo corruption và repair

## So sánh metrics

| Metric | Baseline | Corrupted | Repaired | Corruption Δ | Repair Δ |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

## Data observability

| Trạng thái | Quality | Pass/Fail checks | Freshness | Stale rows |
| --- | --- | ---: | --- | ---: |
| Corrupted | {'PASS' if corrupted_quality.get('passed') else 'FAIL'} | {corrupted_quality.get('passed_checks', 0)}/{corrupted_quality.get('failed_checks', 0)} | {corrupted_freshness.get('status')} | {corrupted_freshness.get('stale_rows', 0)} |
| Repaired | {'PASS' if repaired_quality.get('passed') else 'FAIL'} | {repaired_quality.get('passed_checks', 0)}/{repaired_quality.get('failed_checks', 0)} | {repaired_freshness.get('status')} | {repaired_freshness.get('stale_rows', 0)} |

## Phân tích nhân quả

1. Xóa bản ghi mới, làm rỗng summary, chèn noise, cắt title, làm cũ ngày và tạo duplicate làm các quality/freshness signal chuyển xấu; cùng test set cố định ghi nhận thay đổi ở retrieval và answer metrics.
2. Repair xây lại dữ liệu từ raw snapshot đáng tin cậy, không chỉnh trực tiếp dữ liệu corrupted. Quality/freshness và agent metrics vì vậy được đo lại độc lập trên index repaired.

Nếu một metric không giảm, kết luận phù hợp là corruption đó chưa tác động đến metric trên test set/top-k hiện tại; không suy diễn tác động khi số liệu không hỗ trợ.
"""
    write_text(report_path, report)
