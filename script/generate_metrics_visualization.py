from __future__ import annotations

from core.config import load_settings
from core.utils import read_json
from observability.visualization import generate_metrics_svg


if __name__ == "__main__":
    settings = load_settings()
    output = settings.paths.comparison_report.parent / "metrics_comparison.svg"
    generate_metrics_svg(output, read_json(settings.paths.baseline_metrics), read_json(settings.paths.corrupted_metrics), read_json(settings.paths.repaired_metrics))
    print(f"Wrote {output}")
