# PHÂN CÔNG CÔNG VIỆC — DAY 10

Repository: <https://github.com/Lsdfs/K3_Day10_Data-Pipeline-Data-Observability>

## Chu Thị Yến Khanh — 2A202601739

- **Vai trò:** Trưởng nhóm.
- **Phần việc/module:** quản lý tiến độ, review chất lượng, GitHub/PR, tổng hợp báo cáo, slide và trình bày.
- **Input:** code, test output, metrics, quality/freshness và Rubric audit.
- **Output:** quyết định review, slide, phê duyệt submission.
- **Artifact:** `report/group_report.md`, `RUBRIC_AUDIT.md`, slide do trưởng nhóm quản lý.
- **Test xác minh:** `day10-pipeline audit`, review thủ công đường dẫn/metrics.
- **Dependency:** output của ba thành viên và ROLE 1 integration.
- **Definition of Done:** audit/report khớp artifact; PR/slide do Chu Thị Yến Khanh tự tạo và xác nhận.
- **Bằng chứng hiện tại:** group report/audit có; không suy diễn commit, PR, slide hoặc chữ ký cá nhân.

## Nguyễn Quang Huy — 2A202601873

- **Vai trò:** Thành viên — ROLE 1 phần nhóm.
- **Phần việc/module:** architecture; pipeline integration; baseline/corruption/repair orchestration; CLI; end-to-end validation; README; group report; audit; artifact validation; submission checklist.
- **Input:** contracts ingestion/cleaning/retrieval/evaluation/observability và raw snapshot.
- **Output:** `src/pipelines/`, CLI `day10-pipeline`, ba flow, comparison artifacts, project docs/audit.
- **Artifact:** toàn bộ `data/`, `README.md`, `report/group_report.md`, `RUBRIC_AUDIT.md`, `SUBMISSION_CHECKLIST.md`.
- **Test xác minh:** `tests/test_reporting_pipeline.py` và toàn suite; CLI baseline/corruption/all/audit.
- **Dependency:** các module chuyên môn; Crossref hoặc raw snapshot; MiniLM hay explicit fallback.
- **Definition of Done:** architecture khớp code; flow/CLI/tests/audit PASS; reports đọc trực tiếp artifact; không secret/placeholder.
- **Bằng chứng hiện tại:** code, tests và artifact Role 1 có; commit mới chỉ tạo khi người dùng cho phép.

## Nguyễn Quốc Việt — 2A202601737

- **Vai trò:** Thành viên.
- **Phần việc/module:** Crossref ingestion, retry, timeout, exponential backoff, raw dataset/JSON và unit tests ingestion.
- **Input:** Crossref query/filter/settings.
- **Output:** `PaperRecord`, raw response/records và ingestion summary.
- **Artifact:** `data/raw/`.
- **Test xác minh:** `tests/test_crossref.py` dùng mock, không phụ thuộc Internet.
- **Dependency:** `core.config`, Crossref REST API.
- **Definition of Done:** parse thiếu field/fallback ID/deduplicate; retry 429/5xx; persist raw artifacts; tests PASS.
- **Bằng chứng hiện tại:** implementation/test/artifact tích hợp có; ownership/commit cần Nguyễn Quốc Việt tự review và xác nhận.

## Diêm Công Thành — 2A202601689

- **Vai trò:** Thành viên.
- **Phần việc/module:** cleaning, normalize/deduplicate, corruption/repair, quality/freshness, reporting/visualization và tests liên quan.
- **Input:** raw `PaperRecord`, baseline dataframe, metrics payload.
- **Output:** clean/corrupted/repaired datasets; quality/freshness; log/report/SVG.
- **Artifact:** `data/clean/`, `data/quality/`, `data/results/corruption_log.json`, `data/reports/`.
- **Test xác minh:** `tests/test_cleaning_corruption.py`, `tests/test_quality_evaluation.py`.
- **Dependency:** ingestion schema, Settings, evaluation metrics.
- **Definition of Done:** deterministic/non-mutating corruption; repair từ raw; observability phát hiện và phục hồi; tests PASS.
- **Bằng chứng hiện tại:** implementation/test/artifact tích hợp có; ownership/commit cần Diêm Công Thành tự review và xác nhận.

Không file nào trong tài liệu này thay thế bằng chứng commit/PR/chữ ký thật của từng thành viên.
