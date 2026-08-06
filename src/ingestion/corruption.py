from __future__ import annotations

from datetime import timedelta

import pandas as pd

from core.utils import normalize_whitespace, write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Create deterministic, auditable corruption scenarios without mutating input."""
    if len(df) < 8:
        raise ValueError("At least 8 cleaned rows are required for the corruption experiment.")
    result = df.copy(deep=True).reset_index(drop=True)
    log: list[dict] = []

    drop_count = max(1, len(result) // 6)
    latest_indices = result.sort_values("published", ascending=False).head(drop_count).index.tolist()
    dropped_ids = result.loc[latest_indices, "paper_id"].astype(str).tolist()
    result = result.drop(index=latest_indices).reset_index(drop=True)
    log.append({"type": "drop_latest_records", "count": len(dropped_ids), "paper_ids": dropped_ids})

    usable = len(result)
    scenario_indices = list(range(min(4, usable)))
    summary_index = scenario_indices[0]
    noise_index = scenario_indices[1]
    title_index = scenario_indices[2]
    stale_index = scenario_indices[3]

    summary_id = str(result.at[summary_index, "paper_id"])
    result.at[summary_index, "summary"] = ""
    result.at[summary_index, "summary_chars"] = 0
    log.append({"type": "blank_summary", "count": 1, "paper_ids": [summary_id]})

    noise_id = str(result.at[noise_index, "paper_id"])
    noise = " zxqv corrupt-token repeated-noise " * 20
    result.at[noise_index, "summary"] = normalize_whitespace(str(result.at[noise_index, "summary"]) + noise)
    result.at[noise_index, "summary_chars"] = len(str(result.at[noise_index, "summary"]))
    log.append({"type": "inject_noise", "count": 1, "paper_ids": [noise_id], "noise_repetitions": 20})

    title_id = str(result.at[title_index, "paper_id"])
    original_title = str(result.at[title_index, "title"])
    result.at[title_index, "title"] = original_title[: max(1, min(12, len(original_title) // 3))]
    log.append({"type": "truncate_title", "count": 1, "paper_ids": [title_id]})

    stale_id = str(result.at[stale_index, "paper_id"])
    stale_date = pd.to_datetime(result.at[stale_index, "published"], errors="raise") - timedelta(days=3650)
    result.at[stale_index, "published"] = stale_date.date().isoformat()
    result.at[stale_index, "age_days"] = int(result.at[stale_index, "age_days"]) + 3650
    log.append({"type": "stale_publication_date", "count": 1, "paper_ids": [stale_id], "days_shifted": 3650})

    duplicate = result.iloc[[min(4, len(result) - 1)]].copy()
    duplicate_id = str(duplicate.iloc[0]["paper_id"])
    result = pd.concat([result, duplicate], ignore_index=True)
    log.append({"type": "duplicate_row", "count": 1, "paper_ids": [duplicate_id]})

    result["text_for_embedding"] = result.apply(
        lambda row: normalize_whitespace(
            f"Title: {row['title']}. Abstract: {row['summary']} Authors: {row['authors_joined']}. "
            f"Categories: {row['categories_joined']}. Published: {row['published']}."
        ),
        axis=1,
    )
    write_json(
        output_log_path,
        {
            "input_rows": len(df),
            "output_rows": len(result),
            "deterministic": True,
            "scenarios": log,
        },
    )
    return result
