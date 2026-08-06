from __future__ import annotations

from datetime import UTC, datetime
import json

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize, validate and model raw papers for embedding and monitoring."""
    columns = [
        "paper_id", "title", "summary", "authors", "categories", "primary_category",
        "published", "updated", "abs_url", "pdf_url", "comment", "authors_joined",
        "categories_joined", "summary_chars", "age_days", "text_for_embedding",
    ]
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=UTC)
    else:
        run_date = run_date.astimezone(UTC)

    cleaned: list[dict] = []
    for record in records:
        paper_id = normalize_whitespace(record.paper_id).lower()
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not paper_id or not title or not summary:
            continue
        authors = list(dict.fromkeys(normalize_whitespace(str(item)) for item in record.authors if normalize_whitespace(str(item))))
        categories = list(
            dict.fromkeys(normalize_whitespace(str(item)) for item in record.categories if normalize_whitespace(str(item)))
        )
        if not categories:
            categories = [normalize_whitespace(record.primary_category) or "Uncategorized"]
        published = pd.to_datetime(record.published, utc=True, errors="coerce")
        updated = pd.to_datetime(record.updated, utc=True, errors="coerce")
        if pd.isna(published):
            continue
        if pd.isna(updated):
            updated = published
        published_date = published.date().isoformat()
        updated_date = updated.date().isoformat()
        authors_joined = compact_join(authors) or "Unknown"
        categories_joined = compact_join(categories)
        age_days = max(0, (run_date.date() - published.date()).days)
        text_for_embedding = normalize_whitespace(
            f"Title: {title}. Abstract: {summary} Authors: {authors_joined}. "
            f"Categories: {categories_joined}. Published: {published_date}."
        )
        cleaned.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": json.dumps(authors, ensure_ascii=False),
                "categories": json.dumps(categories, ensure_ascii=False),
                "primary_category": categories[0],
                "published": published_date,
                "updated": updated_date,
                "abs_url": normalize_whitespace(record.abs_url),
                "pdf_url": normalize_whitespace(record.pdf_url),
                "comment": normalize_whitespace(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )
    frame = pd.DataFrame(cleaned, columns=columns)
    if frame.empty:
        raise ValueError("No valid records remained after cleaning; title, summary and published date are required.")
    return (
        frame.drop_duplicates(subset=["paper_id"], keep="first")
        .sort_values(["published", "paper_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
