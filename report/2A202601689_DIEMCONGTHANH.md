# Individual Report - Day 10: Data Pipeline & Data Observability

## 1. Thông Tin Cá Nhân

| Thông tin | Nội dung |
| Họ và tên | Diêm Công Thành |
| MSSV | 2A202601689 |
| Khóa/Lớp | Khóa 3 |
| Tên nhóm | VitaminB4 |
| Vai trò chính | Vai trò 3 - RAG & agent |
| Phạm vi | MiniLM, Chroma, tìm kiếm ngữ nghĩa, tra cứu chính xác, agent tools |
| Repository | K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai Trò Và Phạm Vi Công Việc

Trong bài lab này, mình phụ trách phần RAG và agent. Phần việc của mình nằm sau bước cleaning và trước/đồng hành với evaluation: nhận cleaned dataset, kiểm tra dữ liệu có phù hợp để embedding không, tạo MiniLM embeddings, xây Chroma collections riêng cho baseline/corrupted/repaired, kiểm tra semantic search, exact lookup, và xác minh agent sử dụng tool trước khi trả lời câu hỏi theo dữ kiện.

| Module/deliverable | File/hàm/artifact phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Vector index preflight | `LocalEmbeddingIndex.prepare_config`, `check_vector_index_ready.py` | `data/clean/papers_clean.csv` | Schema check, preview documents, text checks | Hoàn thành |
| MiniLM embeddings | `MiniLMEmbeddings`, `LocalEmbeddingIndex.build` | `text_for_embedding` từ clean CSV | Vector embeddings normalized | Hoàn thành |
| Chroma collections | `data/chroma`, collection names | baseline/corrupted/repaired clean data | `papers-baseline`, `papers-corrupted`, `papers-repaired` | Hoàn thành |
| Embedding manifests | `data/embeddings/*.json` | Chroma build output | Manifest chứa collection name, persist path, documents | Hoàn thành |
| Semantic search | `LocalEmbeddingIndex.search` | query text | top-k `SearchResult` có score/content/metadata | Hoàn thành |
| Exact lookup | `LocalEmbeddingIndex.lookup` | `paper_id` hoặc exact title | document đúng từ local corpus | Hoàn thành |
| Agent tools | `build_agent_tools`, `build_agent` | `LocalEmbeddingIndex` | `semantic_search_papers`, `lookup_paper`, agent object | Hoàn thành |

## 3. Kết Quả Theo Vai Trò

### 3.1 Kiểm tra `text_for_embedding`

mình đã đọc trực tiếp một vài `text_for_embedding` thật từ clean dataset. Các sample baseline đều có title, authors, summary; không rỗng; tỷ lệ token lặp không quá cao.

| Paper ID | Kiểm tra title | Kiểm tra summary | Repeated token ratio | Kết luận |
| --- | --- | --- | ---: | --- |
| `10.1007/s10278-026-02086-9` | Có | Có | 0.3414 | OK |
| `10.1093/sleep/zsag091.0346` | Có | Có | 0.3562 | OK |
| `10.1111/exsy.70341` | Có | Có | 0.2511 | OK |

Ví dụ nội dung đã kiểm:

```text
Title: JADE-Plus: A Multimodal Agentic Retrieval-Augmented Generation Large Language Framework...
Authors: Soroush Baseri Saadi; Jonas Ver Berne; ...
Summary: Abstract Diagnosing jawbone lesions...
```

### 3.2 Xác nhận schema cho vector index

Clean dataframe có đủ các cột cần cho vector index:

```text
paper_id, title, summary, text_for_embedding, published,
authors_joined, categories_joined, abs_url, pdf_url
```

Khi đưa vào Chroma, document được chuẩn hóa theo contract:

| Field trong index | Nguồn từ dataframe | Mục đích |
| --- | --- | --- |
| `record_id` | `paper_id::row_index` | ID duy nhất trong Chroma |
| `paper_id` | `paper_id` | lookup chính xác và ground truth |
| `title` | `title` | lookup theo exact title và hiển thị |
| `content` | `text_for_embedding` | text đưa vào MiniLM để embedding |
| `metadata` | các cột metadata | trả context/source cho agent/evaluator |

Metadata lưu trong Chroma:

```text
paper_id, title, published, authors_joined,
categories_joined, summary, abs_url, pdf_url
```

