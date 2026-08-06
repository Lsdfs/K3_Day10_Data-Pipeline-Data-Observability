from __future__ import annotations

from evaluation.metrics import _token_f1, evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.corruption import corrupt_clean_dataframe
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.index import SearchResult


def test_quality_and_freshness_detect_corruption(clean_df, settings, tmp_path):
    baseline = run_data_quality_checks(clean_df, settings, "baseline")
    fresh = build_freshness_report(clean_df, settings, tmp_path / "fresh.json")
    corrupted = corrupt_clean_dataframe(clean_df, tmp_path / "log.json", seed=9)
    bad = run_data_quality_checks(corrupted, settings, "corrupted")
    stale = build_freshness_report(corrupted, settings, tmp_path / "stale.json")
    assert baseline["status"] == "PASS" and fresh["is_fresh"]
    assert bad["status"] == "FAIL" and not stale["is_fresh"]
    assert {"failed_count", "failed_rate", "threshold", "message"} <= set(bad["checks"][0])
    assert {"stale_rate", "median_age_days", "max_age_days", "generated_at"} <= set(stale)


def test_testset_and_metrics_are_deterministic(clean_df, settings, tmp_path):
    path = tmp_path / "test_set.json"
    first = build_test_set(clean_df, path)
    second = build_test_set(clean_df, path)
    assert first == second and len({item["id"] for item in first}) == len(first)

    class FakeIndex:
        def lookup(self, value):
            rows = clean_df.loc[clean_df["title"] == value]
            if rows.empty:
                return None
            row = rows.iloc[0]
            return {"paper_id": row.paper_id, "title": row.title, "content": row.text_for_embedding, "metadata": row.to_dict()}
        def search(self, query, top_k=None):
            row = next((row for _, row in clean_df.iterrows() if row.title in query), clean_df.iloc[0])
            return [SearchResult(row.paper_id, row.title, 1.0, row.text_for_embedding, row.to_dict())]
    bundle = evaluate_pipeline(settings, FakeIndex(), path, tmp_path / "metrics.json", tmp_path / "answers.json")
    assert _token_f1("alpha alpha beta", "alpha beta") == 0.8
    assert bundle.summary["samples"] == len(first)
    assert bundle.summary["retrieval_hit_rate"] == 1.0
    assert bundle.summary["judge_mode"] == ["heuristic"]
