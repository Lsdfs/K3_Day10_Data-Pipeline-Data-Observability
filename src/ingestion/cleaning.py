from __future__ import annotations

from datetime import UTC, datetime
import json

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


CLEAN_COLUMNS = [
    "paper_id", "title", "summary", "authors", "categories", "primary_category",
    "published", "updated", "abs_url", "pdf_url", "comment", "authors_joined",
    "categories_joined", "summary_chars", "age_days", "text_for_embedding",
]


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Return a deterministic embedding-ready dataframe without mutating raw records."""
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=UTC)
    else:
        run_date = run_date.astimezone(UTC)
    cleaned: list[dict] = []
    for record in records:
        paper_id = normalize_whitespace(str(record.paper_id)).lower()
        title = normalize_whitespace(str(record.title))
        summary = normalize_whitespace(str(record.summary))
        if not paper_id or not title or not summary:
            continue
        published = pd.to_datetime(record.published, utc=True, errors="coerce")
        updated = pd.to_datetime(record.updated, utc=True, errors="coerce")
        if pd.isna(published):
            continue
        if pd.isna(updated):
            updated = published
        authors = list(dict.fromkeys(
            text for value in record.authors if (text := normalize_whitespace(str(value)))
        ))
        categories = list(dict.fromkeys(
            text for value in record.categories if (text := normalize_whitespace(str(value)))
        ))
        if not categories:
            categories = [normalize_whitespace(record.primary_category) or "Uncategorized"]
        authors_joined = compact_join(authors) or "Unknown"
        categories_joined = compact_join(categories)
        published_text = published.date().isoformat()
        updated_text = updated.date().isoformat()
        age_days = (run_date.date() - published.date()).days
        text_for_embedding = normalize_whitespace(
            f"Title: {title}. Abstract: {summary} Authors: {authors_joined}. "
            f"Categories: {categories_joined}. Published: {published_text}."
        )
        cleaned.append({
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": json.dumps(authors, ensure_ascii=False),
            "categories": json.dumps(categories, ensure_ascii=False),
            "primary_category": categories[0],
            "published": published_text,
            "updated": updated_text,
            "abs_url": normalize_whitespace(record.abs_url),
            "pdf_url": normalize_whitespace(record.pdf_url),
            "comment": normalize_whitespace(record.comment),
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": len(summary),
            "age_days": age_days,
            "text_for_embedding": text_for_embedding,
        })
    frame = pd.DataFrame(cleaned, columns=CLEAN_COLUMNS)
    if frame.empty:
        raise ValueError(
            "Cleaning produced no rows; paper_id, title, summary and a parseable published date are required."
        )
    return (
        frame.drop_duplicates(subset=["paper_id"], keep="first")
        .sort_values(["published", "paper_id"], ascending=[False, True], kind="stable")
        .reset_index(drop=True)
    )
