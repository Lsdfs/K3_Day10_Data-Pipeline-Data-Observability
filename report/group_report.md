# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Submission information

| Field | Value |
| --- | --- |
| Class | K3 |
| Group | ViatminB4 |
| Repository | `K3_Day10_Data-Pipeline-Data-Observability` |
| Completion date | 2026-08-06 |

| Role | Ownership | Main deliverables |
| --- | --- | --- |
| 1 | Configuration and orchestration | `src/core/`, `src/pipelines/` |
| 2 | Data platform and recovery | `src/ingestion/`, raw/clean artifacts |
| 3 | RAG and agent | `src/retrieval/`, Chroma collections |
| 4 | Evaluation and observability | `src/evaluation/`, `src/observability/` |

## 2. Summary

The team implemented an end-to-end RAG data pipeline using Crossref metadata. The baseline run persisted the original API response, 24 parsed and cleaned papers, a MiniLM/Chroma index, a fixed 24-question evaluation set, answers, quality/freshness evidence, and a Markdown report. The corruption run deliberately removed two latest papers, blanked summaries, injected noise, truncated a title, made a publication stale, and inserted a duplicate. These changes reduced retrieval hit rate from 1.000 to 0.750 and mean token F1 from 1.000 to 0.667. Repair reloads the immutable raw snapshot and rebuilds the clean data and separate Chroma collection; all four measured metrics recovered to baseline. Quality checks also changed from baseline PASS to corrupted FAIL and repaired PASS; freshness recovered from `stale_or_invalid` to `fresh`.

## 3. Architecture and reproducibility

```text
Crossref API -> data/raw -> clean dataframe -> MiniLM + Chroma
             -> fixed test set -> evaluation/quality/freshness reports
             -> corruption -> re-index/evaluate -> repair from raw -> comparison
```

Configuration is loaded from `.env` and `src/core/config.py`. The embedding model is `sentence-transformers/all-MiniLM-L6-v2`; collections are `papers-baseline`, `papers-corrupted`, and `papers-repaired`. Run:

```powershell
python -m pip install -e .
python script/run_phase1.py
python script/run_corruption_flow.py
```

For a fast reproducible full evaluation without 72 remote LLM judge requests, use `USE_LLM_JUDGE=false`; the live Gemini agent was verified separately with `script/smoke_retrieval_agent.py --agent`.

## 4. Data contract

Crossref is queried for agentic retrieval/RAG/LLM papers. A DOI normalized to lowercase is the stable `paper_id`. Raw response and parsed `PaperRecord` objects are persisted before cleaning. The fetcher retries retryable HTTP statuses with exponential backoff.

The clean schema includes `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `updated`, URLs, `summary_chars`, `age_days`, and `text_for_embedding`. Cleaning removes records without titles, deduplicates by DOI, normalizes whitespace, and constructs embedding text from title, authors, and summary.

## 5. Baseline evidence

| Artifact | Path |
| --- | --- |
| Raw response and records | `data/raw/` |
| Clean data | `data/clean/papers_clean.csv` and `.json` |
| Index manifest | `data/embeddings/papers_embeddings.json` |
| Evaluation set | `data/eval/test_set.json` |
| Metrics and answers | `data/results/baseline_metrics.json`, `baseline_answers.json` |
| Quality and freshness | `data/quality/baseline_quality.json`, `freshness_report.json` |
| Report | `data/reports/phase1_report.md` |

| Metric | Baseline |
| --- | ---: |
| Samples | 24 |
| Retrieval hit rate | 1.000 |
| Mean token F1 | 1.000 |
| Judge accuracy | 1.000 |
| Mean judge score | 5.000 |

Baseline quality passed all 10 checks. It contained 24 unique IDs, no empty title/summary/embedding text, and no stale rows. Freshness was `fresh`; published dates range from 2026-02-12 to 2026-08-01 with a 180-day threshold.

## 6. Corruption, repair, and comparison

| Scenario | Evidence | Expected signal |
| --- | --- | --- |
| Drop latest | 2 DOI records in `corruption_log.json` | lower retrieval coverage |
| Blank summary | 2 records | missing/short summaries |
| Noise injection | 1 record | degraded embedding content |
| Title truncation | 1 record | weaker title matching |
| Stale date | 1 record | stale freshness row |
| Duplicate | 1 row | duplicate DOI check fails |

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 1.000 | 0.750 | 1.000 |
| Mean token F1 | 1.000 | 0.667 | 1.000 |
| Judge accuracy | 1.000 | 0.667 | 1.000 |
| Mean judge score | 5.000 | 3.667 | 5.000 |
| Quality | PASS | FAIL (5/10 checks) | PASS (10/10 checks) |
| Freshness | fresh | stale_or_invalid | fresh |

The causal evidence is direct: dropped/blank/noisy/duplicate/stale data produced quality failures and a 0.25 retrieval-hit reduction; rebuilding from the original raw snapshot restored both quality/freshness and all evaluation metrics. The complete comparison is in `data/reports/corruption_report.md`.

## 7. Integration issue and limitation

The initial full flow called Gemini once per evaluation sample, causing 48 sequential judge calls in corruption/recovery and exceeding the execution limit. The evaluator now supports `USE_LLM_JUDGE=false`, which uses the existing deterministic token-F1 fallback for a fast full reproducible run; the live Gemini agent remains separately smoke-tested. Ragas is intentionally disabled unless `RUN_RAGAS=1` because it is slower and optional.

## 8. Submission checklist

- [x] Raw, clean, embedding, evaluation, metrics, quality, freshness, and report artifacts exist.
- [x] Baseline/corrupted/repaired use the same fixed test set.
- [x] Corruption log records affected DOI IDs and counts.
- [x] Repair rebuilds from raw snapshot rather than modifying corrupted data.
- [ ] Fill remaining member names and MSSV before submission, if applicable.
- [ ] Commit the final code and regenerated artifacts before submission.
