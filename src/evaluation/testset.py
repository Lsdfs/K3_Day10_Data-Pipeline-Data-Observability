from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    if len(df) < 4:
        raise ValueError(f"Need at least 4 documents, got {len(df)}")

    sample = df.head(min(8, len(df)))
    test_set: list[dict[str, Any]] = []

    for idx, (_, row) in enumerate(sample.iterrows()):
        pid = row["paper_id"]
        title = row["title"]
        summary = row.get("summary", "")
        authors = row.get("authors_joined", "")
        categories = row.get("categories_joined", "")
        published = row.get("published", "")

        questions = []

        if summary:
            questions.append({
                "question_type": "summary",
                "question": f"What is the paper '{title}' about?",
                "ground_truth": summary[:200],
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

    write_json(output_path, test_set)
    return test_set
