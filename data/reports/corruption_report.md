# Corruption & Repair Comparison Report

## Metrics Comparison

| Metric | Baseline | Corrupted | Delta | Repaired | Delta vs Baseline |
|--------|----------|-----------|-------|----------|-------------------|
| Retrieval Hit Rate | 1.000 | 1.000 | +0.000 | 1.000 | +0.000 |
| Mean Token F1 | 0.963 | 0.841 | -0.122 | 0.963 | +0.000 |
| Judge Accuracy | 1.000 | 0.875 | -0.125 | 1.000 | +0.000 |
| Mean Judge Score | 4.4 | 4.0 | -0.417 | 4.4 | +0.000 |

## Quality Comparison

| Check | Corrupted | Repaired |
|-------|-----------|----------|
| Total rows | 25 | 24 |
| Unique paper_ids | 24 | 24 |
| Stale rows | 1 | 0 |

## Freshness Comparison

| Field | Corrupted | Repaired |
|-------|-----------|----------|
| Is fresh | NO | YES |

## Conclusion

The corruption flow demonstrates that data quality issues directly degrade agent performance.
Repairing from raw source data restores performance to near-baseline levels.
