from __future__ import annotations

from datetime import timedelta
import random

import pandas as pd

from core.utils import normalize_whitespace, write_json


def _rebuild_embedding_text(row: pd.Series) -> str:
    return normalize_whitespace(
        f"Title: {row['title']}. Abstract: {row['summary']} Authors: {row['authors_joined']}. "
        f"Categories: {row['categories_joined']}. Published: {row['published']}."
    )


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path,
    seed: int = 2026,
) -> pd.DataFrame:
    """Apply deterministic, logged corruption scenarios to a deep copy of baseline data."""
    if len(df) < 8:
        raise ValueError("At least 8 clean rows are required for the corruption experiment.")
    required = {
        "paper_id", "title", "summary", "published", "age_days", "authors_joined",
        "categories_joined", "summary_chars", "text_for_embedding",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Cannot corrupt dataframe; missing columns: {sorted(missing)}")
    result = df.copy(deep=True).reset_index(drop=True)
    scenarios: list[dict] = []

    drop_count = max(1, len(result) // 6)
    drop_indices = result.sort_values("published", ascending=False).head(drop_count).index.tolist()
    dropped_ids = result.loc[drop_indices, "paper_id"].astype(str).tolist()
    result = result.drop(index=drop_indices).reset_index(drop=True)
    scenarios.append({"type": "drop_latest_records", "count": len(dropped_ids), "paper_ids": dropped_ids})

    rng = random.Random(seed)
    mutation_indices = rng.sample(range(len(result)), 4)
    summary_index, noise_index, title_index, stale_index = mutation_indices

    summary_id = str(result.at[summary_index, "paper_id"])
    result.at[summary_index, "summary"] = ""
    result.at[summary_index, "summary_chars"] = 0
    scenarios.append({"type": "blank_summary", "count": 1, "paper_ids": [summary_id]})

    noise_id = str(result.at[noise_index, "paper_id"])
    noise_repetitions = 12
    result.at[noise_index, "summary"] = normalize_whitespace(
        str(result.at[noise_index, "summary"]) + (" zxqv-corrupt-token" * noise_repetitions)
    )
    result.at[noise_index, "summary_chars"] = len(str(result.at[noise_index, "summary"]))
    scenarios.append({
        "type": "inject_noise", "count": 1, "paper_ids": [noise_id],
        "noise_repetitions": noise_repetitions,
    })

    title_id = str(result.at[title_index, "paper_id"])
    original_title = str(result.at[title_index, "title"])
    result.at[title_index, "title"] = original_title[:max(1, min(12, len(original_title) // 3))]
    scenarios.append({"type": "truncate_title", "count": 1, "paper_ids": [title_id]})

    stale_id = str(result.at[stale_index, "paper_id"])
    stale_days = 3650
    shifted = pd.to_datetime(result.at[stale_index, "published"], errors="raise") - timedelta(days=stale_days)
    result.at[stale_index, "published"] = shifted.date().isoformat()
    result.at[stale_index, "age_days"] = int(result.at[stale_index, "age_days"]) + stale_days
    scenarios.append({
        "type": "stale_publication_date", "count": 1, "paper_ids": [stale_id],
        "days_shifted": stale_days,
    })

    duplicate_index = rng.randrange(len(result))
    duplicate = result.iloc[[duplicate_index]].copy(deep=True)
    duplicate_id = str(duplicate.iloc[0]["paper_id"])
    result = pd.concat([result, duplicate], ignore_index=True)
    scenarios.append({"type": "duplicate_row", "count": 1, "paper_ids": [duplicate_id]})

    result["text_for_embedding"] = result.apply(_rebuild_embedding_text, axis=1)
    write_json(output_log_path, {
        "seed": seed,
        "deterministic": True,
        "input_rows": len(df),
        "output_rows": len(result),
        "scenarios": scenarios,
    })
    return result
