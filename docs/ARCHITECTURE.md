# Literature Intelligence Platform — System Architecture

## 1. Architectural Philosophy & Design Constraints

The **Literature Intelligence Platform** is a local-first, privacy-preserving research intelligence SaaS engineered specifically for edge execution on memory-constrained hardware (e.g., **Windows 11, 8 GB RAM, CPU-only**).

Scientific literature workflows are notoriously resource-intensive: processing 100-page academic monographs, generating 768-dimensional dense vector embeddings, maintaining vector indexes, and running LLM inference routinely exhaust host memory. To guarantee stability and zero memory thrashing without cloud telemetry or dedicated GPUs, the system enforces five foundational architectural principles:

1. **Strict 8 GB RAM Enveloping:** The entire runtime footprint (OS + Ollama + Python Backend + ChromaDB + React Frontend) is partitioned with a minimum 1.5 GB memory safety buffer.
2. **Sequential Multi-Agent Execution:** Asynchronous concurrent execution of multiple LLM agents causes memory spikes. Agents execute sequentially with structured state handover and intermediate SQLite/JSON checkpointing.
3. **Local-First & Air-Gapped Privacy:** Zero paper data, abstracts, or analysis queries leave the local host. Ingestion, vectorization, and generation occur entirely on the user's machine.
4. **Verifiable Page-Level Provenance:** Every extracted finding, limitation, and claim must be tied to a 1-indexed PDF page citation and exact verbatim source quote.
5. **Non-Blocking Resilient Fallbacks:** High-frequency socket health probes detect offline inference servers in < 5 ms, falling back to deterministic local heuristic synthesis rather than failing or timing out for 60 seconds.

---

## 2. Global System Architecture

```mermaid
flowchart TD
    subgraph Client["Presentation Layer (React 18 + Vite + Tailwind CSS)"]
        UI_Dash["Overview Dashboard"]
        UI_Lib["PDF Library & Ingestion"]
        UI_Disc["Research Discovery"]
        UI_Analysis["14-Dim Paper Analysis"]
        UI_Comp["Cross-Paper Comparison"]
        UI_Graph["Interactive Knowledge Graph (D3/Canvas)"]
        UI_Gaps["Research Gap Matrix"]
        UI_Contra["Contradiction Detection"]
        UI_Verif["Evidence Verification"]
        UI_Reports["Multi-Format Report Generator"]
        UI_Settings["Diagnostics & System Health"]
    end

    subgraph API_Gateway["FastAPI Gateway (Port 8000)"]
        Router_Projects["/api/projects"]
        Router_Docs["/api/documents"]
        Router_RAG["/api/rag"]
        Router_Analysis["/api/analysis"]
        Router_Comp["/api/comparison"]
        Router_Graph["/api/graph"]
        Router_Gaps["/api/gaps"]
        Router_Contra["/api/contradictions"]
        Router_Trends["/api/trends"]
        Router_Verif["/api/verification"]
        Router_Reports["/api/reports"]
        Router_System["/api/system"]
        Router_Orch["/api/orchestrator"]
    end

    subgraph Agent_Core["Multi-Agent Orchestrator (Sequential Pipeline)"]
        A1["1. Research Discovery Agent"]
        A2["2. PDF Understanding Agent"]
        A3["3. Semantic Retrieval Agent"]
        A4["4. Research Analysis Agent"]
        A5["5. Cross-Paper Comparison Agent"]
        A6["6. Knowledge Graph Agent"]
        A7["7. Research Gap Discovery Agent"]
        A8["8. Evidence Verification Agent"]
        A9["9. Contradiction Detection Agent"]
        A10["10. Research Trend Analysis Agent"]
    end

    subgraph Storage["Storage & Persistence Layer"]
        SQL[(SQLite Persistent Database\nWAL Mode - 11 Entities)]
        VEC[(ChromaDB Vector Store\nCosine HNSW - 768-dim)]
        PDF_Store["Local File Store\nbackend/data/PDFs/"]
    end

    subgraph Local_Inference["Local Inference Engine (Ollama / Local Fallback)"]
        OLLAMA_LLM["LLM Engine: qwen3:1.7b / qwen2.5:1.5b (Q4_K_M)"]
        OLLAMA_EMB["Embedding Engine: nomic-embed-text (768-dim)"]
        FALLBACK_VEC["Deterministic L2-Normalized Fallback Embedder"]
    end

    Client -->|REST & SSE (HTTP)| API_Gateway
    API_Gateway --> Agent_Core
    Agent_Core --> Storage
    Agent_Core --> Local_Inference
```

---

## 3. Hardware Resource Budget (8 GB RAM Allocation)

