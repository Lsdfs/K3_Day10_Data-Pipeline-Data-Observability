from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import normalize_whitespace, compact_join
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    rows = []
    for r in records:
        summary = normalize_whitespace(r.summary)
        title = normalize_whitespace(r.title)
        if not title:
            continue

        authors_joined = compact_join(r.authors, "; ")
        categories_joined = compact_join(r.categories, "; ")

        published = r.published or ""
        try:
            pub_dt = datetime.strptime(published, "%Y-%m-%d")
            age_days = (run_date - pub_dt).days
        except (ValueError, TypeError):
            pub_dt = None
            age_days = -1

        text_for_embedding = f"Title: {title}. {'Authors: ' + authors_joined + '.' if authors_joined else ''} Summary: {summary}."

        rows.append({
            "paper_id": r.paper_id,
            "title": title,
            "summary": summary,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "primary_category": r.primary_category,
            "published": published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
            "summary_chars": len(summary),
            "age_days": age_days,
            "text_for_embedding": normalize_whitespace(text_for_embedding),
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df = df.drop_duplicates(subset="paper_id", keep="first")
    df = df.sort_values("paper_id").reset_index(drop=True)

    return df