### 3.3 Config vector index

Config baseline đã chuẩn bị và xác nhận:

| Thuộc tính | Giá trị |
| --- | --- |
| Clean path | `data/clean/papers_clean.csv` |
| Embedding backend | Chroma |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Distance metric | cosine |
| Collection baseline | `papers-baseline` |
| Top-k mặc định | 4 |
| Manifest path | `data/embeddings/papers_embeddings.json` |
| Persist path | `data/chroma` |

## 4. Embedding, Chroma Và Ba Collection Tách Biệt

mình đã tạo MiniLM embeddings và build ba Chroma collections riêng, không ghi đè lẫn nhau:

| Trạng thái | Clean dataset | Manifest | Chroma collection | Số documents |
| --- | --- | --- | --- | ---: |
| Baseline | `data/clean/papers_clean.csv` | `data/embeddings/papers_embeddings.json` | `papers-baseline` | 24 |
| Corrupted | `data/clean/papers_clean_corrupted.csv` | `data/embeddings/papers_embeddings_corrupted.json` | `papers-corrupted` | 25 |
| Repaired | `data/clean/papers_clean_repaired.csv` | `data/embeddings/papers_embeddings_repaired.json` | `papers-repaired` | 24 |

Danh sách collection cuối cùng trong Chroma:

```text
['papers-baseline', 'papers-repaired', 'papers-corrupted']
```

mình cũng xác nhận manifest khớp với clean dataset:

| Trạng thái | Manifest khớp clean dataset | Ghi chú |
| --- | --- | --- |
| Baseline | True | 24 document IDs khớp clean |
| Corrupted | True | 25 documents do có duplicate có chủ đích |
| Repaired | True | 24 document IDs khôi phục như baseline |

## 5. Semantic Search Và Exact Lookup Demo

Query baseline dùng để đối chiếu xuyên suốt:

```text
agentic retrieval augmented generation diagnostic support
```

Kết quả semantic search top-3 trên `papers-baseline`:

| Rank | Paper ID | Score | Title |
| ---: | --- | ---: | --- |
| 1 | `10.32473/flairs.39.1.141782` | 0.5712 | An Exploratory Study of Agentic Retrieval Augmented Generation for Mental Health Oriented Language Models |
| 2 | `10.63646/kpqm1958` | 0.5014 | The Age of Autonomous Agents: A Bibliometric Review of Agentic AI Architectures, Applications, and Emerging Challenges |
| 3 | `10.70121/001c.158711` | 0.4992 | The Role of Retrieval-Augmented Generation in Improving Factual Accuracy for Medical Large Language Models |

Exact lookup demo:

| Lookup input | Kết quả |
| --- | --- |
| `10.32473/flairs.39.1.141782` | Found đúng paper |
| Exact title `An Exploratory Study of Agentic Retrieval Augmented Generation for Mental Health Oriented Language Models` | Found đúng paper |

Kết quả smoke test:

```text
semantic search result_count: 3
exact lookup by_paper_id: True
exact lookup by_exact_title: True
tool output semantic_search_papers_has_top_doc: True
tool output lookup_paper_has_top_doc: True
```

## 6. Agent Và Tool Output

Agent được tạo bằng `build_agent(settings, index)` và có hai tool:

```text
semantic_search_papers
lookup_paper
```

System prompt yêu cầu agent dùng tools trước khi trả lời câu hỏi factual và nói rõ nếu corpus không hỗ trợ câu trả lời. mình tách thêm `build_agent_tools(index)` để kiểm tra trực tiếp tool output mà không cần gọi LLM ra ngoài.

Kết quả kiểm tra:

| Collection | `semantic_search_papers` có trả doc top? | `lookup_paper` có trả đúng doc? | Corpus-bound |
| --- | --- | --- | --- |
| Baseline | True | True | True |
| Repaired | True | True | True |

LLM config hiện tại:

