from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run transparent data-contract checks and persist their evidence."""
    required = {"paper_id", "title", "summary", "age_days", "text_for_embedding"}
    missing_columns = sorted(required - set(df.columns))
    total_rows = len(df)

    def result(name: str, dimension: str, passed: bool, observed: Any, expectation: str) -> dict[str, Any]:
        return {
            "name": name,
            "dimension": dimension,
            "passed": bool(passed),
            "observed": observed,
            "expectation": expectation,
        }

    if missing_columns:
        checks = [result("required_columns", "validity", False, missing_columns, "no missing required columns")]
    else:
        nonempty_ids = df["paper_id"].fillna("").astype(str).str.strip().ne("")
        nonempty_titles = df["title"].fillna("").astype(str).str.strip().ne("")
        nonempty_text = df["text_for_embedding"].fillna("").astype(str).str.strip().ne("")
        summary_lengths = df["summary"].fillna("").astype(str).str.len()
        long_summary_ratio = float((summary_lengths >= 40).mean()) if total_rows else 0.0
        age_days = pd.to_numeric(df["age_days"], errors="coerce")
        stale_rows = int((age_days > settings.freshness_threshold_days).sum())
        duplicate_count = int(df["paper_id"].duplicated(keep=False).sum())
        checks = [
            result("minimum_row_count", "completeness", total_rows >= 8, total_rows, ">= 8 rows"),
            result("paper_id_not_null", "completeness", bool(nonempty_ids.all()), int((~nonempty_ids).sum()), "0 empty IDs"),
            result("paper_id_unique", "uniqueness", duplicate_count == 0, duplicate_count, "0 rows with duplicate IDs"),
            result("title_not_null", "completeness", bool(nonempty_titles.all()), int((~nonempty_titles).sum()), "0 empty titles"),
            result("summary_length", "completeness", long_summary_ratio >= 0.9, round(long_summary_ratio, 4), ">= 90% summaries have at least 40 characters"),
            result("embedding_text_not_null", "validity", bool(nonempty_text.all()), int((~nonempty_text).sum()), "0 empty embedding texts"),
            result("freshness_age_days", "timeliness", stale_rows == 0, stale_rows, f"0 rows older than {settings.freshness_threshold_days} days"),
        ]
    payload = {
        "report_name": report_name,
        "total_rows": total_rows,
        "passed": all(check["passed"] for check in checks),
        "passed_checks": sum(1 for check in checks if check["passed"]),
        "failed_checks": sum(1 for check in checks if not check["passed"]),
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / f"{report_name}.json", payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize record-level freshness against the configured threshold."""
    published = pd.to_datetime(df.get("published"), utc=True, errors="coerce")
    age_days = pd.to_numeric(df.get("age_days"), errors="coerce")
    invalid_dates = int(published.isna().sum())
    stale_rows = int((age_days > settings.freshness_threshold_days).sum())
    total_rows = len(df)
    payload = {
        "latest_published": published.max().date().isoformat() if total_rows and published.notna().any() else None,
        "oldest_published": published.min().date().isoformat() if total_rows and published.notna().any() else None,
        "stale_rows": stale_rows,
        "invalid_date_rows": invalid_dates,
        "total_rows": total_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": bool(total_rows > 0 and stale_rows == 0 and invalid_dates == 0),
        "status": "fresh" if total_rows > 0 and stale_rows == 0 and invalid_dates == 0 else "stale_or_invalid",
    }
    write_json(report_path, payload)
    return payload
