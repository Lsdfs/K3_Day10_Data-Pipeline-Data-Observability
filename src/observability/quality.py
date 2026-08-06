from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    total = len(df)

    unique_paper_ids = df["paper_id"].nunique() if "paper_id" in df.columns else 0
    null_paper_ids = int(df["paper_id"].isna().sum()) if "paper_id" in df.columns else total
    null_titles = int(df["title"].isna().sum()) if "title" in df.columns else total
    empty_summaries = int((df.get("summary") == "").sum()) if "summary" in df.columns else 0
    min_summary_chars = int(df.get("summary_chars", pd.Series([0])).min()) if "summary_chars" in df.columns else 0
    max_summary_chars = int(df.get("summary_chars", pd.Series([0])).max()) if "summary_chars" in df.columns else 0
    stale_count = int((df.get("age_days", pd.Series([0])) > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0
    duplicate_paper_ids = total - unique_paper_ids if "paper_id" in df.columns else 0

    checks = {
        "total_rows": total,
        "unique_paper_ids": unique_paper_ids,
        "pass_paper_id_unique": unique_paper_ids == total,
        "pass_no_null_paper_id": null_paper_ids == 0,
        "pass_no_null_title": null_titles == 0,
        "empty_summaries": empty_summaries,
        "min_summary_chars": min_summary_chars,
        "max_summary_chars": max_summary_chars,
        "stale_rows": stale_count,
        "pass_stale_check": stale_count == 0,
        "duplicate_paper_ids": duplicate_paper_ids,
        "pass_no_duplicates": duplicate_paper_ids == 0,
    }

    output_path = settings.paths.quality_dir / f"{report_name}_quality.json"
    write_json(output_path, checks)

    return checks


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    if "published" not in df.columns or df.empty:
        result = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": len(df),
            "is_fresh": len(df) == 0,
        }
        write_json(report_path, result)
        return result

    published_dates = pd.to_datetime(df["published"], errors="coerce").dropna()
    latest = published_dates.max().strftime("%Y-%m-%d") if not published_dates.empty else None
    oldest = published_dates.min().strftime("%Y-%m-%d") if not published_dates.empty else None
    stale = int((df.get("age_days", pd.Series([0])) > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0

    result = {
        "latest_published": latest,
        "oldest_published": oldest,
        "stale_rows": stale,
        "total_rows": len(df),
        "is_fresh": stale == 0 and len(df) > 0,
    }

    write_json(report_path, result)
    return result
