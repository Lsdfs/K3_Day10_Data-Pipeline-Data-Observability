from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.config import load_settings


def audit_artifacts(project_dir: Path | None = None) -> dict:
    settings = load_settings(project_dir)
    required = [
        settings.paths.raw_api_response,
        settings.paths.raw_records_json,
        settings.paths.clean_csv,
        settings.paths.clean_json,
        settings.paths.embeddings_json,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
        settings.paths.freshness_report,
        settings.paths.baseline_report,
        settings.paths.corruption_log,
        settings.paths.corrupted_metrics,
        settings.paths.repaired_metrics,
        settings.paths.comparison_report,
        settings.paths.comparison_report.parent / "metrics_comparison.svg",
    ]
    artifact_status = {
        str(path.relative_to(settings.paths.project_dir)): path.is_file() and path.stat().st_size > 0
        for path in required
    }
    markers = []
    for path in settings.paths.project_dir.joinpath("src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "TODO" + "(student)" in text or "NotImplemented" + "Error" in text:
            markers.append(str(path.relative_to(settings.paths.project_dir)))
    return {
        "passed": all(artifact_status.values()) and not markers,
        "artifacts": artifact_status,
        "incomplete_source_files": markers,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Day 10 data observability pipeline")
    parser.add_argument("command", choices=["baseline", "corruption", "all", "audit"])
    args = parser.parse_args(argv)
    if args.command in {"baseline", "all"}:
        from pipelines.phase1 import main as run_baseline

        run_baseline()
    if args.command in {"corruption", "all"}:
        from pipelines.corruption_flow import main as run_corruption

        run_corruption()
    if args.command == "audit":
        payload = audit_artifacts()
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        if not payload["passed"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
