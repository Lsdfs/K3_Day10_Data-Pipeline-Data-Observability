# BÁO CÁO CÁ NHÂN — NGUYỄN QUANG HUY

| Thông tin | Nội dung |
| --- | --- |
| MSSV | 2A202601873 |
| Khóa/Lớp | K3 |
| Vai trò | Tích hợp Data Pipeline |
| Repository | <https://github.com/Bietdoibongdem888/K3_Day10_Data-Pipeline-Data-Observability> |
| Ngày lập báo cáo kỹ thuật | 2026-08-06 |

## Phạm vi và kết quả

Phạm vi gồm `src/retrieval/`, `src/evaluation/`, `src/pipelines/`, CLI và kiểm thử end-to-end. Pipeline đã tạo ba Chroma collection, ba manifest, evaluation set 6 câu, metrics/answers của ba trạng thái và comparison artifact.

## Contract đầu vào/đầu ra

- **Input:** cleaned dataframe có `paper_id`, `title`, `text_for_embedding` và metadata; test set có ground-truth DOI.
- **Output:** persistent Chroma index, ranked `SearchResult`, `AnswerResult`, metrics và answers JSON.
- **Phụ thuộc:** cleaning, embedding adapter, provider config, observability report.
- **Điều kiện lỗi:** index rỗng; dimension embedding không nhất quán; baseline artifact thiếu trước corruption; model/LLM không truy cập được.

## Cách triển khai

Index tạo record ID theo `paper_id::row_index` để duplicate scenario vẫn được index nhưng quality có thể bắt DOI trùng. Retrieval dùng cosine distance và đổi thành similarity. QA ưu tiên exact title trong dấu nháy trước semantic results, rồi extract đúng field theo question type. Evaluation dùng cùng test set và tính retrieval hit, token F1, judge accuracy/score; judge có fallback deterministic khi LLM không sẵn sàng.

## Quyết định kỹ thuật quan trọng

MiniLM là backend chính; thay vì để toàn pipeline chết khi model chưa cache và Hugging Face mất DNS, adapter có local feature hashing fallback và ghi `embedding_backend`/`fallback_reason` vào manifest. `REQUIRE_MINILM=true` hỗ trợ môi trường bắt buộc MiniLM. Trade-off là fallback reproducible nhưng kém semantic hơn transformer.

## Vấn đề đã xử lý

Manifest ban đầu lưu absolute Chroma path, làm artifact không portable. Path đã đổi thành `data/chroma` tương đối project root; loader resolve lại ở máy chạy. Test build/load/search xác minh contract.

## Kiểm thử

`tests/test_index.py`, `tests/test_evaluation_quality.py`, `tests/test_cli_visualization.py`; lệnh `uv run pytest -q --basetemp .pytest_tmp` cho kết quả `9 passed`. Hai CLI flow exit code 0 và audit PASS.

## Phân tích kết quả

Việc drop 4/6 DOI xuất hiện trong test set là nguyên nhân chính làm retrieval hit rate giảm còn `0.3333`; câu trả lời sai document kéo token F1 còn `0.3690`. Rebuild từ raw phục hồi đồng thời index và metrics về baseline.

## Trạng thái xác nhận

- [x] Code/test/artifact kỹ thuật đã kiểm chứng.
- [x] Không chứa secret.
- [ ] Nguyễn Quang Huy đã tự đọc và xác nhận nội dung bằng lời của mình.
- [ ] Commit/PR đúng danh tính đã được liên kết.

**Chữ ký/ngày xác nhận của thành viên:** Chưa xác nhận.
