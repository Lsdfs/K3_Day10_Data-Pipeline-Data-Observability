# BÁO CÁO CÁ NHÂN — NGUYỄN QUANG HUY

| Thông tin | Nội dung |
| --- | --- |
| MSSV | 2A202601873 |
| Khóa/Lớp | K3 |
| Vai trò | Thành viên — ROLE 1 phần nhóm |
| Repository | <https://github.com/Lsdfs/K3_Day10_Data-Pipeline-Data-Observability> |
| Nhánh | `NGUYENQUANGHUY` |
| Ngày kiểm chứng | 2026-08-06 |

## 1. Phạm vi ROLE 1

ROLE 1 sở hữu kiến trúc tổng thể, integration contract, orchestration baseline/corruption/repair, CLI, end-to-end validation, artifact audit, README, group report, Rubric audit và submission checklist. Các thuật toán chuyên môn của ingestion/cleaning/observability được tích hợp qua public functions; báo cáo này không nhận công việc của thành viên khác làm đóng góp cá nhân.

## 2. Architecture và integration

Luồng tích hợp:

Crossref/raw snapshot → cleaning → clean CSV/JSON → embedding/Chroma baseline → retrieval/QA → evaluation → quality/freshness → corruption → corrupted evaluation → repair từ raw → repaired evaluation → comparison report/CSV/SVG.

Contract quan trọng là DOI/stable ID đi xuyên suốt từ `PaperRecord` đến Chroma metadata và `ground_truth_doc_ids`. Ba collection và ba manifest tách riêng; cùng test-set hash được kiểm tra trước khi tạo comparison.

## 3. Orchestration và CLI

`pipelines.common.run_stage` bọc mỗi stage bằng tên lỗi rõ, không swallow exception. `phase1.main` nối 16 stage baseline; `corruption_flow.main` kiểm tra baseline immutable, repair từ raw và chạy lại toàn bộ evaluation/observability. CLI chỉ điều phối module và hỗ trợ `baseline`, `corruption`, `all`, `audit`.

## 4. Artifact validation

Audit kiểm tra file tồn tại/không rỗng, strict JSON, CSV không rỗng, metrics range, test-set hash, corruption degradation, repair recovery, implementation markers, placeholders/URL cũ, machine path, tracked junk và secret signature. Output: `data/reports/audit_report.json`.

## 5. Quyết định kỹ thuật

- **Bối cảnh:** Hugging Face/model cache không phải lúc nào cũng sẵn sàng.
- **Phương án:** bắt buộc MiniLM và fail; hoặc fallback ngầm; hoặc explicit opt-in fallback có manifest.
- **Chọn:** `ALLOW_EMBEDDING_FALLBACK=true` cùng `EMBEDDING_BACKEND=hashing`; mặc định vẫn MiniLM/fallback false.
- **Lý do:** pipeline offline tái hiện được nhưng không fake backend. Manifest ghi model null, backend fallback, dimension 384 và lý do.
- **Bằng chứng:** ba embedding manifests và index tests.

## 6. Lỗi đã xử lý

- **Triệu chứng:** flow in “PASS” nhưng command exit code 1 sau khi mọi artifact đã sinh.
- **Root cause:** Windows console `charmap` không encode Unicode arrow trong summary.
- **Sửa:** đổi terminal summary thành ASCII `->`; không thay metrics/report.
- **Xác minh:** `day10-pipeline corruption` chạy lại exit code 0; hit rate `1.0000 -> 0.5000 -> 1.0000`.

## 7. Kết quả thực tế

| Signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 1.0000 | 0.5000 | 1.0000 |
| Token F1 | 1.0000 | 0.6509 | 1.0000 |
| Judge accuracy | 1.0000 | 0.6250 | 1.0000 |
| Judge score | 5.0000 | 3.5000 | 5.0000 |
| Quality | PASS | FAIL | PASS |
| Freshness | fresh | stale_or_invalid | fresh |

Test suite có 15 tests; smoke test chạy hai flow offline trên fixture. LLM judge và Ragas không được bật, nên báo cáo chỉ ghi heuristic mode.

## 8. Lệnh xác minh

```powershell
python -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_runtime
python -m compileall src script
day10-pipeline --help
day10-pipeline all
day10-pipeline audit
git diff --check
```

## 9. Điều học được

1. Orchestration phải kiểm tra identity/test-set hash chứ không chỉ kiểm tra file tồn tại.
2. Data observability cần failed count/rate và threshold để giải thích metric degradation.
3. Offline fallback chỉ đáng tin khi opt-in và artifact tự mô tả backend thật.

## 10. Git và xác nhận

Base commit trước thay đổi ROLE 1: `9f2bd15`. Commit cho thay đổi hiện tại chưa được tạo vì prompt yêu cầu chỉ commit khi người dùng cho phép. Pull Request và chữ ký không được tạo giả.

**Chữ ký:** Nguyễn Quang Huy tự bổ sung sau khi review nội dung; Codex không ký thay.
