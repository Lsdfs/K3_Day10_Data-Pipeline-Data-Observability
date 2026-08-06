# Báo cáo baseline pipeline

## Nguồn và cấu hình

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API |
| Endpoint | https://api.crossref.org/works |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2026-02-07,until-pub-date:2026-08-06,has-abstract:true |
| Raw/Clean rows | 24 / 24 |
| Source mode | cached raw snapshot |
| Embedding backend | local_hashing_fallback |
| Collection | papers-baseline |

## Evaluation

| Metric | Giá trị |
| --- | ---: |
| `samples` | 8 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5 |
| `judge_mode` | ['heuristic'] |

Ragas: `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}`.

## Data quality

Overall: **PASS** — 15 pass, 0 fail.

| Check | Dimension | Status | Observed | Threshold |
| --- | --- | --- | --- | --- |
| dataset_not_empty | completeness | PASS | 24 | > 0 rows |
| required_columns | validity | PASS | [] | no missing required columns |
| paper_id_completeness | completeness | PASS | 0 | 0 empty |
| paper_id_uniqueness | uniqueness | PASS | 0 | 0 duplicate rows |
| duplicate_rate | uniqueness | PASS | 0.0000 | 0.0 |
| title_completeness | completeness | PASS | 0 | 0 empty |
| summary_completeness | completeness | PASS | 0 | 0 empty |
| summary_length | completeness | PASS | 1.0000 | 100% >= 40 chars |
| embedding_text_completeness | validity | PASS | 0 | 0 empty |
| published_parseability | validity | PASS | 0 | 0 invalid |
| age_days_validity | validity | PASS | 0 | 0 null/negative |
| stale_rate | timeliness | PASS | 0.0000 | 0 rows > 180 days |
| authors_completeness | completeness | PASS | 0 | 0 unknown/empty |
| categories_completeness | completeness | PASS | 0 | 0 empty |
| abstract_url_validity | validity | PASS | 0 | 0 invalid URL |

## Freshness

| Signal | Giá trị |
| --- | --- |
| Latest / oldest | 2026-08-01 / 2026-02-12 |
| Stale rows/rate | 0 / 0.0 |
| Median / max age | 66.0 / 175 ngày |
| Threshold | 180 ngày |
| Status | **fresh** |

Các số liệu được đọc trực tiếp từ output của lần chạy, không hard-code trong pipeline.
