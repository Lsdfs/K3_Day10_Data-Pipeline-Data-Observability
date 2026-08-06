# Individual Report — Data Platform & Recovery

## 1. Information

| Field | Value |
| --- | --- |
| Name | Nguyễn Quốc Việt |
| MSSV | 2A202601737 |
| Class | K3 |
| Group | VitaminB4 |
| Role | Role 2 — Data Platform & Recovery |

## 2. Owned work

| Module | Input | Output |
| --- | --- | --- |
| `src/ingestion/crossref.py` | Crossref REST payload | Raw API response and DOI-keyed `PaperRecord` JSON |
| `src/ingestion/cleaning.py` | Raw records | Clean CSV/JSON with embedding and freshness fields |
| `src/ingestion/corruption.py` | Baseline clean dataframe | Auditable corrupted dataframe and log |
| Repair flow | Raw snapshot | Rebuilt repaired clean dataframe |

## 3. Technical implementation

Crossref records are parsed into a stable schema. The DOI is normalized to lowercase and used as the durable `paper_id`. The fetcher persists the original API response before parsing and retries temporary API failures. Cleaning normalizes title, abstract, authors and categories; deduplicates by DOI; computes `summary_chars` and `age_days`; and builds `text_for_embedding` from title, authors, and summary.

The corruption experiment is deterministic and logged. It drops two latest records by publication timestamp, blanks summaries, injects noise, truncates a title, shifts one publication date into the stale range, and appends one duplicate. Repair does not edit the corrupted dataset: it reloads `data/raw/crossref_records.json` and reruns the cleaning function.

## 4. Evidence

| Artifact | Result |
| --- | --- |
| `data/raw/crossref_response.json` | Original Crossref response persisted |
| `data/raw/crossref_records.json` | 24 parsed records |
| `data/clean/papers_clean.csv` | 24 clean DOI-unique records |
| `data/results/corruption_log.json` | Six corruption scenarios with affected paper IDs |
| `data/clean/papers_clean_corrupted.csv` | 23 corrupted rows |
| `data/clean/papers_clean_repaired.csv` | 24 records rebuilt from raw snapshot |

The corrupted quality report fails duplicate, summary completeness, summary-length, and freshness checks. The repaired dataset passes all quality checks and freshness returns to `fresh`.

## 5. Verification

```powershell
python script/run_phase1.py
python script/run_corruption_flow.py
```

The comparison shows that corruption reduced retrieval hit rate from 1.000 to 0.750 and mean token F1 from 1.000 to 0.667. Rebuilding from raw restored both values to 1.000.

## 6. Key decision

Using DOI as `paper_id` preserves lineage from Crossref through clean data, Chroma metadata, and evaluation ground truth. Using the raw snapshot for repair ensures recovery is reproducible and demonstrates actual data restoration rather than masking errors in the corrupted output.

## 7. Confirmation

- [x] The report uses artifacts produced by the pipeline.
- [x] Repair is performed from raw data, not manual correction.
- [x] No API key or secret is included.
