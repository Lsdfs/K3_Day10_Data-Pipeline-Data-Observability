# Báo cáo corruption và repair

## So sánh metrics

| Metric | Baseline | Corrupted | Repaired | Corruption Δ | Repair Δ |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 0.3333 | 1.0000 | -0.6667 | +0.6667 |
| `mean_token_f1` | 1.0000 | 0.3690 | 1.0000 | -0.6310 | +0.6310 |
| `judge_accuracy` | 1.0000 | 0.3333 | 1.0000 | -0.6667 | +0.6667 |
| `mean_judge_score` | 5.0000 | 2.3333 | 5.0000 | -2.6667 | +2.6667 |

## Data observability

| Trạng thái | Quality | Pass/Fail checks | Freshness | Stale rows |
| --- | --- | ---: | --- | ---: |
| Corrupted | FAIL | 5/2 | stale_or_invalid | 1 |
| Repaired | PASS | 7/0 | fresh | 0 |

## Phân tích nhân quả

1. Xóa bản ghi mới, làm rỗng summary, chèn noise, cắt title, làm cũ ngày và tạo duplicate làm các quality/freshness signal chuyển xấu; cùng test set cố định ghi nhận thay đổi ở retrieval và answer metrics.
2. Repair xây lại dữ liệu từ raw snapshot đáng tin cậy, không chỉnh trực tiếp dữ liệu corrupted. Quality/freshness và agent metrics vì vậy được đo lại độc lập trên index repaired.

Nếu một metric không giảm, kết luận phù hợp là corruption đó chưa tác động đến metric trên test set/top-k hiện tại; không suy diễn tác động khi số liệu không hỗ trợ.
