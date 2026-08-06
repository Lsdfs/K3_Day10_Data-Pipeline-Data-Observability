# RUBRIC AUDIT — DAY 10

Audit ngày 2026-08-06 trên nhánh `NGUYENQUANGHUY`. Không tự tuyên bố 100/100; trạng thái dựa trên lệnh và artifact thực tế.

| Hạng mục | Điểm tối đa | Code bằng chứng | Artifact bằng chứng | Lệnh kiểm tra | Trạng thái |
| --- | ---: | --- | --- | --- | --- |
| Code structure | 10 | `src/core`, `ingestion`, `retrieval`, `evaluation`, `observability`, `pipelines` | audit report | `python -m compileall src script` | PASS |
| Raw ingestion | 15 | `src/ingestion/crossref.py` | `data/raw/` (24 valid records, 1 attempt) | tests + baseline | PASS |
| Cleaning/modeling | 15 | `src/ingestion/cleaning.py` | baseline/corrupted/repaired CSV/JSON | cleaning tests | PASS |
| Embedding/vector store | 10 | `retrieval/embeddings.py`, `index.py` | ba manifest + Chroma collections | index test | PASS |
| Agent/multi-provider | 10 | `agent.py`, `qa.py`, `llm.py` | QA demo; heuristic evaluation answers | provider tests | PASS |
| Evaluation/scoring | 10 | `evaluation/testset.py`, `metrics.py` | 8-item test set, metrics + answers | evaluation tests | PASS |
| Data observability | 10 | `observability/quality.py` | 15 checks/state + freshness | quality tests | PASS |
| Corruption/comparison | 10 | `corruption.py`, `corruption_flow.py` | log, comparison JSON/CSV/MD/SVG | corruption flow | PASS |
| Bonus: reports/visualization/tests/CLI | N/A | reporting, visualization, CLI, 15 tests | docs + SVG + audit | `day10-pipeline audit` | PASS |

## Ghi chú trung thực

- Vector store chạy Chroma; artifact hiện dùng explicit `local_hashing_fallback` 384 chiều. MiniLM code path tồn tại nhưng runtime MiniLM chưa được dùng trong artifact này.
- `judge_mode=["heuristic"]`; LLM judge/Ragas bị tắt, không có kết quả LLM giả.
- PASS của agent/provider dựa trên abstraction, offline validation và extractive QA; không khẳng định đã gọi thật mọi provider.
