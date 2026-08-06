# Corruption and Repair Comparison Report

## Evaluation metrics

| Metric | Baseline | Corrupted | Repaired | Corruption Δ | Repair Δ |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 0.7500 | 1.0000 | -0.2500 | +0.2500 |
| `mean_token_f1` | 1.0000 | 0.6667 | 1.0000 | -0.3333 | +0.3333 |
| `judge_accuracy` | 1.0000 | 0.6667 | 1.0000 | -0.3333 | +0.3333 |
| `mean_judge_score` | 5.0000 | 3.6667 | 5.0000 | -1.3333 | +1.3333 |

## Data observability

| Dataset | Quality | Passed / Failed | Freshness | Stale rows |
| --- | --- | ---: | --- | ---: |
| Corrupted | FAIL | 6 / 4 | stale_or_invalid | 1 |
| Repaired | PASS | 10 / 0 | fresh | 0 |

## Interpretation

The corrupted run has lower retrieval hit rate than baseline; inspect the answer and corruption-log artifacts for affected cases.

Repair is evaluated from a freshly rebuilt index and the same fixed test set. The report should be read together with `corruption_log.json`, answer artifacts, and the three metrics JSON files.
