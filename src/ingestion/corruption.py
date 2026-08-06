from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

from core.utils import normalize_whitespace


def _rebuild_text(row: pd.Series) -> str:
    title = row["title"]
    authors = row["authors_joined"]
    summary = row["summary"]
    text = f"Title: {title}."
    if authors:
        text += f" Authors: {authors}."
    text += f" Summary: {summary}."
    return normalize_whitespace(text)


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    df = df.copy()
    log: list[dict] = []
    total = len(df)

    # 1. Drop the latest records.  Use the source publication timestamp rather
    # than age_days because Crossref may provide year/month precision, for
    # which cleaning deliberately uses age_days=-1.
    if "published" in df.columns and len(df) >= 3:
        published = pd.to_datetime(df["published"], errors="coerce", utc=True)
        latest_indices = published.sort_values(ascending=False, na_position="last").head(2).index.tolist()
        if not latest_indices and "age_days" in df.columns:
            latest_indices = df["age_days"].sort_values().head(2).index.tolist()
        dropped_ids = df.loc[latest_indices, "paper_id"].tolist()
        df = df.drop(index=latest_indices).reset_index(drop=True)
        log.append({
            "type": "drop_latest",
            "removed_count": len(dropped_ids),
            "removed_paper_ids": dropped_ids,
            "selection_field": "published",
        })

    # 2. Blank summary on a few rows
    available = df.index.tolist()
    if len(available) >= 2:
        idxs = available[:2]
        df.loc[idxs, "summary"] = ""
        df.loc[idxs, "summary_chars"] = 0
        log.append({
            "type": "blank_summary",
            "affected_count": len(idxs),
            "affected_paper_ids": df.loc[idxs, "paper_id"].tolist(),
        })

    # 3. Inject noise into summary
    noise = " SPAM_NOISE_12345 "
    if len(available) >= 1:
        idx = available[min(3, len(available) - 1)]
        original = df.at[idx, "summary"]
        df.at[idx, "summary"] = noise + (original or "") + noise
        df.at[idx, "summary_chars"] = len(df.at[idx, "summary"])
        log.append({
            "type": "inject_noise",
            "affected_paper_ids": [df.at[idx, "paper_id"]],
        })

    # 4. Truncate title
    if len(available) >= 1:
        idx = available[min(2, len(available) - 1)]
        original = df.at[idx, "title"]
        df.at[idx, "title"] = (original or "")[:15]
        log.append({
            "type": "truncate_title",
            "affected_paper_ids": [df.at[idx, "paper_id"]],
        })

    # 5. Make published date stale (subtract 500 days)
    if "published" in df.columns and len(available) >= 1:
        idx = available[min(1, len(available) - 1)]
        try:
            pub = pd.Timestamp(df.at[idx, "published"])
            stale = pub - pd.Timedelta(days=500)
            df.at[idx, "published"] = stale.strftime("%Y-%m-%d")
            if "age_days" in df.columns:
                df.at[idx, "age_days"] = max(0, df.at[idx, "age_days"] + 500)
            log.append({
                "type": "stale_date",
                "affected_paper_ids": [df.at[idx, "paper_id"]],
            })
        except (ValueError, TypeError):
            pass

    # 6. Add duplicate rows
    if len(df) >= 1:
        dup = df.iloc[[0]].copy()
        df = pd.concat([df, dup], ignore_index=True)
        log.append({
            "type": "add_duplicate",
            "duplicate_count": 1,
            "duplicate_paper_id": dup.iloc[0]["paper_id"],
        })

    # Rebuild text_for_embedding
    df["text_for_embedding"] = df.apply(_rebuild_text, axis=1)

    log.append({"total_before_corruption": total, "total_after_corruption": len(df)})

    if output_log_path:
        Path(output_log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_log_path, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return df
