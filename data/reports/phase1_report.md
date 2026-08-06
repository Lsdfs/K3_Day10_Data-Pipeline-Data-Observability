# Baseline Pipeline Report

## Source lineage

| Field | Value |
| --- | --- |
| API | Crossref REST API |
| Query | agentic retrieval augmented generation large language model |
| Raw records | 24 |
| Clean records | 24 |

## Evaluation metrics

| Metric | Value |
| --- | ---: |
| `samples` | 24 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5 |

## Data quality

Overall: **PASS** — 10 passed, 0 failed.

| Check | Dimension | Status | Observed |
| --- | --- | --- | ---: |
| minimum_row_count | completeness | PASS | 24 |
| paper_id_not_null | completeness | PASS | 0 |
| paper_id_unique | uniqueness | PASS | 0 |
| title_not_null | completeness | PASS | 0 |
| summary_not_null | completeness | PASS | 0 |
| summary_length | completeness | PASS | 1.0000 |
| embedding_text_not_null | validity | PASS | 0 |
| published_date_valid | validity | PASS | 0 |
| age_days_valid | validity | PASS | 0 |
| freshness_age_days | timeliness | PASS | 0 |

## Freshness

| Field | Value |
| --- | --- |
| Latest published | 2026-08-01 |
| Oldest published | 2026-02-12 |
| Latest source update | N/A |
| Stale rows | 0 / 24 |
| Threshold | 180 days |
| Status | **fresh** |

## Evidence

The metrics above are calculated from the persisted test set, answer artifact, and baseline index. Quality and freshness values are calculated from the clean-data artifact of the same run.
