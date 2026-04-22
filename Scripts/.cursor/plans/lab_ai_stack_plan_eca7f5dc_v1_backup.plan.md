---
name: Lab AI Stack Plan
overview: "A Docker-first reference architecture for an R&D lab assistant: Streamlit UI, Flowise + LM Studio for agents/chat orchestration, DuckDB for tabular OLAP, Chroma for vectors, and a pragmatic RAG path that stays maintainable for a small team."
todos:
  - id: compose-skeleton
    content: Add Docker Compose with Streamlit, Flowise, Chroma, persisted volumes; document LM Studio host URL for Windows
    status: pending
  - id: contracts
    content: Define HTTP/API contract between Streamlit and Flowise; env var strategy for secrets
    status: pending
  - id: duckdb-schema
    content: Design DuckDB registry + curated views for lab tables; mount paths for raw vs warehouse
    status: pending
  - id: ingest-pipeline
    content: Implement Python ingest (chunk, hash, metadata) → Chroma + DuckDB index; pluggable EmbeddingClient (Gemini first)
    status: pending
  - id: flowise-flows
    content: "Build Flowise flows: RAG retrieval + optional SQL tool over DuckDB; export/version flow JSON"
    status: pending
  - id: eval-golden-set
    content: Create small golden Q/A set to validate gemini-embedding-001 retrieval quality vs baseline
    status: pending
isProject: false
---

# Lab manager: Streamlit, Flowise, DuckDB, Chroma, Docker

## Where you are today

Your repo `[d:\Vanessa\AI_project\Lab_manager\Scripts\](d:\Vanessa\AI_project\Lab_manager\Scripts\)` is effectively greenfield (minimal `[README.txt](d:\Vanessa\AI_project\Lab_manager\Scripts\README.txt)`). The plan below is stack-level guidance you can implement incrementally and later move under GitHub with `docker-compose` and clear env/config separation.

## Target architecture (logical)

```mermaid
on
Data_plane
flowchart LR
  subgraph ui [UI]
    Streamlit[Streamlit]
  end
  subgraph orchestration [Orchestration]
    Flowise[Flowise]
    LMStudio[LMStudio_host]
  end
  subgraph data [Data_plane]
    DuckDB[DuckDB_files]
    Chroma[ChromaDB]
  end
  subgraph ingest [Ingestion_RAG]
    ETL[ETL_and_chunkers]
    EmbAPI[Gemini_embeddings_API]
  end
  Streamlit -->|HTTP_SSE| Flowise
  Flowise -->|OpenAI_compat_chat| LMStudio
  Streamlit -->|optional_direct_SQL| DuckDB
  ETL --> DuckDB
  ETL --> EmbAPI
  ETL --> Chroma
  Flowise -->|vector_retrieval| Chroma
  Flowise -->|SQL_or_tool| DuckDB
```



**Roles**

- **Streamlit**: Primary UX for chat, tables, charts, and “export report” (PDF/HTML/Markdown). Keep heavy orchestration out of Streamlit when possible; treat it as a thin client calling your orchestration and data APIs.
- **Flowise**: Visual multi-step / multi-tool flows (RAG + SQL agent patterns). Good for iterating prompts and wiring tools without redeploying the whole app for every tweak.
- **LM Studio (host)**: Local chat/completions via OpenAI-compatible base URL. Common pattern: run LM Studio on the GPU machine; containers reach it via `host.docker.internal` (Windows) or a published port.
- **DuckDB**: Analytical queries over CSV/Parquet/lab exports; optional `duckdb-extensions` for Excel if needed. File-backed DBs on mounted volumes work well in Docker.
- **Chroma**: Vector store for document chunks; persist with a Docker volume.

## Important design caveat: “local LLM” vs “Gemini embeddings”

- **LM Studio** keeps **generation** on-box (good for confidentiality and latency for chat).
- `**gemini-embedding-001`** is a **Google API** embedding model: chunk text leaves your network unless you later switch to a local embedding model in LM Studio / another runtime.

For R&D data, decide explicitly: *embedding via cloud is acceptable for the pilot* vs *air-gapped requirement*. If you need full on-prem later, plan a swap interface (`EmbeddingClient`) so you can replace Gemini with a local model without rewriting retrieval.

## RAG: beginner-friendly options that fit this stack

