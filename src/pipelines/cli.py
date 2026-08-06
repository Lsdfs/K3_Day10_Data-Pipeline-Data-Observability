from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import pandas as pd

from core.config import load_settings
from core.utils import write_json


def _strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Invalid JSON constant {value}")),
    )


def audit_artifacts(project_dir: Path | None = None) -> dict[str, Any]:
    """Validate submission artifacts, source completeness, docs and tracked-file hygiene."""
    settings = load_settings(project_dir)
    paths = settings.paths
    required = [
        paths.raw_api_response, paths.raw_records_json, paths.ingestion_summary,
        paths.clean_csv, paths.clean_json, paths.corrupted_clean_csv, paths.corrupted_clean_json,
        paths.repaired_clean_csv, paths.repaired_clean_json,
        paths.embeddings_json, paths.corrupted_embeddings_json, paths.repaired_embeddings_json,
        paths.eval_testset,
        paths.baseline_metrics, paths.baseline_answers, paths.corrupted_metrics,
        paths.corrupted_answers, paths.repaired_metrics, paths.repaired_answers,
        paths.corruption_log, paths.comparison_metrics,
        paths.quality_dir / "baseline_quality.json",
        paths.quality_dir / "corrupted_quality.json",
        paths.quality_dir / "repaired_quality.json",
        paths.freshness_report, paths.corrupted_freshness_report, paths.repaired_freshness_report,
        paths.baseline_report, paths.comparison_report, paths.comparison_csv, paths.comparison_chart,
        paths.project_dir / "README.md", paths.project_dir / "PHAN_CONG_CONG_VIEC.md",
        paths.project_dir / "RUBRIC_AUDIT.md", paths.project_dir / "SUBMISSION_CHECKLIST.md",
        paths.project_dir / "report" / "group_report.md",
        paths.project_dir / "report" / "individual_nguyen_quang_huy.md",
    ]
    artifact_status = {
        str(path.relative_to(paths.project_dir)): path.is_file() and path.stat().st_size > 0
        for path in required
    }
    errors: list[str] = [f"missing_or_empty:{name}" for name, ok in artifact_status.items() if not ok]

    json_files = [path for path in required if path.suffix == ".json" and path.is_file()]
    for path in json_files:
        try:
            _strict_json(path)
        except Exception as exc:
            errors.append(f"invalid_json:{path.relative_to(paths.project_dir)}:{type(exc).__name__}")
    csv_files = [path for path in required if path.suffix == ".csv" and path.is_file()]
    for path in csv_files:
        try:
            frame = pd.read_csv(path)
            if frame.empty:
                errors.append(f"empty_csv:{path.relative_to(paths.project_dir)}")
        except Exception as exc:
            errors.append(f"invalid_csv:{path.relative_to(paths.project_dir)}:{type(exc).__name__}")

    metrics_payloads = {}
    for state, path in {
        "baseline": paths.baseline_metrics,
        "corrupted": paths.corrupted_metrics,
        "repaired": paths.repaired_metrics,
    }.items():
        if not path.is_file():
            continue
        payload = _strict_json(path)
        metrics_payloads[state] = payload
        for name in ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy"]:
            value = payload.get(name)
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                errors.append(f"metric_out_of_range:{state}:{name}")
        score = payload.get("mean_judge_score")
        if not isinstance(score, (int, float)) or not 1 <= score <= 5:
            errors.append(f"metric_out_of_range:{state}:mean_judge_score")
        if not isinstance(payload.get("samples"), int) or payload["samples"] <= 0:
            errors.append(f"invalid_sample_count:{state}")
    if len(metrics_payloads) == 3:
        test_hashes = {payload.get("test_set_sha256") for payload in metrics_payloads.values()}
        if len(test_hashes) != 1 or None in test_hashes:
            errors.append("evaluation_test_set_hash_mismatch")
        baseline = metrics_payloads["baseline"]
        corrupted = metrics_payloads["corrupted"]
        repaired = metrics_payloads["repaired"]
        names = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
        if not any(corrupted[name] < baseline[name] for name in names):
            errors.append("corruption_did_not_degrade_any_metric")
        if not any(repaired[name] > corrupted[name] for name in names):
            errors.append("repair_did_not_recover_any_metric")

    marker = "TODO" + "(student)"
    unimplemented = "NotImplemented" + "Error"
    incomplete_source = []
    for path in paths.project_dir.joinpath("src").rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        if marker in content or unimplemented in content:
            incomplete_source.append(str(path.relative_to(paths.project_dir)))
    if incomplete_source:
        errors.append("incomplete_source")

    submission_docs = [
        paths.project_dir / "README.md", paths.project_dir / "PHAN_CONG_CONG_VIEC.md",
        paths.project_dir / "RUBRIC_AUDIT.md", paths.project_dir / "SUBMISSION_CHECKLIST.md",
        paths.project_dir / "report" / "group_report.md",
        paths.project_dir / "report" / "individual_nguyen_quang_huy.md",
    ]
    placeholder_pattern = re.compile(r"\[(?:Họ tên|MSSV|Giá trị|Mô tả|Điền|Viết|Tên nhóm)[^\]]*\]", re.IGNORECASE)
    old_urls = ["Bietdoibongdem888", "VinUni-AI20k/K3_Day10"]
    for path in submission_docs:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        if placeholder_pattern.search(content):
            errors.append(f"placeholder:{path.relative_to(paths.project_dir)}")
        if any(old in content for old in old_urls):
            errors.append(f"old_repository_url:{path.relative_to(paths.project_dir)}")

    text_artifacts = [path for path in required if path.is_file() and path.suffix in {".json", ".csv", ".md", ".svg"}]
    local_path_pattern = re.compile(r"[A-Za-z]:\\Users\\")
    for path in text_artifacts:
        if local_path_pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
            errors.append(f"machine_path:{path.relative_to(paths.project_dir)}")

    tracked = subprocess.run(
        ["git", "ls-files"], cwd=paths.project_dir, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    junk_patterns = [
        re.compile(r"(^|/)\.env$"), re.compile(r"(^|/)\.pytest_(?:tmp|cache|tmp_runtime)(/|$)"),
        re.compile(r"(^|/)\.venv(/|$)"), re.compile(r"(^|/)__pycache__(/|$)"),
        re.compile(r"\.pyc$"), re.compile(r"(^|/)\.vscode(/|$)"),
    ]
    tracked_junk = [name for name in tracked if any(pattern.search(name) for pattern in junk_patterns)]
    if tracked_junk:
        errors.append("tracked_local_files")
    secret_patterns = [
        re.compile("sk-" + r"[A-Za-z0-9_-]{20,}"),
        re.compile("AIza" + r"[A-Za-z0-9_-]{30,}"),
        re.compile("gh" + r"[pousr]_[A-Za-z0-9]{20,}"),
    ]
    secret_files = []
    for name in tracked:
        path = paths.project_dir / name
        if not path.is_file() or path.suffix in {".bin", ".sqlite3"}:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(content) for pattern in secret_patterns):
            secret_files.append(name)
    if secret_files:
        errors.append("potential_secret")

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "PASS" if not errors else "FAIL",
        "passed": not errors,
        "artifact_status": artifact_status,
        "incomplete_source_files": incomplete_source,
        "tracked_local_files": tracked_junk,
        "potential_secret_files": secret_files,
        "errors": errors,
    }
    write_json(paths.audit_report, payload)
    return payload


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Day 10 Data Pipeline & Data Observability CLI")
    parser.add_argument("command", choices=["baseline", "corruption", "all", "audit"])
    args = parser.parse_args(argv)
    try:
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
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
