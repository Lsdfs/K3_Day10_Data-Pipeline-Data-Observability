from __future__ import annotations

from observability.visualization import generate_metrics_svg


def test_metrics_visualization_is_valid_svg(tmp_path):
    path = tmp_path / "chart.svg"
    baseline = {"retrieval_hit_rate": 1, "mean_token_f1": 1, "judge_accuracy": 1, "mean_judge_score": 5}
    corrupted = {"retrieval_hit_rate": 0.3, "mean_token_f1": 0.4, "judge_accuracy": 0.3, "mean_judge_score": 2}
    generate_metrics_svg(path, baseline, corrupted, baseline)
    content = path.read_text(encoding="utf-8")
    assert content.startswith("<svg")
    assert "Corrupted" in content
