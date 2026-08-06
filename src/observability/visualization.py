"""Small dependency-free visualizations for reproducible pipeline reports."""
from __future__ import annotations

from html import escape
from pathlib import Path

from core.utils import ensure_parent, write_text


def generate_metrics_svg(path: Path, baseline: dict, corrupted: dict, repaired: dict) -> None:
    """Write a compact SVG comparing the three pipeline states."""
    metrics = [
        ("Retrieval hit", "retrieval_hit_rate", 1.0),
        ("Token F1", "mean_token_f1", 1.0),
        ("Judge accuracy", "judge_accuracy", 1.0),
        ("Judge score", "mean_judge_score", 5.0),
    ]
    states = [("Baseline", baseline, "#2563eb"), ("Corrupted", corrupted, "#dc2626"), ("Repaired", repaired, "#16a34a")]
    rows = []
    for row, (label, key, maximum) in enumerate(metrics):
        y = 72 + row * 95
        rows.append(f'<text x="22" y="{y}" font-size="15" fill="#0f172a">{escape(label)}</text>')
        for col, (state, payload, color) in enumerate(states):
            value = float(payload.get(key, 0.0)) / maximum
            x = 180 + col * 150
            height = round(55 * value, 1)
            rows.append(f'<rect x="{x}" y="{y + 62 - height}" width="78" height="{height}" rx="5" fill="{color}"/>')
            rows.append(f'<text x="{x + 39}" y="{y + 82}" text-anchor="middle" font-size="12" fill="#334155">{float(payload.get(key, 0.0)):.3f}</text>')
    legend = "".join(f'<text x="{180 + i * 150}" y="30" font-size="14" fill="{color}">{state}</text>' for i, (state, _, color) in enumerate(states))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="660" height="470" viewBox="0 0 660 470">
<rect width="660" height="470" fill="#f8fafc"/><text x="22" y="30" font-size="20" font-weight="700" fill="#0f172a">RAG quality recovery</text>{legend}{''.join(rows)}</svg>'''
    ensure_parent(path)
    write_text(path, svg)
