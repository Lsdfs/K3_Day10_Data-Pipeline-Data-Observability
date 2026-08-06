from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _check(
    name: str,
    dimension: str,
    failed_count: int,
    total_rows: int,
    observed: Any,
    threshold: str,
    message: str,
) -> dict[str, Any]:
    passed = failed_count == 0
    return {
        "name": name,
        "dimension": dimension,
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "observed": observed,
        "threshold": threshold,
        "failed_count": int(failed_count),
        "failed_rate": round(failed_count / total_rows, 6) if total_rows else (0.0 if passed else 1.0),
        "message": message,
    }


def run_data_quality_checks(
    df: pd.DataFrame, settings: Settings, report_name: str
) -> dict[str, Any]:
    """Run explicit data-contract checks and persist machine-readable evidence."""
    total = len(df)
    required = {
        "paper_id", "title", "summary", "authors_joined", "categories_joined",
        "published", "age_days", "abs_url", "text_for_embedding",
    }
    missing = sorted(required - set(df.columns))
    checks = [
        _check(
            "dataset_not_empty", "completeness", 0 if total > 0 else 1, total,
            total, "> 0 rows", "Dataset must contain at least one row.",
        ),
        _check(
            "required_columns", "validity", len(missing), max(total, 1), missing,
            "no missing required columns", "All pipeline contract columns must exist.",
        ),
    ]
    if not missing and total:
        def text_series(column: str) -> pd.Series:
            return df[column].fillna("").astype(str).str.strip()

        ids = text_series("paper_id")
        titles = text_series("title")
        summaries = text_series("summary")
        embedding_text = text_series("text_for_embedding")
        authors = text_series("authors_joined")
        categories = text_series("categories_joined")
        dates = pd.to_datetime(df["published"], utc=True, errors="coerce")
        ages = pd.to_numeric(df["age_days"], errors="coerce")
        urls = text_series("abs_url")
        duplicate_rows = int(ids.duplicated(keep=False).sum())
        empty_ids = int(ids.eq("").sum())
        empty_titles = int(titles.eq("").sum())
        empty_summaries = int(summaries.eq("").sum())
        short_summaries = int(summaries.str.len().lt(40).sum())
        empty_embedding = int(embedding_text.eq("").sum())
        invalid_dates = int(dates.isna().sum())
        invalid_ages = int((ages.isna() | ages.lt(0)).sum())
        stale_rows = int(ages.gt(settings.freshness_threshold_days).sum())
        empty_authors = int(authors.isin(["", "Unknown"]).sum())
        empty_categories = int(categories.eq("").sum())
        invalid_urls = int((~urls.str.match(r"^https?://[^\s]+$", na=False)).sum())
        checks.extend([
            _check("paper_id_completeness", "completeness", empty_ids, total, empty_ids, "0 empty", "Every row needs a stable document ID."),
            _check("paper_id_uniqueness", "uniqueness", duplicate_rows, total, duplicate_rows, "0 duplicate rows", "Document IDs must be unique."),
            _check("duplicate_rate", "uniqueness", duplicate_rows, total, round(duplicate_rows / total, 6), "0.0", "Duplicate rate is measured across paper_id."),
            _check("title_completeness", "completeness", empty_titles, total, empty_titles, "0 empty", "Titles are required for retrieval and lookup."),
            _check("summary_completeness", "completeness", empty_summaries, total, empty_summaries, "0 empty", "Summaries are required for answer extraction."),
            _check("summary_length", "completeness", short_summaries, total, round((total - short_summaries) / total, 6), "100% >= 40 chars", "Summaries should contain meaningful text."),
            _check("embedding_text_completeness", "validity", empty_embedding, total, empty_embedding, "0 empty", "Embedding text must be present."),
            _check("published_parseability", "validity", invalid_dates, total, invalid_dates, "0 invalid", "Publication dates must parse as ISO dates."),
            _check("age_days_validity", "validity", invalid_ages, total, invalid_ages, "0 null/negative", "age_days must be numeric and non-negative."),
            _check("stale_rate", "timeliness", stale_rows, total, round(stale_rows / total, 6), f"0 rows > {settings.freshness_threshold_days} days", "No row should exceed the freshness threshold."),
            _check("authors_completeness", "completeness", empty_authors, total, empty_authors, "0 unknown/empty", "Authors should be available from source metadata."),
            _check("categories_completeness", "completeness", empty_categories, total, empty_categories, "0 empty", "Categories must have a normalized value."),
            _check("abstract_url_validity", "validity", invalid_urls, total, invalid_urls, "0 invalid URL", "abs_url must be an HTTP(S) URL."),
        ])
    payload = {
        "report_name": report_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows": total,
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "passed": all(item["passed"] for item in checks),
        "passed_checks": sum(item["passed"] for item in checks),
        "failed_checks": sum(not item["passed"] for item in checks),
        "checks": checks,
        "great_expectations": {"status": "NOT_APPLICABLE", "message": "Core checks run without a GX checkpoint."},
    }
    write_json(settings.paths.quality_dir / f"{report_name}.json", payload)
    return payload


def build_freshness_report(
    df: pd.DataFrame, settings: Settings, report_path
) -> dict[str, Any]:
    """Build record-level freshness statistics from publication dates and age_days."""
    total = len(df)
    published = pd.to_datetime(df.get("published", pd.Series(dtype="object")), utc=True, errors="coerce")
    ages = pd.to_numeric(df.get("age_days", pd.Series(dtype="float64")), errors="coerce")
    stale_rows = int(ages.gt(settings.freshness_threshold_days).sum())
    invalid_rows = int(published.isna().sum() + ages.isna().sum())
    is_fresh = total > 0 and stale_rows == 0 and invalid_rows == 0 and not ages.lt(0).any()
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows": total,
        "latest_published": published.max().date().isoformat() if published.notna().any() else None,
        "oldest_published": published.min().date().isoformat() if published.notna().any() else None,
        "stale_rows": stale_rows,
        "stale_rate": round(stale_rows / total, 6) if total else 0.0,
        "invalid_rows": invalid_rows,
        "threshold_days": settings.freshness_threshold_days,
        "median_age_days": round(float(ages.median()), 2) if ages.notna().any() else None,
        "max_age_days": int(ages.max()) if ages.notna().any() else None,
        "is_fresh": bool(is_fresh),
        "status": "fresh" if is_fresh else "stale_or_invalid",
    }
    write_json(report_path, payload)
    return payload
