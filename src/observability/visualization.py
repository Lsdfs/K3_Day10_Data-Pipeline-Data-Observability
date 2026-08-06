from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from core.utils import write_text


def generate_metrics_svg(
    output_path: Path,
    baseline: dict[str, Any],
    corrupted: dict[str, Any],
    repaired: dict[str, Any],
) -> None:
    """Create a dependency-free SVG comparison chart from evaluation artifacts."""
    states = [
        ("Baseline", baseline, "#2563eb"),
        ("Corrupted", corrupted, "#dc2626"),
        ("Repaired", repaired, "#16a34a"),
    ]
    metrics = [
        ("Retrieval hit rate", "retrieval_hit_rate", 1.0),
        ("Token F1", "mean_token_f1", 1.0),
        ("Judge accuracy", "judge_accuracy", 1.0),
        ("Judge score / 5", "mean_judge_score", 5.0),
    ]
    width, height = 980, 520
    chart_left, chart_top, chart_width, chart_height = 190, 70, 740, 360
    group_height = chart_height / len(metrics)
    bar_height = 18
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="40" y="36" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#111827">Baseline → Corrupted → Repaired</text>',
    ]
    for tick in range(6):
        x = chart_left + chart_width * tick / 5
        parts.append(f'<line x1="{x:.1f}" y1="{chart_top}" x2="{x:.1f}" y2="{chart_top + chart_height}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{x:.1f}" y="{chart_top + chart_height + 24}" text-anchor="middle" font-family="Arial" font-size="12" fill="#4b5563">{tick / 5:.1f}</text>')
    for metric_index, (label, key, scale) in enumerate(metrics):
        y_base = chart_top + metric_index * group_height
        parts.append(f'<text x="20" y="{y_base + 38:.1f}" font-family="Arial" font-size="14" fill="#111827">{escape(label)}</text>')
        for state_index, (state, payload, color) in enumerate(states):
            normalized = max(0.0, min(1.0, float(payload.get(key, 0.0)) / scale))
            y = y_base + 8 + state_index * (bar_height + 5)
            bar_width = normalized * chart_width
            parts.append(f'<rect x="{chart_left}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height}" rx="3" fill="{color}"/>')
            parts.append(f'<text x="{chart_left + bar_width + 6:.1f}" y="{y + 14:.1f}" font-family="Arial" font-size="12" fill="#374151">{float(payload.get(key, 0.0)):.3f}</text>')
    for index, (state, _, color) in enumerate(states):
        x = 300 + index * 180
        parts.append(f'<rect x="{x}" y="{height - 42}" width="14" height="14" rx="2" fill="{color}"/>')
        parts.append(f'<text x="{x + 22}" y="{height - 30}" font-family="Arial" font-size="13" fill="#111827">{escape(state)}</text>')
    parts.append('</svg>')
    write_text(output_path, "\n".join(parts) + "\n")
