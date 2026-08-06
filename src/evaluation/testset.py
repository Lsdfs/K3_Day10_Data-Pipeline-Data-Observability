from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic multi-type evaluation set from cleaned papers."""
    required = {
        "paper_id", "title", "summary", "authors_joined", "categories_joined", "published"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe misses test-set columns: {sorted(missing)}")
    if len(df) < 8:
        raise ValueError("At least 8 cleaned documents are required to build a representative test set.")

    selected = df.sort_values(["published", "paper_id"], ascending=[False, True]).head(min(6, len(df)))
    question_templates = [
        ("summary", "What is the main point of the paper '{title}'?", lambda row: first_sentence(str(row["summary"]))),
        ("authors", "Who authored the paper '{title}'?", lambda row: str(row["authors_joined"])),
        ("date", "When was the paper '{title}' published?", lambda row: str(row["published"])),
        ("categories", "What categories are listed for the paper '{title}'?", lambda row: str(row["categories_joined"])),
    ]
    test_set: list[dict[str, Any]] = []
    for position, (_, row) in enumerate(selected.iterrows()):
        question_type, template, answer_builder = question_templates[position % len(question_templates)]
        test_set.append(
            {
                "id": f"eval-{position + 1:02d}",
                "question_type": question_type,
                "question": template.format(title=row["title"]),
                "ground_truth": answer_builder(row),
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )
    write_json(output_path, test_set)
    return test_set