| Component | Target Allocator | Typical Footprint | Architectural Optimization Strategy |
|:---|:---|:---|:---|
| **OS & Background Apps** | Windows 11 (64-bit) | ~3,200 – 3,800 MB | Baseline reserved |
| **Local LLM Engine** | Ollama (`qwen3:1.7b`) | ~1,200 – 1,600 MB | 4-bit quantization (Q4_K_M); serialized prompt processing |
| **Embedding Model** | Ollama (`nomic-embed-text`) | ~280 – 450 MB | Runs in Ollama daemon; avoids loading PyTorch in Python |
| **Python / FastAPI Runtime** | Backend process | ~120 – 180 MB | Lazy module imports, garbage collection after PDF ingestion |
| **ChromaDB Vector Store** | Persistent client | ~150 – 300 MB | Batch inserts (capped at 64), Cosine distance HNSW |
| **SQLite Relational DB** | SQLite WAL mode | ~20 – 40 MB | Write-Ahead Logging, indexed queries, zero in-memory caching |
| **Frontend Dev Server** | Vite + React + Node.js | ~120 – 200 MB | Native ES modules, fast HMR, asset pre-bundling |
| **System Headroom Buffer** | OS Memory Reserve | ~1,500 – 2,000 MB | Strict safety cushion preventing paging file thrashing |

---

## 4. Multi-Agent Pipeline Data Flow

The central multi-agent orchestrator executes stages sequentially to respect memory limits. The data flow from raw PDF upload to final academic synthesis follows this state progression:

```
[PDF Upload / Topic Input]
           │
           ▼
[1. Research Discovery Agent]
  ├── Query arXiv / OpenAlex / Semantic Scholar
  └── Register paper metadata in SQLite
           │
           ▼
[2. PDF Understanding Agent]
  ├── High-speed text & table extraction via PyMuPDF
  ├── Structure into sections (Abstract, Intro, Methods, Results, Discussion)
  ├── 512-token chunking with 64-token overlap
  └── ChromaDB indexing with 768-dim vectors
           │
           ▼
[3. Semantic Retrieval Agent]
  ├── Dense cosine similarity top-k search
  └── Extract relevant passages with 1-indexed page citations
           │
           ▼
[4. Research Analysis Agent]
  └── Extract 14 structured dimensions with supporting excerpts
           │
           ▼
[5. Cross-Paper Comparison Agent]
  └── Synthesize 13-criteria comparative matrix across 2–5 papers
           │
           ▼
[6. Knowledge Graph Agent]
  └── Extract entities (Papers, Authors, Algorithms, Datasets, Topics) & relationships
           │
           ▼
[7. Research Gap Discovery Agent]
  ├── Detect explicit author limitations
  └── Infer implicit cross-paper methodological/dataset gaps with confidence scoring
           │
           ▼
[8. Evidence Verification Agent]
  └── Verify factual claims: Supported, Partially Supported, Contradicted, Insufficient Evidence
           │
           ▼
[9. Final Research Report Generator]
  └── Compile literature review, comparative tables, and references (IEEE / APA) -> MD / PDF / DOCX
```

---

## 5. Storage Layer Architecture

### 5.1 SQLite Relational Store (`backend/data/literature.db`)
Configured in Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) with `synchronous=NORMAL` to allow non-blocking concurrent reads while agent stages commit structured findings.

Tables include:
- `research_projects`: Project metadata, research topic, and status.
- `research_papers`: Paper titles, authors, abstract, publication year, file path.
- `paper_sections`: Chunked passages, section headers, 1-indexed page numbers.
- `paper_analyses`: 14-dimension structured analysis JSON.
- `paper_comparisons`: Multi-paper comparison matrices and narratives.
- `research_gaps`: Identified gaps, heuristic confidence scores, and counter-evidence.
- `gap_evidences`: Verbatim supporting excerpts tied to page numbers.
- `research_contradictions`: Conflicting findings, divergent conclusions, and root-cause analysis.
- `verification_results`: Claim verification statuses and evidence sentences.
- `generated_reports`: Markdown content, report types, and citation formats.
- `agent_execution_histories`: Audit log of agent execution durations, inputs, outputs, and statuses.

### 5.2 ChromaDB Vector Store (`backend/data/chromadb/`)
- **Collection Name:** `literature_chunks`
- **Metric:** Cosine distance (`hnsw:space: cosine`)
- **Metadata Fields:** `paper_id`, `project_id`, `page_number`, `section_title`, `chunk_index`
- **Embedding Dimensions:** 768 float values.

---

## 6. Fault Tolerance & Non-Blocking Design

- **Ollama Probe:** A 150 ms TCP port probe (`socket.create_connection`) checks if Ollama is running. If offline, the platform seamlessly activates grounded heuristic fallback synthesis and deterministic L2-normalized 768-dim embeddings without hanging.
- **State Checkpointing:** Every workflow stage persists intermediate state to `backend/data/workflows/{workflow_id}.json`. If interrupted, workflows resume from the last completed stage without redundant re-processing.
- **Streaming Responses:** Real-time synthesis streams tokens to the frontend via Server-Sent Events (SSE) with keep-alive heartbeats, ensuring no browser timeout during long generation runs.