| Biến | Giá trị |
| --- | --- |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-2.5-flash` |
| LLM object | `ChatGoogleGenerativeAI` |

Không ghi API key trong report.

## 7. So Sánh Baseline, Corrupted, Repaired

Với baseline query đã chọn, top-3 retrieval hiện giống nhau ở cả ba collection. Điều này cho thấy corruption trong lần chạy này không làm đổi top-k của query đó, có thể vì các corruption chính không đánh trực tiếp vào những documents top-k của query.

| Collection | Top-1 paper ID | Top-1 score | Nhận xét |
| --- | --- | ---: | --- |
| `papers-baseline` | `10.32473/flairs.39.1.141782` | 0.5712 | Retrieval ổn |
| `papers-corrupted` | `10.32473/flairs.39.1.141782` | 0.5712 | Top-k không đổi với query này |
| `papers-repaired` | `10.32473/flairs.39.1.141782` | 0.5712 | Khôi phục giống baseline |

mình cũng xác nhận sau khi build `papers-corrupted` và `papers-repaired`, `papers-baseline` vẫn đọc được và kết quả baseline query không bị mutate:

```text
baseline_not_mutated_after_other_builds: True
```

## 8. Metrics Và Data Quality Liên Quan

Mặc dù vai trò chính của mình là RAG/index/agent, mình có đối chiếu metrics để hiểu tác động của corrupted data lên agent.

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | 1.0000 | Retrieval vẫn tìm đúng doc theo ground truth |
| `mean_token_f1` | 0.9627 | 0.8406 | 0.9627 | Corruption làm chất lượng answer giảm |
| `judge_accuracy` | 1.0000 | 0.8750 | 1.0000 | Agent/evaluator bị ảnh hưởng bởi dữ liệu xấu |
| `mean_judge_score` | 4.4167 | 4.0000 | 4.4167 | Repair khôi phục về baseline |
| Empty summaries | 0 | 3 | 0 | Corruption tạo summary rỗng |
| Duplicate paper IDs | 0 | 1 | 0 | Corruption thêm duplicate |
| Stale rows | 0 | 1 | 0 | Corruption làm stale publication date |

Corruption log chính:

```text
blank_summary: 2 affected records
inject_noise: 1 affected record
truncate_title: 1 affected record
stale_date: 1 affected record
add_duplicate: 1 duplicate
total_before_corruption: 24
total_after_corruption: 25
```

Chuỗi nguyên nhân - bằng chứng:

1. Blank summary, stale date, duplicate row -> quality signals fail (`empty_summaries=3`, `duplicate_paper_ids=1`, `stale_rows=1`) -> `mean_token_f1` giảm từ 0.9627 xuống 0.8406 và `judge_accuracy` giảm từ 1.0 xuống 0.875.
2. Repair từ dữ liệu sạch -> quality signals phục hồi (`empty_summaries=0`, `duplicate_paper_ids=0`, `stale_rows=0`) -> metrics quay về baseline.

## 9. Quyết Định Kỹ Thuật Quan Trọng

**Bối cảnh:** Cần so sánh baseline, corrupted và repaired mà không làm lẫn artifact.

**Phương án cân nhắc:**

1. Dùng một collection Chroma duy nhất và ghi đè mỗi lần build.
2. Dùng ba collection riêng: `papers-baseline`, `papers-corrupted`, `papers-repaired`.

**Phương án đã chọn:** Dùng ba collection riêng.

**Lý do:** Cách này tái lập tốt hơn, tránh mutate baseline khi build corrupted/repaired, và giúp team demo trực tiếp từng trạng thái. Manifest riêng cũng làm việc audit dễ hơn vì mỗi manifest trỏ đúng collection và document payload của trạng thái tương ứng.

**Bằng chứng:** Chroma hiện có đủ ba collection, manifest khớp clean dataset, và `baseline_not_mutated_after_other_builds=True`.

## 10. Blocker Đã Xử Lý

### Blocker 1: manifest cũ có `persist_path` không khớp workspace

- **Triệu chứng:** `LocalEmbeddingIndex.load()` có thể đọc manifest nhưng không tìm thấy collection nếu `persist_path` trong manifest trỏ sang thư mục cũ.
- **Nguyên nhân gốc:** Repo được pull/chạy ở workspace khác, trong khi manifest lưu absolute path.
- **Cách xử lý:** Cho `LocalEmbeddingIndex.load()` thử path trong manifest trước, nếu không mở được collection thì fallback về `settings.paths.chroma_dir`.
- **Xác minh:** Smoke retrieval load được `papers-baseline` tại workspace hiện tại.

### Blocker 2: corrupted dataset có summary rỗng/duplicate theo thiết kế

- **Triệu chứng:** validation ban đầu quá chặt, chặn build `papers-corrupted` vì có summary rỗng.
- **Nguyên nhân gốc:** Trong corruption phase, summary rỗng và duplicate là dữ liệu lỗi có chủ đích để đo impact.
- **Cách xử lý:** Validation cho vector index chỉ bắt buộc `paper_id`, `title`, `text_for_embedding` không rỗng; `summary` vẫn là metadata và có thể rỗng trong corrupted dataset.
- **Xác minh:** Build thành công `papers-corrupted` với 25 docs, quality report vẫn ghi nhận lỗi dữ liệu.

## 11. Hiểu Biết Về Luồng End-to-End

1. Crossref trả raw response, ingestion parse thành raw records. Cleaning chuẩn hóa title, summary, authors, categories, published date và tạo `text_for_embedding`. RAG module dùng `text_for_embedding` để tạo MiniLM embeddings, lưu vào Chroma và manifest.
2. Evaluation set chứa câu hỏi, ground truth và `ground_truth_doc_ids`. Khi agent/retrieval trả lời, evaluator kiểm tra có retrieve đúng document không và answer có gần ground truth không.
3. Quality checks kiểm tra tình trạng dữ liệu tại một thời điểm như null, duplicate, empty summary. Freshness monitoring tập trung vào tuổi dữ liệu, ví dụ `published`, `age_days`, stale rows.
4. Phải dùng cùng test set cho baseline/corrupted/repaired để so sánh công bằng. Nếu test set thay đổi, metric thay đổi có thể do câu hỏi khác chứ không phải do data corruption/repair.
5. Repair thành công khi repaired dataset/manifest/collection khôi phục gần baseline và metrics/quality signals quay lại trạng thái tốt. Trong lần chạy này, repaired metrics quay về đúng baseline.

## 12. Lệnh Tái Hiện

Kiểm tra clean data và vector config:

```powershell
uv run python script\check_vector_index_ready.py
```

Build và kiểm tra toàn bộ phần Vai trò 3:

```powershell
uv run python script\run_role3_rag_checks.py
```

Smoke test từng collection:

```powershell
uv run python script\smoke_retrieval_agent.py --embeddings-path data\embeddings\papers_embeddings.json
uv run python script\smoke_retrieval_agent.py --embeddings-path data\embeddings\papers_embeddings_corrupted.json
uv run python script\smoke_retrieval_agent.py --embeddings-path data\embeddings\papers_embeddings_repaired.json
```

Live agent test nếu được phép gọi provider:

```powershell
uv run python script\smoke_retrieval_agent.py --agent
```

## 13. Điều Học Được Và Hướng Cải Thiện

### Ba điều quan trọng nhất

1. RAG quality phụ thuộc mạnh vào contract của clean data. Nếu `text_for_embedding` thiếu title/summary hoặc metadata không đầy đủ, retrieval và answer đều khó audit.
2. Vector store cần tách collection theo trạng thái dữ liệu. Nếu ghi đè collection baseline, việc so sánh corrupted/repaired sẽ không còn đáng tin.
3. Agent nên bị ràng buộc bằng tools và corpus. Việc kiểm tra tool output trực tiếp giúp xác minh agent có nguồn dữ liệu đúng trước khi gọi LLM.

### Nếu có thêm thời gian

mình sẽ chọn thêm một baseline query nhắm trực tiếp vào các record bị corruption, ví dụ các paper bị blank summary/truncate title, để quan sát top-k đổi rõ hơn. Query hiện tại ổn để smoke test nhưng chưa nhạy với corruption vì top-k không thay đổi giữa ba trạng thái.

## 14. Cam Kết Cá Nhân

- [x] Báo cáo phản ánh đúng phần việc Vai trò 3 mình phụ trách.
- [x] Các kết luận có artifact hoặc lệnh kiểm chứng.
- [x] Không ghi API key, token hoặc nội dung `.env` vào báo cáo.
- [x] mình có thể giải thích luồng clean data -> MiniLM -> Chroma -> semantic search/exact lookup -> agent tools.
- [x] mình không ghi thành công cho phần live LLM agent invoke vì phần đó cần quyền gọi provider bên ngoài.

**Họ và tên:** [Diêm Công Thành]  
**Ngày xác nhận:** 2026-08-06
