# BÁO CÁO NHÓM — DAY 10 DATA PIPELINE & DATA OBSERVABILITY

## 1. Thông tin chung

| Thuộc tính | Nội dung |
| --- | --- |
| Khóa/Lớp | K3 |
| Repository | <https://github.com/Bietdoibongdem888/K3_Day10_Data-Pipeline-Data-Observability> |
| Ngày hoàn thành kỹ thuật | 2026-08-06 |
| Trạng thái audit | PASS |

| Thành viên | MSSV | Vai trò chính |
| --- | --- | --- |
| Chu Thị Yến Khanh | 2A202601739 | Nhóm trưởng, audit và báo cáo |
| Nguyễn Quang Huy | 2A202601873 | Pipeline, embedding/index, retrieval, evaluation |
| Nguyễn Quốc Việt | 2A202601737 | Crossref ingestion, retry/backoff, raw artifacts |
| Diêm Công Thành | 2A202601689 | Cleaning, corruption/repair, quality, reporting |

Phân công chi tiết và trạng thái bằng chứng Git nằm tại `PHAN_CONG_CONG_VIEC.md`.

## 2. Tóm tắt kết quả

Pipeline đã chạy end-to-end với 24 bản ghi Crossref: raw → clean → Chroma → evaluation → observability → corruption → repair → comparison. Cùng evaluation set 6 câu được giữ nguyên cho cả ba trạng thái. Retrieval hit rate giảm từ `1.0000` xuống `0.3333` sau corruption và phục hồi về `1.0000`; mean token F1 giảm từ `1.0000` xuống `0.3690` rồi phục hồi về `1.0000`.

## 3. Cấu hình lần chạy

| Cấu hình | Giá trị |
| --- | --- |
| Source | Crossref REST API `/works` |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | 180 ngày gần nhất và có abstract |
| Raw/Clean records | 24 / 24 |
| Retrieval top-k | 4 |
| Embedding model cấu hình | `sentence-transformers/all-MiniLM-L6-v2` |
| Backend artifact thực tế | `local_hashing_fallback` |
| Lý do fallback | DNS tới Hugging Face thất bại trong lần chạy; manifest ghi rõ backend |
| LLM mặc định | Gemini `gemini-2.5-flash` nếu có key |
| Evaluation lần này | extractive QA + heuristic judge; Ragas tắt |
| Randomness | corruption và test-set xác định, không dùng random |

MiniLM vẫn là backend ưu tiên trong code. `REQUIRE_MINILM=true` dùng để fail-fast nếu không cho phép fallback; `EMBEDDING_OFFLINE_FALLBACK=true` cho phép tái hiện hoàn toàn offline.

## 4. Data contract và cleaning

Raw schema gồm `paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, `comment`. Cleaning yêu cầu ID, title, summary và published hợp lệ; chuẩn hóa whitespace/HTML; chuyển ngày sang ISO; deduplicate theo DOI; tạo `authors_joined`, `categories_joined`, `summary_chars`, `age_days` và `text_for_embedding`.

Document ID là DOI lowercase. `text_for_embedding` ghép title, abstract, authors, categories và published theo nhãn rõ ràng. `age_days` là chênh lệch giữa ngày chạy UTC và ngày xuất bản.

## 5. Evaluation

Evaluation set có 6 câu thuộc bốn loại `summary`, `authors`, `date`, `categories`. Ground truth document ID lấy trực tiếp từ DOI của row được chọn. Giữ nguyên `data/eval/test_set.json` giữa ba trạng thái là điều kiện để thay đổi metric phản ánh thay đổi dữ liệu/index, không phải thay đổi câu hỏi.

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 0.3333 | 1.0000 |
| `mean_token_f1` | 1.0000 | 0.3690 | 1.0000 |
| `judge_accuracy` | 1.0000 | 0.3333 | 1.0000 |
| `mean_judge_score` | 5.0000 | 2.3333 | 5.0000 |
| Ragas | Tắt | Tắt | Tắt |

Ragas được giữ là tùy chọn `RUN_RAGAS=true` vì cần LLM credential và chi phí/thời gian ngoài đường chạy mặc định.

## 6. Quality và freshness

Baseline đạt 7/7 checks; corrupted đạt 5/7; repaired đạt 7/7. Corrupted fail uniqueness vì có 2 row thuộc một DOI duplicate và fail timeliness vì 1 row cũ hơn 180 ngày. Freshness chuyển `fresh → stale_or_invalid → fresh`.

| Signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Rows | 24 | 21 | 24 |
| Duplicate rows | 0 | 2 | 0 |
| Stale rows | 0 | 1 | 0 |
| Quality overall | PASS | FAIL | PASS |
| Freshness | fresh | stale_or_invalid | fresh |

## 7. Corruption và repair

`data/results/corruption_log.json` ghi sáu scenario: xóa 4 latest records; blank 1 summary; inject noise 1 summary; truncate 1 title; dịch 1 published date lùi 3650 ngày; thêm 1 duplicate. Mỗi scenario ghi count, DOI và tham số liên quan.

Repair không sửa trực tiếp corrupted rows. Pipeline đọc lại `data/raw/crossref_records.json`, chạy lại cùng cleaning contract, build collection `papers-repaired` và đánh giá bằng test set cũ.

Chuỗi bằng chứng nhân quả:

1. Drop latest records và phá nội dung → retrieval hit rate `1.0000 → 0.3333`, token F1 `1.0000 → 0.3690`; duplicate/stale đồng thời làm quality/freshness fail.
2. Rebuild từ raw snapshot → rows `21 → 24`, quality `FAIL → PASS`, freshness `stale_or_invalid → fresh`, retrieval/F1 trở lại `1.0000`.

Biểu đồ: `data/reports/metrics_comparison.svg`.

## 8. Artifact checklist

| Artifact | Trạng thái |
| --- | --- |
| `data/raw/` response + records | Có |
| `data/clean/` baseline/corrupted/repaired | Có |
| `data/chroma/` ba collections | Có |
| `data/embeddings/` ba manifests | Có |
| `data/eval/test_set.json` | Có |
| `data/results/` metrics + answers + corruption log | Có |
| `data/quality/` quality + freshness | Có |
| `data/reports/` Markdown + SVG | Có |

## 9. Kiểm thử và lệnh tái hiện

```powershell
uv sync --extra dev
uv run pytest -q --basetemp .pytest_tmp
$env:EMBEDDING_OFFLINE_FALLBACK='true'
uv run day10-pipeline all
uv run day10-pipeline audit
```

Kết quả xác minh: `9 passed`; baseline và corruption CLI exit code 0; audit PASS với 15/15 artifact và không còn marker chưa triển khai trong `src/`.

## 10. Vấn đề tích hợp và giới hạn

- Hugging Face không phân giải DNS trong lần chạy, nên artifact hiện tại dùng fallback hashing. Manifest không ghi sai backend; khi mạng/cache sẵn sàng, MiniLM tự được dùng.
- LLM judge/Ragas không chạy mặc định khi không có credential. Heuristic judge giúp pipeline deterministic, nhưng không thay thế đánh giá ngữ nghĩa của LLM trên câu trả lời mở.
- Test set 6 câu phù hợp lab nhỏ nhưng chưa đủ đại diện production; cải thiện tiếp theo là tăng số câu và stratify theo chủ đề/thời gian.
- Bằng chứng commit/PR theo đúng từng thành viên chưa thể suy ra từ working tree; từng thành viên phải tự review, commit và xác nhận báo cáo cá nhân.
