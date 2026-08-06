from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.config import load_settings
from ingestion.crossref import PaperRecord


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_EMBEDDING_FALLBACK", "true")
    monkeypatch.setenv("EMBEDDING_BACKEND", "hashing")
    monkeypatch.setenv("ENABLE_LLM_JUDGE", "false")
    monkeypatch.setenv("RUN_RAGAS", "false")
    return load_settings(project_dir=tmp_path)


@pytest.fixture
def paper_records() -> list[PaperRecord]:
    today = datetime.now(UTC).date()
    records = []
    for index in range(12):
        published = (today - timedelta(days=index + 1)).isoformat()
        records.append(PaperRecord(
            paper_id=f"10.1000/{index}",
            title=f"Paper {index} about retrieval systems",
            summary=(
                f"This is a sufficiently detailed abstract for scholarly paper {index}; "
                "it presents reproducible retrieval and evaluation findings."
            ),
            authors=[f"Author {index}"],
            categories=["Computer Science", "Information Retrieval"],
            primary_category="Computer Science",
            published=published,
            updated=published,
            abs_url=f"https://doi.org/10.1000/{index}",
            pdf_url="",
            comment="",
        ))
    return records


@pytest.fixture
def clean_df(paper_records):
    from ingestion.cleaning import build_clean_dataframe
    return build_clean_dataframe(paper_records, datetime.now(UTC))