**Option A — RAG mostly inside Flowise (fastest to a demo)**  
Use Flowise document loaders, text splitters, Chroma vector store nodes, and a conversational agent. **Pros**: minimal Python glue, fast iteration. **Cons**: harder to unit test, versioning of ingest logic is manual, less control over lineage.

**Option B — Python ingestion pipeline + Flowise for query-time only (recommended for “lab records” seriousness)**  
Implement ingestion as a small Python package in this repo (scheduled or on-demand):

1. **Extract**: `unstructured` (PDFs/Office), `pandas`/`polars` (tables), optional `pypdf` for simple PDFs.
2. **Normalize metadata**: project, assay, date, instrument, SOP version → store in **DuckDB** as a *document registry / chunk index* (source path, checksum, chunk ids, permissions).
3. **Chunk + embed**: call Gemini embedding API; upsert vectors to **Chroma** with the same `chunk_id` you store in DuckDB.
4. **Query**: Flowise retrieves from Chroma and optionally runs **DuckDB SQL** (tool use) for quantitative questions.

**Libraries that keep the learning curve manageable**

- **LlamaIndex** (Python): strong “data framework” mental model (connectors, indices, query engines); plays well with DuckDB and Chroma; good docs for RAG newcomers.
- **LangChain**: ubiquitous; more pieces and moving targets, still viable if you already know it.

For a starter team, **Option B + LlamaIndex** is usually the sweet spot: Flowise stays the agent UI, Python stays the reliable ingestion/lineage layer.

## Multi-agent “platform” expectations

Flowise supports agent/tool patterns visually, but it is not a full “agent ops platform.” If you outgrow it, you can migrate orchestration to **LangGraph / custom FastAPI** while keeping DuckDB + Chroma + the same schemas.

Practical seam: expose **one HTTP contract** from Streamlit (e.g., `POST /lab/ask`) that internally calls Flowise’s prediction API today and can be swapped later.

## Analytics (OLAP) patterns with DuckDB

- Land raw files in a volume (`/data/raw/...`), build curated Parquet (or DuckDB tables) in `/data/warehouse/`.
- Put **business logic in SQL views** (assay rollups, QC thresholds) so both Streamlit charts and the LLM “SQL tool” hit the same definitions.
- For “show me a table in Streamlit,” prefer parameterized SQL (never paste unconstrained LLM SQL into production without guardrails). A safe pattern is: LLM proposes filters → your code maps them to **pre-approved queries** or **parameterized templates**.

## Docker layout (suggested)

- `**docker-compose.yml`** services: `streamlit`, `flowise`, `chroma`, optional `minio` (if you want S3-compatible object storage for blobs), optional `postgres` (Flowise persistence if you outgrow defaults).
- **LM Studio**: typically **not** containerized; document `EXTRA_HOSTS` / Windows host access clearly.
- **Volumes**: `data_duckdb`, `data_chroma`, `data_raw`, `flowise_data`.
- **Secrets**: `.env` (not committed) for `GOOGLE_API_KEY`, Flowise secrets, and any DB paths.

## Repository structure (when you implement)

Keep concerns separated even in a monorepo:

- `apps/streamlit/` — UI
- `apps/flowise/` — exported flows JSON (optional) + notes
- `packages/ingest/` — RAG + ETL pipeline
- `infra/docker/` — compose + Dockerfiles

## Evaluation plan for `gemini-embedding-001`

Before scaling ingestion:

- Build a **small golden set** (20–50 representative chunks: protocols, instrument logs, messy tables-as-text).
- Measure **recall@k** on known questions and **contamination** (retrieved chunks from wrong project).
- Compare against one local embedding baseline (even a small model) to quantify privacy vs quality trade-offs.

## Suggestions for a “seamless” system (high leverage)

- **Single metadata schema** linking `doc_id`, `chunk_id`, `source_uri`, `hash`, `created_at`, `acl_tags` in DuckDB; mirror `chunk_id` in Chroma payloads.
- **Idempotent ingestion** (re-run safe): upsert by content hash, delete stale chunks.
- **Tracing**: enable basic request/flow logging (Flowise + your ingest jobs) so debugging “wrong answer” is feasible.
- **Access control**: if multiple lab groups share one deployment, enforce ACL in retrieval (filter Chroma metadata / DuckDB `WHERE`)—do not rely on the LLM to refuse silently.

## What this plan intentionally does not prescribe yet

Exact Flowise node graph, table schemas, and report templates depend on your document types and compliance constraints; those should be derived once you list primary file formats (PDF only vs Excel-heavy vs instrument exports).