from __future__ import annotations

import csv
from html import escape
from pathlib import Path
from typing import Any

from core.utils import ensure_parent, write_text


def generate_metrics_visualization(
    csv_path: Path,
    svg_path: Path,
    baseline: dict[str, Any],
    corrupted: dict[str, Any],
    repaired: dict[str, Any],
) -> None:
    states = [("Baseline", baseline, "#2563eb"), ("Corrupted", corrupted, "#dc2626"), ("Repaired", repaired, "#16a34a")]
    metrics = [
        ("retrieval_hit_rate", 1.0), ("mean_token_f1", 1.0),
        ("judge_accuracy", 1.0), ("mean_judge_score", 5.0),
    ]
    ensure_parent(csv_path)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["state", *[name for name, _ in metrics]])
        for state, payload, _ in states:
            writer.writerow([state.lower(), *[payload[name] for name, _ in metrics]])

    width, height = 980, 520
    left, top, chart_width, chart_height = 190, 70, 740, 360
    group_height = chart_height / len(metrics)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<text x="40" y="36" font-family="Arial" font-size="24" font-weight="700">Baseline → Corrupted → Repaired</text>',
    ]
    for tick in range(6):
        x = left + chart_width * tick / 5
        parts.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top + chart_height}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{x}" y="{top + chart_height + 24}" text-anchor="middle" font-family="Arial" font-size="12">{tick / 5:.1f}</text>')
    for metric_index, (name, scale) in enumerate(metrics):
        base_y = top + metric_index * group_height
        parts.append(f'<text x="20" y="{base_y + 38}" font-family="Arial" font-size="13">{escape(name)}</text>')
        for state_index, (_, payload, color) in enumerate(states):
            value = float(payload[name])
            normalized = max(0.0, min(1.0, value / scale))
            y = base_y + 8 + state_index * 23
            bar_width = normalized * chart_width
            parts.append(f'<rect x="{left}" y="{y}" width="{bar_width}" height="18" rx="3" fill="{color}"/>')
            parts.append(f'<text x="{left + bar_width + 6}" y="{y + 14}" font-family="Arial" font-size="12">{value:.3f}</text>')
    for index, (state, _, color) in enumerate(states):
        x = 300 + index * 180
        parts.append(f'<rect x="{x}" y="{height - 42}" width="14" height="14" fill="{color}"/>')
        parts.append(f'<text x="{x + 22}" y="{height - 30}" font-family="Arial" font-size="13">{state}</text>')
    parts.append("</svg>")
    write_text(svg_path, "\n".join(parts) + "\n")
