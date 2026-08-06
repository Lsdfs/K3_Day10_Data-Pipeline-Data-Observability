from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic, verifiable multi-type evaluation set from clean data."""
    required = {
        "paper_id", "title", "summary", "authors_joined", "categories_joined", "published"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe misses evaluation columns: {sorted(missing)}")
    if len(df) < 8:
        raise ValueError("At least 8 clean documents are required for the evaluation set.")
    selected = df.sort_values(
        ["published", "paper_id"], ascending=[False, True], kind="stable"
    ).head(min(8, len(df)))
    templates = [
        ("summary", "What is the main point of the paper '{title}'?", lambda row: first_sentence(str(row["summary"]))),
        ("authors", "Who authored the paper '{title}'?", lambda row: str(row["authors_joined"])),
        ("date", "When was the paper '{title}' published?", lambda row: str(row["published"])),
        ("categories", "What categories are listed for the paper '{title}'?", lambda row: str(row["categories_joined"])),
    ]
    test_set = []
    for position, (_, row) in enumerate(selected.iterrows()):
        question_type, template, answer = templates[position % len(templates)]
        test_set.append({
            "id": f"eval-{position + 1:02d}",
            "question_type": question_type,
            "question": template.format(title=row["title"]),
            "ground_truth": answer(row),
            "ground_truth_doc_ids": [str(row["paper_id"])],
        })
    if len({item["id"] for item in test_set}) != len(test_set):
        raise RuntimeError("Evaluation IDs are not unique.")
    write_json(output_path, test_set)
    return test_set
