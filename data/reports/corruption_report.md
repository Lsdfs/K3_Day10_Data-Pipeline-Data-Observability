# Báo cáo corruption và repair

## Metrics comparison

| Metric | Baseline | Corrupted | Repaired | Corruption Δ | Repair Δ |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | -0.5000 | +0.5000 |
| `mean_token_f1` | 1.0000 | 0.6509 | 1.0000 | -0.3491 | +0.3491 |
| `judge_accuracy` | 1.0000 | 0.6250 | 1.0000 | -0.3750 | +0.3750 |
| `mean_judge_score` | 5.0000 | 3.5000 | 5.0000 | -1.5000 | +1.5000 |

## Observability comparison

| State | Quality | Pass/Fail checks | Freshness | Stale rows/rate |
| --- | --- | ---: | --- | ---: |
| Corrupted | FAIL | 10/5 | stale_or_invalid | 1/0.047619 |
| Repaired | PASS | 15/0 | fresh | 0/0.0 |

## Kết luận có bằng chứng

Corruption được đánh giá bằng cùng test-set hash với baseline; repair dựng lại dữ liệu từ raw snapshot rồi chạy lại cleaning, index, evaluation và observability. Chỉ những thay đổi thể hiện trong bảng metrics mới được dùng làm kết luận.
