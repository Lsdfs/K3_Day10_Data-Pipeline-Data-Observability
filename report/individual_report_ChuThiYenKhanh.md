# Individual Report — Evaluation & Observability

## 1. Information

| Field | Value |
| --- | --- |
| Name | Yen Khanh |
| MSSV | 2A202601739 |
| Class | K3 |
| Group | ViatminB4 |
| Role | Evaluation & Observability |

## 2. Owned work

| Module | Input | Output |
| --- | --- | --- |
| `src/evaluation/testset.py` | Clean dataframe | Fixed questions with clean `paper_id` ground truth IDs |
| `src/evaluation/metrics.py` | Index and test set | Metrics and per-question answers |
| `src/observability/quality.py` | Clean/corrupted/repaired dataframes | Quality and freshness JSON evidence |
| `src/observability/reporting.py` | Metrics and quality artifacts | Baseline and comparison reports |

## 3. Technical implementation

The test set is generated deterministically from the cleaned corpus. Every `ground_truth_doc_ids` value comes directly from the clean DOI-based `paper_id`, never an invented ID. Questions cover summary, authors, date, and categories when source metadata is present. The same persisted test set is used for baseline, corrupted, and repaired evaluations, making the comparison fair.

Quality checks measure row count, null IDs/titles/summaries, duplicate IDs, summary length, embedding text, publication-date validity, `age_days`, and stale rows. Freshness summarizes newest/oldest publication dates and uses a 180-day threshold. The report reads generated JSON artifacts and compares the three states without claiming degradation unless metrics support it.

## 4. Evidence and results

| Signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 1.000 | 0.750 | 1.000 |
| Mean token F1 | 1.000 | 0.667 | 1.000 |
| Judge accuracy | 1.000 | 0.667 | 1.000 |
| Mean judge score | 5.000 | 3.667 | 5.000 |
| Quality status | PASS | FAIL | PASS |
| Freshness status | fresh | stale_or_invalid | fresh |

Commands used:

```powershell
$env:USE_LLM_JUDGE='false'
python script/run_phase1.py
python script/run_corruption_flow.py
```

Artifacts: `data/eval/test_set.json`, `data/results/*metrics.json`, `data/results/*answers.json`, `data/quality/`, `data/reports/`.

## 5. Key decision and blocker

I kept the test set fixed across all states so a lower score can be attributed to data corruption instead of changing questions. The initial flow used one Gemini judge request per sample and became slow during the two evaluation passes. I added `USE_LLM_JUDGE=false`, which uses deterministic token-F1 judging for fast reproducible full runs; Gemini live-agent smoke testing remains available separately.

## 6. End-to-end understanding

Crossref records are saved raw, cleaned into a DOI-keyed dataframe, embedded with MiniLM, and stored in Chroma. Retrieval hit rate checks whether the ground-truth DOI appears among retrieved documents; token F1 and judge metrics compare the answer with ground truth. Quality checks test data contract violations, while freshness focuses on time validity. Repair succeeds only when it rebuilds from raw data and restores both data signals and the fixed-test-set metrics.

## 7. Confirmation

- [x] Claims in this report are supported by artifacts.
- [x] No secret is included.
