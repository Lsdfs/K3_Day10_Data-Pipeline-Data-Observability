from __future__ import annotations

from evaluation.metrics import _token_f1, evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.corruption import corrupt_clean_dataframe
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.index import SearchResult


def test_testset_is_deterministic_and_complete(clean_df, tmp_path):
    path = tmp_path / "eval.json"
    first = build_test_set(clean_df, path)
    second = build_test_set(clean_df, path)
    assert first == second
    assert len(first) == 6
    assert {"id", "question_type", "question", "ground_truth", "ground_truth_doc_ids"} <= set(first[0])
    assert {item["question_type"] for item in first} == {"summary", "authors", "date", "categories"}


def test_quality_detects_corruption_and_repair(clean_df, settings, tmp_path):
    baseline = run_data_quality_checks(clean_df, settings, "baseline")
    baseline_freshness = build_freshness_report(clean_df, settings, tmp_path / "fresh.json")
    corrupted = corrupt_clean_dataframe(clean_df, tmp_path / "log.json")
    bad = run_data_quality_checks(corrupted, settings, "bad")
    bad_freshness = build_freshness_report(corrupted, settings, tmp_path / "bad-fresh.json")
    assert baseline["passed"]
    assert baseline_freshness["is_fresh"]
    assert not bad["passed"]
    assert not bad_freshness["is_fresh"]


def test_token_f1_and_evaluation_artifacts(clean_df, settings, tmp_path):
    test_path = tmp_path / "eval.json"
    test_set = build_test_set(clean_df, test_path)
    target = clean_df.iloc[0]

    class FakeIndex:
        def lookup(self, value):
            row = clean_df.loc[clean_df["title"] == value]
            if row.empty:
                return None
            item = row.iloc[0]
            return {
                "paper_id": item["paper_id"], "title": item["title"],
                "content": item["text_for_embedding"], "metadata": item.to_dict(),
            }

        def search(self, query, top_k=None):
            title = next((row["title"] for _, row in clean_df.iterrows() if row["title"] in query), target["title"])
            item = clean_df.loc[clean_df["title"] == title].iloc[0]
            return [SearchResult(item["paper_id"], item["title"], 1.0, item["text_for_embedding"], item.to_dict())]

    metrics = tmp_path / "metrics.json"
    answers = tmp_path / "answers.json"
    bundle = evaluate_pipeline(settings, FakeIndex(), test_path, metrics, answers)
    assert _token_f1("alpha beta", "alpha beta") == 1.0
    assert bundle.summary["samples"] == len(test_set)
    assert bundle.summary["retrieval_hit_rate"] == 1.0
    assert metrics.exists() and answers.exists()
