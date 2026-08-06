from __future__ import annotations

import pandas as pd

from core.utils import read_json
from ingestion.corruption import corrupt_clean_dataframe


def test_cleaning_schema_and_deduplication(clean_df):
    assert len(clean_df) == 10
    assert clean_df["paper_id"].is_unique
    assert clean_df["summary_chars"].min() >= 40
    assert clean_df["text_for_embedding"].str.contains("Title:").all()
    assert pd.api.types.is_integer_dtype(clean_df["age_days"])


def test_corruption_is_auditable_and_does_not_mutate_input(clean_df, tmp_path):
    original = clean_df.copy(deep=True)
    log_path = tmp_path / "corruption.json"
    corrupted = corrupt_clean_dataframe(clean_df, log_path)
    pd.testing.assert_frame_equal(clean_df, original)
    assert corrupted["paper_id"].duplicated(keep=False).any()
    assert (corrupted["summary"] == "").any()
    assert corrupted["summary"].str.contains("corrupt-token").any()
    payload = read_json(log_path)
    assert {item["type"] for item in payload["scenarios"]} == {
        "drop_latest_records", "blank_summary", "inject_noise", "truncate_title",
        "stale_publication_date", "duplicate_row",
    }
