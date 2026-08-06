# PHÂN CÔNG CÔNG VIỆC — DAY 10

Repository: <https://github.com/Bietdoibongdem888/K3_Day10_Data-Pipeline-Data-Observability>

Ngày đối chiếu artifact: 2026-08-06.

## 1. Chu Thị Yến Khanh — 2A202601739

- **Vai trò:** Nhóm trưởng.
- **Module phụ trách:** quản lý tiến độ, review tích hợp, audit Rubric, báo cáo nhóm, slide và trình bày.
- **Input:** code của các module, kết quả test, `data/results/`, `data/quality/`, README/Guide/Rubric.
- **Output:** `report/group_report.md`, checklist audit, nội dung tổng hợp để làm slide.
- **Artifact:** `report/group_report.md`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md`, `data/reports/metrics_comparison.svg`.
- **Test/xác minh:** `uv run day10-pipeline audit`; `uv run pytest -q --basetemp .pytest_tmp`.
- **Definition of Done:** báo cáo khớp artifact; audit PASS; không secret; review đủ Rubric; slide được nhóm trưởng tự xác nhận.
- **Trạng thái có bằng chứng:** code/report/audit đã có; **commit/PR và slide do đúng thành viên thực hiện chưa có bằng chứng trong repository hiện tại, không đánh dấu hoàn thành**.

## 2. Nguyễn Quang Huy — 2A202601873

- **Vai trò:** Thành viên, tích hợp Data Pipeline.
- **Module phụ trách:** embedding/index, retrieval, evaluation, orchestration, CLI và kiểm thử end-to-end.
- **Input:** cleaned dataframe, evaluation set, cấu hình embedding/LLM.
- **Output:** Chroma collections, embedding manifests, answers/metrics, CLI baseline/corruption/audit.
- **Artifact:** `data/chroma/`, `data/embeddings/`, `data/eval/test_set.json`, `data/results/*metrics.json`, `data/results/*answers.json`.
- **Test/xác minh:** `tests/test_index.py`, `tests/test_evaluation_quality.py`, `tests/test_cli_visualization.py`; hai lệnh pipeline CLI.
- **Definition of Done:** build/load/query index; cùng test set cho ba trạng thái; metrics và answers được lưu; baseline và corruption flow chạy xong; audit PASS.
- **Trạng thái có bằng chứng:** code, test và artifact đã kiểm chứng; **commit theo đúng danh tính thành viên cần Nguyễn Quang Huy tạo/xác nhận**.

## 3. Nguyễn Quốc Việt — 2A202601737

- **Vai trò:** Thành viên, Data Ingestion.
- **Module phụ trách:** Crossref API, parse schema, timeout, retry, exponential backoff, raw JSON.
- **Input:** query/filter/settings và Crossref payload.
- **Output:** danh sách `PaperRecord`, raw response và raw record snapshot.
- **Artifact:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`.
- **Test/xác minh:** `tests/test_crossref.py` kiểm tra normalize schema, retry 503 và load snapshot.
- **Definition of Done:** timeout cấu hình được; retry/backoff có giới hạn; parse ổn định; lưu đủ hai raw artifact; unit test PASS.
- **Trạng thái có bằng chứng:** code, test và artifact đã kiểm chứng; **commit theo đúng danh tính thành viên cần Nguyễn Quốc Việt tạo/xác nhận**.

## 4. Diêm Công Thành — 2A202601689

- **Vai trò:** Thành viên, Cleaning và Data Observability.
- **Module phụ trách:** normalize, deduplicate, corruption, repair, quality/freshness, reporting, visualization.
- **Input:** `PaperRecord`, clean baseline và metrics của ba trạng thái.
- **Output:** clean/corrupted/repaired datasets; corruption log; quality/freshness reports; Markdown report và SVG.
- **Artifact:** `data/clean/`, `data/quality/`, `data/results/corruption_log.json`, `data/reports/`.
- **Test/xác minh:** `tests/test_cleaning_corruption.py`, phần quality/freshness trong `tests/test_evaluation_quality.py`, `tests/test_cli_visualization.py`.
- **Definition of Done:** schema sạch và deduplicate; sáu corruption có log; repair từ raw; quality/freshness phát hiện lỗi và phục hồi; report/visualization khớp metrics.
- **Trạng thái có bằng chứng:** code, test và artifact đã kiểm chứng; **commit theo đúng danh tính thành viên cần Diêm Công Thành tạo/xác nhận**.

## Quy tắc bàn giao Git

Không sửa lịch sử, không force-push và không gán sai tác giả. Mỗi thành viên cần tạo commit/PR cho phần mình thực sự review và sở hữu. File này không thay thế bằng chứng GitHub.
