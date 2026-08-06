from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _empty_mask(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype(str).str.strip().eq("")


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run auditable quality checks over the clean-data contract."""
    required = {"paper_id", "title", "summary", "published", "age_days", "text_for_embedding"}
    missing_columns = sorted(required - set(df.columns))
    total_rows = len(df)

    def check(name: str, dimension: str, passed: bool, observed: Any, expectation: str) -> dict[str, Any]:
        return {
            "name": name,
            "dimension": dimension,
            "passed": bool(passed),
            "observed": observed,
            "expectation": expectation,
        }

    checks: list[dict[str, Any]] = []
    if missing_columns:
        checks.append(check("required_columns", "validity", False, missing_columns, "all clean-schema columns present"))
        null_paper_ids = null_titles = empty_summaries = duplicate_paper_ids = stale_rows = 0
        unique_paper_ids = 0
    else:
        paper_id_empty = _empty_mask(df["paper_id"])
        title_empty = _empty_mask(df["title"])
        summary_empty = _empty_mask(df["summary"])
        embedding_empty = _empty_mask(df["text_for_embedding"])
        published = pd.to_datetime(df["published"], errors="coerce", utc=True, format="mixed")
        age_days = pd.to_numeric(df["age_days"], errors="coerce")

        null_paper_ids = int(paper_id_empty.sum())
        null_titles = int(title_empty.sum())
        empty_summaries = int(summary_empty.sum())
        duplicate_paper_ids = int(df["paper_id"].astype(str).duplicated(keep=False).sum())
        unique_paper_ids = int(df["paper_id"].nunique(dropna=True))
        stale_rows = int((age_days > settings.freshness_threshold_days).sum())
        invalid_dates = int(published.isna().sum())
        invalid_age_days = int(age_days.isna().sum())
        summary_chars = df["summary"].fillna("").astype(str).str.len()
        min_summary_chars = int(summary_chars.min()) if total_rows else 0
        max_summary_chars = int(summary_chars.max()) if total_rows else 0
        long_summary_ratio = float((summary_chars >= 40).mean()) if total_rows else 0.0

        checks = [
            check("minimum_row_count", "completeness", total_rows >= 4, total_rows, ">= 4 rows"),
            check("paper_id_not_null", "completeness", null_paper_ids == 0, null_paper_ids, "0 empty IDs"),
            check("paper_id_unique", "uniqueness", duplicate_paper_ids == 0, duplicate_paper_ids, "0 duplicated ID rows"),
            check("title_not_null", "completeness", null_titles == 0, null_titles, "0 empty titles"),
            check("summary_not_null", "completeness", empty_summaries == 0, empty_summaries, "0 empty summaries"),
            check("summary_length", "completeness", long_summary_ratio >= 0.9, round(long_summary_ratio, 4), ">= 90% summaries have >= 40 characters"),
            check("embedding_text_not_null", "validity", not embedding_empty.any(), int(embedding_empty.sum()), "0 empty embedding texts"),
            check("published_date_valid", "validity", invalid_dates == 0, invalid_dates, "0 invalid publication dates"),
            check("age_days_valid", "validity", invalid_age_days == 0, invalid_age_days, "0 invalid age_days values"),
            check("freshness_age_days", "timeliness", stale_rows == 0, stale_rows, f"0 rows older than {settings.freshness_threshold_days} days"),
        ]

    payload = {
        "report_name": report_name,
        "total_rows": total_rows,
        "unique_paper_ids": unique_paper_ids,
        "null_paper_ids": null_paper_ids,
        "null_titles": null_titles,
        "empty_summaries": empty_summaries,
        "duplicate_paper_ids": duplicate_paper_ids,
        "stale_rows": stale_rows,
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
        "passed_checks": sum(item["passed"] for item in checks),
        "failed_checks": sum(not item["passed"] for item in checks),
    }
    # Backward-compatible top-level flags consumed by the existing report template.
    payload.update({
        "pass_paper_id_unique": duplicate_paper_ids == 0 and not missing_columns,
        "pass_no_null_paper_id": null_paper_ids == 0 and not missing_columns,
        "pass_no_null_title": null_titles == 0 and not missing_columns,
        "pass_no_duplicates": duplicate_paper_ids == 0 and not missing_columns,
    })
    write_json(settings.paths.quality_dir / f"{report_name}_quality.json", payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Persist freshness evidence from publication and source-update timestamps."""
    total_rows = len(df)
    if "published" not in df.columns:
        published = pd.Series(dtype="datetime64[ns, UTC]")
    else:
        published = pd.to_datetime(df["published"], errors="coerce", utc=True, format="mixed")
    updated = pd.to_datetime(df["updated"], errors="coerce", utc=True, format="mixed") if "updated" in df.columns else pd.Series(dtype="datetime64[ns, UTC]")
    age_days = pd.to_numeric(df["age_days"], errors="coerce") if "age_days" in df.columns else pd.Series(dtype=float)
    stale_rows = int((age_days > settings.freshness_threshold_days).sum())
    invalid_date_rows = int(published.isna().sum()) if total_rows else 0
    is_fresh = bool(total_rows > 0 and invalid_date_rows == 0 and stale_rows == 0)

    def iso_date(value: pd.Timestamp | Any) -> str | None:
        return value.date().isoformat() if pd.notna(value) else None

    payload = {
        "latest_published": iso_date(published.max()) if not published.empty else None,
        "oldest_published": iso_date(published.min()) if not published.empty else None,
        "latest_source_updated": iso_date(updated.max()) if not updated.empty else None,
        "invalid_date_rows": invalid_date_rows,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": is_fresh,
        "status": "fresh" if is_fresh else "stale_or_invalid",
    }
    write_json(report_path, payload)
    return payload
