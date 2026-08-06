# Báo cáo baseline pipeline

## Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API |
| Endpoint | https://api.crossref.org/works |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2026-02-07,has-abstract:true |
| Raw records | 24 |
| Chế độ | cached raw snapshot |

## Evaluation metrics

| Metric | Giá trị |
| --- | ---: |
| `samples` | 6 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5 |

Ragas: `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}`.

## Data quality

Trạng thái tổng thể: **PASS** (7 pass, 0 fail).

| Check | Dimension | Trạng thái | Observed | Expectation |
| --- | --- | --- | ---: | --- |
| minimum_row_count | completeness | PASS | 24 | >= 8 rows |
| paper_id_not_null | completeness | PASS | 0 | 0 empty IDs |
| paper_id_unique | uniqueness | PASS | 0 | 0 rows with duplicate IDs |
| title_not_null | completeness | PASS | 0 | 0 empty titles |
| summary_length | completeness | PASS | 1.0000 | >= 90% summaries have at least 40 characters |
| embedding_text_not_null | validity | PASS | 0 | 0 empty embedding texts |
| freshness_age_days | timeliness | PASS | 0 | 0 rows older than 180 days |

## Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Latest published | 2026-08-01 |
| Oldest published | 2026-02-12 |
| Stale rows | 0 / 24 |
| Threshold | 180 ngày |
| Status | **fresh** |

## Kết luận

Baseline đã tạo đủ raw, clean, embedding/index, evaluation, quality, freshness và answer artifacts. Các số liệu trên được lấy trực tiếp từ artifact của lần chạy hiện tại.
