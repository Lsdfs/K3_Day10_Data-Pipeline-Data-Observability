# BÁO CÁO CÁ NHÂN — CHU THỊ YẾN KHANH

| Thông tin | Nội dung |
| --- | --- |
| MSSV | 2A202601739 |
| Khóa/Lớp | K3 |
| Vai trò | Nhóm trưởng |
| Repository | <https://github.com/Bietdoibongdem888/K3_Day10_Data-Pipeline-Data-Observability> |
| Ngày lập báo cáo kỹ thuật | 2026-08-06 |

## Phạm vi và kết quả

Phạm vi gồm quản lý deliverable, review tích hợp, đối chiếu Rubric, tổng hợp báo cáo và chuẩn bị nội dung trình bày. Output hiện có là `PHAN_CONG_CONG_VIEC.md`, `report/group_report.md`, hai báo cáo pipeline và biểu đồ SVG. Audit kiểm tra 15 artifact và marker code chưa hoàn thiện đã PASS.

## Contract đầu vào/đầu ra

- **Input:** README/Guide/Rubric, code, test output, raw/clean/eval/result/quality artifacts.
- **Output:** báo cáo nhóm khớp số liệu, checklist bàn giao, mapping owner → module → artifact → test.
- **Điều kiện lỗi:** báo cáo ghi metric không trùng JSON; thiếu artifact; secret; claim hoàn thành không có bằng chứng.
- **Cách xác minh:** `uv run day10-pipeline audit` và đọc chéo `data/results/comparison_metrics.json`.

## Quyết định kỹ thuật quan trọng

Giữa việc báo cáo MiniLM theo cấu hình và báo cáo backend thực chạy, phương án được chọn là ghi cả hai và nêu rõ artifact dùng `local_hashing_fallback` do DNS Hugging Face. Cách này bảo toàn tính truy vết và tránh kết luận sai. Manifest embedding là bằng chứng.

## Vấn đề tích hợp đã xử lý

Traceback test cho thấy Settings từng có thể đọc `.env` từ thư mục cha và in key trong `repr`. Root cause là phạm vi dotenv quá rộng và dataclass không ẩn field nhạy cảm. Cấu hình đã giới hạn về project root và các key dùng `repr=False`; test được chạy lại thành công.

## Hiểu luồng end-to-end

Crossref response được parse thành `PaperRecord`, làm sạch và tạo `text_for_embedding`, sau đó build Chroma. Test set gắn ground-truth DOI để đo retrieval hit và câu trả lời. Quality kiểm tra completeness/uniqueness/validity/timeliness; freshness tập trung vào tuổi dữ liệu. Corruption dùng cùng test set để cô lập tác động của data; repair chỉ thành công khi quality/freshness và agent metric phục hồi từ raw snapshot.

## Số liệu chính

Retrieval hit rate `1.0000 → 0.3333 → 1.0000`; token F1 `1.0000 → 0.3690 → 1.0000`; quality `PASS → FAIL → PASS`; freshness `fresh → stale_or_invalid → fresh`.

## Trạng thái xác nhận

- [x] Nội dung kỹ thuật có artifact đối chiếu.
- [x] Không chứa secret.
- [ ] Chu Thị Yến Khanh đã tự đọc và xác nhận nội dung bằng lời của mình.
- [ ] Commit/PR và slide đúng danh tính đã được liên kết.

**Chữ ký/ngày xác nhận của thành viên:** Chưa xác nhận.
