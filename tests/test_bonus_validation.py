from pathlib import Path

import pandas as pd

from evaluation.testset import build_test_set
from core.config import load_settings
from observability.quality import run_data_quality_checks
from observability.visualization import generate_metrics_svg


def test_test_set_quality_and_svg(tmp_path):
    settings = load_settings()
    df = pd.read_csv(settings.paths.clean_csv, keep_default_na=False)
    test_set = build_test_set(df, tmp_path / "test_set.json")
    assert test_set and all(item["ground_truth_doc_ids"][0] in set(df.paper_id) for item in test_set)
    assert run_data_quality_checks(df, settings, "bonus_test")["passed"]
    output = tmp_path / "comparison.svg"
    generate_metrics_svg(output, {"retrieval_hit_rate": 1, "mean_token_f1": 1, "judge_accuracy": 1, "mean_judge_score": 5}, {"retrieval_hit_rate": .5, "mean_token_f1": .5, "judge_accuracy": .5, "mean_judge_score": 2.5}, {"retrieval_hit_rate": 1, "mean_token_f1": 1, "judge_accuracy": 1, "mean_judge_score": 5})
    assert output.exists() and "RAG quality recovery" in output.read_text(encoding="utf-8")
