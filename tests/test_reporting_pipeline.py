from __future__ import annotations

from dataclasses import asdict

from core.utils import write_json
from observability.reporting import generate_corruption_report


def test_reporting_uses_input_metrics(tmp_path):
    output = tmp_path / "report.md"
    metrics = {"retrieval_hit_rate": 0.8123, "mean_token_f1": 0.7123, "judge_accuracy": 0.6123, "mean_judge_score": 3.5123}
    corrupted = {key: value / 2 for key, value in metrics.items()}
    quality = {"status": "FAIL", "passed_checks": 3, "failed_checks": 2}
    freshness = {"status": "stale_or_invalid", "stale_rows": 1, "stale_rate": 0.1}
    generate_corruption_report(output, metrics, corrupted, metrics, quality, quality, freshness, freshness)
    content = output.read_text(encoding="utf-8")
    assert "0.8123" in content and "0.4062" in content


def test_offline_pipeline_smoke(monkeypatch, settings, paper_records):
    from pipelines import corruption_flow, phase1
    write_json(settings.paths.raw_records_json, [asdict(record) for record in paper_records])
    write_json(settings.paths.raw_api_response, {"message": {"items": []}})
    monkeypatch.setattr(phase1, "load_settings", lambda: settings)
    monkeypatch.setattr(corruption_flow, "load_settings", lambda: settings)
    phase1.main()
    corruption_flow.main()
    assert settings.paths.baseline_metrics.exists()
    assert settings.paths.corrupted_metrics.exists()
    assert settings.paths.repaired_metrics.exists()
    assert settings.paths.comparison_chart.exists()
