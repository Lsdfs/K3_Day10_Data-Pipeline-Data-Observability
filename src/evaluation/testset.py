from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create a deterministic, auditable evaluation set from cleaned papers.

    The questions deliberately quote the title because ``answer_question`` can
    perform an exact lookup before semantic retrieval.  Each ground-truth
    document ID is taken directly from the clean-data ``paper_id`` contract.
    """
    required_columns = {
        "paper_id",
        "title",
        "summary",
        "authors_joined",
        "categories_joined",
        "published",
    }
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Clean dataframe misses test-set columns: {missing_columns}")
    if len(df) < 4:
        raise ValueError(f"Need at least 4 clean documents, got {len(df)}")
    if df["paper_id"].isna().any() or df["paper_id"].astype(str).str.strip().eq("").any():
        raise ValueError("Cannot build a test set with empty paper_id values.")
    if df["paper_id"].astype(str).duplicated().any():
        raise ValueError("Cannot build a test set from duplicate paper_id values.")

    sample = df.sort_values(["published", "paper_id"], ascending=[False, True]).head(min(8, len(df)))
    test_set: list[dict[str, Any]] = []

    for idx, (_, row) in enumerate(sample.iterrows()):
        pid = row["paper_id"]
        title = row["title"]
        def text(column: str) -> str:
            value = row[column]
            return "" if pd.isna(value) else normalize_whitespace(str(value))

        summary = text("summary")
        authors = text("authors_joined")
        categories = text("categories_joined")
        published = text("published")

        questions = []

        if summary:
            questions.append({
                "question_type": "summary",
                "question": f"What is the paper '{title}' about?",
                "ground_truth": first_sentence(summary),
            })

        if authors:
            questions.append({
                "question_type": "authors",
                "question": f"Who authored '{title}'?",
                "ground_truth": authors,
            })

        if published:
            questions.append({
                "question_type": "date",
                "question": f"When was '{title}' published?",
                "ground_truth": published,
            })

        if categories:
            questions.append({
                "question_type": "categories",
                "question": f"What categories does '{title}' belong to?",
                "ground_truth": categories,
            })

        for i, q in enumerate(questions):
            test_set.append({
                "id": f"{pid}__{q['question_type']}__{i}",
                "question_type": q["question_type"],
                "question": q["question"],
                "ground_truth": q["ground_truth"],
                "ground_truth_doc_ids": [pid],
            })

    # Crossref subject metadata is optional.  The other three types are
    # required; category questions appear whenever the source provides them.
    required_question_types = {"summary", "authors", "date"}
    present_question_types = {item["question_type"] for item in test_set}
    missing_question_types = sorted(required_question_types - present_question_types)
    if missing_question_types:
        raise ValueError(
            "Clean data cannot support all required question types: " + ", ".join(missing_question_types)
        )
    write_json(output_path, test_set)
    return test_set
