from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from core.config import load_settings
from ingestion.crossref import PaperRecord


@pytest.fixture
def settings(tmp_path):
    return load_settings(project_dir=tmp_path)


@pytest.fixture
def paper_records() -> list[PaperRecord]:
    today = datetime.now(UTC).date()
    records = []
    for index in range(10):
        published = (today - timedelta(days=index + 1)).isoformat()
        records.append(
            PaperRecord(
                paper_id=f"10.1000/{index}",
                title=f"Paper {index} about retrieval",
                summary=f"This is a sufficiently detailed abstract for scholarly paper number {index} and its retrieval findings.",
                authors=[f"Author {index}"],
                categories=["Computer Science", "Information Retrieval"],
                primary_category="Computer Science",
                published=published,
                updated=published,
                abs_url=f"https://doi.org/10.1000/{index}",
                pdf_url="",
                comment="",
            )
        )
    return records


@pytest.fixture
def clean_df(paper_records):
    from ingestion.cleaning import build_clean_dataframe

    return build_clean_dataframe(paper_records, datetime.now(UTC))
