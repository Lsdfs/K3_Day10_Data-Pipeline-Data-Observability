# BÁO CÁO CÁ NHÂN — NGUYỄN QUỐC VIỆT

| Thông tin | Nội dung |
| --- | --- |
| MSSV | 2A202601737 |
| Khóa/Lớp | K3 |
| Vai trò | Data Ingestion |
| Repository | <https://github.com/Bietdoibongdem888/K3_Day10_Data-Pipeline-Data-Observability> |
| Ngày lập báo cáo kỹ thuật | 2026-08-06 |

## Phạm vi và kết quả

Phạm vi là `src/ingestion/crossref.py`: gọi Crossref, retry/timeout/backoff, parse payload và lưu raw artifacts. Lần chạy tạo 24 `PaperRecord` tại `data/raw/crossref_records.json` cùng response nguyên gốc để truy vết.

## Contract đầu vào/đầu ra

- **Input:** endpoint, query, filter, rows, timeout, max attempts và backoff từ `Settings`/environment.
- **Output:** list `PaperRecord`; raw API response; parsed raw records.
- **Schema:** DOI, title, abstract, authors, subjects, dates, URLs/PDF và comment.
- **Điều kiện lỗi:** 429/5xx, timeout/DNS, JSON sai schema, không có usable records.

## Cách triển khai

Request gửi `query`, `filter`, `rows` và `select`. Các status 408/425/429/500/502/503/504 được retry; delay ưu tiên `Retry-After`, nếu thiếu thì exponential backoff `base × 2^(attempt-1)`. Parse bỏ item không có DOI/title, deduplicate DOI, strip HTML/JATS, chuẩn hóa whitespace, ghép tên tác giả và ưu tiên published date theo thứ tự print/online/published/issued/created.

## Quyết định kỹ thuật quan trọng

Raw response và parsed records được lưu riêng. Chỉ lưu parsed records thì nhẹ nhưng mất khả năng audit parser; lưu cả hai tăng dung lượng nhỏ nhưng cho phép tái hiện cleaning/repair không cần gọi API lại. Corruption repair vì vậy dùng raw snapshot làm nguồn tin cậy.

## Vấn đề đã xử lý

External API có thể trả 503/429 tạm thời. Thay vì retry vô hạn, số attempt, timeout và base backoff đều cấu hình được, có lỗi cuối rõ ràng. Unit test mock chuỗi `503 → 200`, bỏ sleep và xác minh hai file được persist.

## Kiểm thử và bằng chứng

`tests/test_crossref.py` kiểm tra HTML/date/author normalization, lowercase DOI, retry và round-trip `load_raw_records`. Pipeline live fetch đã tạo `data/raw/crossref_response.json` và 24 records.

## Hiểu tác động downstream

DOI ổn định là khóa deduplicate và ground-truth retrieval. Published date sai làm freshness sai; abstract rỗng bị cleaning loại. Vì vậy ingestion schema không chỉ phục vụ ETL mà quyết định trực tiếp chất lượng index/evaluation.

## Trạng thái xác nhận

- [x] Code/test/artifact kỹ thuật đã kiểm chứng.
- [x] Không chứa secret.
- [ ] Nguyễn Quốc Việt đã tự đọc và xác nhận nội dung bằng lời của mình.
- [ ] Commit/PR đúng danh tính đã được liên kết.

**Chữ ký/ngày xác nhận của thành viên:** Chưa xác nhận.
