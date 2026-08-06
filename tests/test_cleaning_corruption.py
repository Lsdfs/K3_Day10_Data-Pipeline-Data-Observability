from __future__ import annotations

from dataclasses import replace

import pandas as pd

from core.utils import read_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe


def test_cleaning_deduplicates_without_mutating_input(paper_records):
    records = paper_records + [replace(paper_records[0])]
    snapshot = list(records)
    frame = build_clean_dataframe(records, pd.Timestamp.now(tz="UTC").to_pydatetime())
    assert records == snapshot
    assert len(frame) == len(paper_records)
    assert frame["paper_id"].is_unique
    assert frame["text_for_embedding"].str.contains("Title:").all()
    assert {"authors_joined", "categories_joined", "summary_chars", "age_days"} <= set(frame)


def test_corruption_is_deterministic_logged_and_non_mutating(clean_df, tmp_path):
    original = clean_df.copy(deep=True)
    first = corrupt_clean_dataframe(clean_df, tmp_path / "first.json", seed=17)
    second = corrupt_clean_dataframe(clean_df, tmp_path / "second.json", seed=17)
    pd.testing.assert_frame_equal(clean_df, original)
    pd.testing.assert_frame_equal(first, second)
    assert first["paper_id"].duplicated(keep=False).any()
    assert (first["summary"] == "").any()
    assert first["summary"].str.contains("corrupt-token").any()
    log = read_json(tmp_path / "first.json")
    assert log["seed"] == 17 and len(log["scenarios"]) == 6
