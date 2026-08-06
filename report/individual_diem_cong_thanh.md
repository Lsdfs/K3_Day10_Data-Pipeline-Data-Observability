# BÁO CÁO CÁ NHÂN — DIÊM CÔNG THÀNH

| Thông tin | Nội dung |
| --- | --- |
| MSSV | 2A202601689 |
| Khóa/Lớp | K3 |
| Vai trò | Cleaning và Data Observability |
| Repository | <https://github.com/Bietdoibongdem888/K3_Day10_Data-Pipeline-Data-Observability> |
| Ngày lập báo cáo kỹ thuật | 2026-08-06 |

## Phạm vi và kết quả

Phạm vi gồm cleaning/modeling, corruption/repair, quality/freshness, Markdown reporting và visualization. Artifacts nằm ở `data/clean/`, `data/quality/`, `data/results/corruption_log.json` và `data/reports/`.

## Contract đầu vào/đầu ra

- **Input cleaning:** list `PaperRecord` và UTC run date.
- **Output cleaning:** dataframe 16 cột, DOI unique, ISO dates, helper fields và embedding text.
- **Input observability:** baseline/corrupted/repaired dataframe.
- **Output observability:** checks JSON, freshness JSON, reports và SVG.
- **Điều kiện lỗi:** dưới 8 rows cho experiment; thiếu required columns; invalid published date; artifact path không ghi được.

## Cách triển khai

Cleaning chuẩn hóa chuỗi/list/date, yêu cầu DOI/title/summary/published, deduplicate DOI và sort newest-first. Quality kiểm tra minimum rows, ID completeness/uniqueness, title completeness, tỷ lệ summary ≥40 ký tự, embedding text và `age_days`. Freshness thống kê latest/oldest, stale/invalid rows và status.

Corruption deterministic gồm sáu scenario: drop latest, blank summary, noise, truncated title, stale date và duplicate. Sau mutation, `text_for_embedding` được dựng lại để index thực sự nhận dữ liệu hỏng. Log ghi DOI/count/parameter. Repair gọi lại cleaning trên raw snapshot.

## Quyết định kỹ thuật quan trọng

Corruption không dùng random để cùng commit luôn tái hiện cùng tác động. Mỗi loại lỗi chạm record xác định và có log. Ưu điểm là so sánh ổn định; giới hạn là coverage cần mở rộng khi corpus lớn hơn.

## Vấn đề và xác minh

Nếu freshness chỉ nhìn latest timestamp, một stale row có thể bị che bởi row mới. Report vì vậy kiểm tra toàn bộ `age_days` và chỉ `fresh` khi không có stale/invalid row. Kết quả corrupted phát hiện đúng 1 stale row và repaired trở về 0.

## Số liệu chính

Baseline/repaired đạt 7/7 checks. Corrupted fail 2 checks (2 duplicate rows và 1 stale row). Quality `PASS → FAIL → PASS`; freshness `fresh → stale_or_invalid → fresh`. SVG trực quan hóa bốn evaluation metrics.

## Kiểm thử

`tests/test_cleaning_corruption.py`, phần quality/freshness trong `tests/test_evaluation_quality.py`, và `tests/test_cli_visualization.py`; toàn suite `9 passed`.

## Trạng thái xác nhận

- [x] Code/test/artifact kỹ thuật đã kiểm chứng.
- [x] Không chứa secret.
- [ ] Diêm Công Thành đã tự đọc và xác nhận nội dung bằng lời của mình.
- [ ] Commit/PR đúng danh tính đã được liên kết.

**Chữ ký/ngày xác nhận của thành viên:** Chưa xác nhận.
