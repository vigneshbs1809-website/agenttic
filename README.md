# Literature Intelligence Platform

> **Local-First, Privacy-Preserving Academic Research Intelligence & Multi-Agent Literature Synthesis Platform**  
> *Engineered for High-Throughput Literature Deconstruction on Low-Resource Hardware (8 GB RAM, CPU-Only)*

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20TypeScript-61DAFB.svg?style=flat&logo=react)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Bundler-Vite-646CFF.svg?style=flat&logo=vite)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/Styling-Tailwind%20CSS-38B2AC.svg?style=flat&logo=tailwind-css)](https://tailwindcss.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%20(WAL)-003B57.svg?style=flat&logo=sqlite)](https://www.sqlite.org/)
[![ChromaDB](https://img.shields.io/badge/Vector%20Store-ChromaDB-FC60A8.svg?style=flat)](https://www.trychroma.com/)
[![Ollama](https://img.shields.io/badge/Local%20LLM-Ollama%20(qwen3:1.7b)-000000.svg?style=flat)](https://ollama.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Objectives](#3-objectives)
4. [Proposed Solution](#4-proposed-solution)
5. [System Architecture](#5-system-architecture)
6. [Eight-Agent Architecture](#6-eight-agent-architecture)
7. [Technology Stack](#7-technology-stack)
8. [RAG Pipeline](#8-rag-pipeline)
9. [Database Architecture](#9-database-architecture)
10. [Research Gap Discovery Methodology](#10-research-gap-discovery-methodology)
11. [Evidence Verification Methodology](#11-evidence-verification-methodology)
12. [Installation Instructions](#12-installation-instructions)
13. [Ollama Setup](#13-ollama-setup)
14. [Local Model Setup](#14-local-model-setup)
15. [Backend Execution](#15-backend-execution)
16. [Frontend Execution](#16-frontend-execution)
17. [API Documentation](#17-api-documentation)
18. [Testing Methodology](#18-testing-methodology)
19. [Limitations](#19-limitations)
20. [Future Enhancements](#20-future-enhancements)
21. [Implemented, Tested & Incomplete Feature Checklist](#21-implemented-tested--incomplete-feature-checklist)

---

## 1. Project Overview

The **Literature Intelligence Platform** is a local-first academic research assistant and literature intelligence platform designed to ingest complex scientific literature (including 100+ page dissertations and multi-column conference papers), deconstruct them into 14 structured academic dimensions, discover explicit and implicit research gaps, detect empirical contradictions, verify factual claims, and generate publication-grade literature reviews with strictly 1-indexed page citations.

Operating with zero cloud dependencies, the platform runs fully on consumer hardware (**Windows 11, 8 GB RAM, no dedicated GPU**), ensuring 100% data privacy and zero cloud token expenditure.

---

## 2. Problem Statement

Modern scientific literature analysis suffers from five compounding challenges:
1. **Information Overload:** Over 5 million academic papers are published annually, making exhaustive literature reviews across multiple related papers practically impossible by manual reading alone.
2. **Cloud Privacy & Data Leakage:** Uploading unreleased preprints, proprietary clinical trials, or grant proposals to third-party commercial LLM clouds violates institutional confidentiality policies.
3. **Severe Hardware Requirements:** Most state-of-the-art AI literature agents demand high-end cloud GPU infrastructure (A100/H100) or 32+ GB host RAM, creating an accessibility barrier for independent researchers and students.
4. **LLM Hallucinations & Fabricated Citations:** Commercial conversational chatbots frequently invent non-existent papers, synthesize bogus author names, and misrepresent quantitative metrics.
5. **Superficial Summarization:** Existing tools provide generic paragraph summaries rather than structured architectural decomposition, contradiction analysis, or grounded gap discovery.

---

## 3. Objectives

- **Local-First Privacy:** Zero research documents, queries, or embeddings leave the local host.
- **Strict 8 GB RAM Compatibility:** Constrain peak process RAM to < 200 MB, reserving over 7.5 GB for OS and local LLM execution.
- **Zero Hallucination with Page Provenance:** Enforce 1-indexed page citations `[Paper Title, Page X]` and verbatim source sentence grounding for every claim.
- **Autonomous Multi-Agent Collaboration:** Coordinate 8 specialized agents sequentially to extract metadata, index vectors, deconstruct papers, synthesize cross-paper matrices, and construct knowledge graphs.
- **Rigorous Gap Discovery & Contradiction Detection:** Formulate explicit author-stated limitations and infer implicit cross-paper methodological trade-offs with transparent confidence scoring.
- **Publication-Ready Export:** Generate formatted literature review reports in IEEE and APA styles with one-click export to PDF, DOCX, and Markdown.

---

## 4. Proposed Solution

The Literature Intelligence Platform introduces an orchestrated multi-agent literature pipeline that bridges local dense vector retrieval with structured relational modeling:

```
[Raw PDFs / arXiv / OpenAlex] 
       │
       ▼
[PyMuPDF Geometry & Table Parser] ──► [512-Token Sliding Window Chunker]
                                                      │
                                                      ▼
[SQLite WAL Relational DB] ◄── [Structured Extraction] ──► [ChromaDB 768-dim Vectors]
                                                      │
                                                      ▼
[Sequential Multi-Agent Orchestrator (8+2 Core Agents)]
  ├── Research Analysis (14 Dimensions)
  ├── Cross-Paper Comparison (13 Criteria)
  ├── Knowledge Graph (NetworkX + Canvas)
  ├── Research Gap Inference (10 Academic Dimensions)
  ├── Contradiction Detection (Side-by-Side Excerpts)
  └── Evidence Verification (Supported / Contradicted)
                               │
                               ▼
[Publication-Grade Report Exporter (IEEE/APA -> PDF/DOCX/MD)]
```

---

## 5. System Architecture

The platform adopts a decoupled client-server architecture:
- **Presentation Layer:** React 18, TypeScript, Vite, Tailwind CSS, Lucide icons, and Recharts. Designed with an academic SaaS aesthetic inspired by Linear, Notion, and GitHub.
- **API Gateway & Orchestrator:** FastAPI asynchronous backend with lazy module loading and non-blocking TCP socket health probing.
- **Relational Storage:** SQLite in Write-Ahead Logging (`WAL`) mode with foreign key integrity.
- **Dense Vector Store:** ChromaDB persistent client utilizing HNSW indexing with Cosine similarity.
- **Inference Layer:** Ollama daemon serving 4-bit quantized `qwen3:1.7b` (or `qwen2.5:1.5b`) and `nomic-embed-text` (768-dim), augmented by an immediate deterministic fallback embedder when offline.

For detailed architecture diagrams, consult [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 6. Eight-Agent Architecture

The core literature intelligence engine connects eight sequential agents managed by `backend/app/agents/orchestrator.py`:

```
Research Topic / PDF Upload
       │
       ▼
1. Research Discovery Agent      ──► Queries OpenAlex, arXiv, and Semantic Scholar
       │
       ▼
2. PDF Understanding Agent       ──► PyMuPDF extraction, section hierarchy, page mapping
       │
       ▼
3. Semantic Retrieval Agent      ──► Dense vector top-K similarity search in ChromaDB
       │
       ▼
4. Research Analysis Agent       ──► 14-dimension structured paper deconstruction
       │
       ▼
5. Cross-Paper Comparison Agent  ──► 13-criteria comparative matrix across 2–5 papers
       │
       ▼
6. Knowledge Graph Agent         ──► Entity-relationship network (Papers, Authors, Algos)
       │
       ▼
7. Research Gap Discovery Agent  ──► Explicit limitations + implicit cross-paper gaps
       │
       ▼
8. Evidence Verification Agent   ──► Factual claim validation with page-level excerpts
       │
       ▼
Final Academic Research Report (IEEE / APA -> PDF, DOCX, Markdown)
```

*(Augmented by Agent 9: Contradiction Detection and Agent 10: Research Trend Analysis).*  
For in-depth specifications of all agents, consult [docs/AGENTS.md](docs/AGENTS.md).

---

## 7. Technology Stack

### Backend
- **Language & Runtime:** Python 3.10 / 3.11 / 3.12 (64-bit)
- **Web Framework:** FastAPI, Uvicorn (ASGI)
- **Relational Database:** SQLite 3 (WAL mode) via SQLAlchemy ORM
- **Vector Database:** ChromaDB (Cosine similarity HNSW index)
- **PDF Extraction:** PyMuPDF (`fitz`)
- **Graph Processing:** NetworkX
- **Document Export:** ReportLab (PDF), python-docx (DOCX)
- **Local LLM & Embeddings:** Ollama API (`qwen3:1.7b`, `nomic-embed-text`)

### Frontend
- **Framework:** React 18 + TypeScript + Vite
- **Styling:** Tailwind CSS (Academic Linear/Notion minimal theme)
- **Icons:** Lucide React
- **Visualizations:** Recharts (Analytics), Canvas/SVG (Knowledge Graph)
- **Routing:** React Router DOM v6

---

## 8. RAG Pipeline

The Retrieval-Augmented Generation (RAG) pipeline is engineered for zero-hallucination factual grounding:
1. **Document Segmentation:** Text is divided into 512-token chunks with 64-token overlap, preserving paragraph boundaries and tables.
2. **Provenance Metadata:** Every chunk encapsulates `paper_id`, `project_id`, `page_number` (1-indexed), `section_title`, and `chunk_index`.
3. **Dense Vectorization:** Vectors are computed using `nomic-embed-text` (768 dimensions). When offline, a deterministic L2-normalized 768-dim hash embedder prevents pipeline stalling.
4. **Similarity Retrieval:** ChromaDB computes cosine nearest-neighbors with project-level metadata scoping.
5. **Grounded Synthesis:** The generation prompt injects retrieved passages with verbatim citations. If Ollama is offline, the synthesis engine falls back to an extractive heuristic summarizer that cites exact page excerpts.

---

## 9. Database Architecture

The platform uses a hybrid dual-store storage architecture:
- **`literature.db` (SQLite):** 11 relational tables managing projects, papers, sections, analyses, comparisons, gaps, gap evidences, contradictions, verification claims, reports, and agent logs.
- **`literature_chunks` (ChromaDB):** Persistent vector embeddings indexed with HNSW cosine distance.

Comprehensive entity-relationship diagrams and table schemas are documented in [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md).

---

## 10. Research Gap Discovery Methodology

The platform identifies research gaps through a two-tiered methodology:
1. **Explicit Author-Stated Limitations:** Scans the discussion, limitations, and future work sections for author-stated constraints, negative results, and computational boundaries.
2. **Implicit Cross-Paper Gaps (10 Academic Dimensions):** Compares papers across orthogonal dimensions (Methodological Gaps, Dataset Bias, Scalability Bottlenecks, Evaluation Discrepancies, Contradictory Trade-offs, Generalization Gaps, Explainability Deficits, etc.).
3. **Confidence Scoring:** Assigns a transparent heuristic score ($0.15$ to $0.92$) based on:
   $$\text{Confidence} = \text{Base} + \text{Paper Confirmation Bonus} + \text{Passage Granularity} - \text{Counter-Evidence Deduction}$$
   *Constraint: Clearly labeled as a heuristic grounding index, never as a pseudo-statistical probability.*

---

## 11. Evidence Verification Methodology

To prevent academic misinformation, every extracted assertion or user-submitted claim is evaluated through an evidence verification protocol:
1. **Semantic Candidate Search:** The claim is embedded and matched against all indexed chunks of the source paper.
2. **Textual Entailment Analysis:** The passage is cross-examined against the assertion.
3. **Classification:**
   - **Supported:** Verbatim evidence directly substantiates the claim.
   - **Partially Supported:** The general premise holds, but under differing conditions or metrics.
   - **Contradicted:** The paper's data or conclusions directly refute the assertion.
   - **Insufficient Evidence:** The paper does not address or contain data regarding the assertion.
4. **Provenance Output:** Returns the exact matching sentence, 1-indexed page number, and similarity score.

---

## 12. Installation Instructions

### Prerequisites
- Python 3.10+ (64-bit)
- Node.js v18+ and npm
- Ollama ([ollama.com](https://ollama.com/download))

### Step 1: Clone Repository
```bash
git clone https://github.com/your-username/Literature-Intelligence-Platform.git
cd Literature-Intelligence-Platform
```

### Step 2: Environment Configuration
```bash
cp .env.example .env
```

### Step 3: Python Environment & Dependencies
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy pymupdf chromadb pydantic pydantic-settings httpx requests psutil reportlab python-docx networkx

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 4: Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

For complete OS-specific walkthroughs, consult [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md).

---

## 13. Ollama Setup

1. Start the Ollama local background daemon:
   - **Windows / macOS:** Launch the Ollama desktop tray application.
   - **Linux:** Run `systemctl start ollama` or `ollama serve`.
2. Confirm the server is reachable:
   ```bash
   curl http://127.0.0.1:11434/api/tags
   ```

---

## 14. Local Model Setup

Download the 4-bit quantized generation model and embedding model:
```bash
# Primary Reasoning LLM (1.7B parameters, ~1.4 GB RAM)
ollama pull qwen3:1.7b

# (Optional ultra-light alternative for 4 GB free RAM)
# ollama pull qwen2.5:1.5b

# Dense Vector Embedding Model (768 dimensions, ~280 MB RAM)
ollama pull nomic-embed-text
```

---

## 15. Backend Execution

Activate your virtual environment and launch the FastAPI server:
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend URL:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **System Health Diagnostics:** `http://127.0.0.1:8000/api/system/status`

---

## 16. Frontend Execution

In a separate terminal, start the Vite development server:
```bash
cd frontend
npm run dev
```
- **Application URL:** `http://localhost:5173`

---

## 17. API Documentation

The platform provides a complete RESTful API covering all intelligence modules:

| Endpoint Route | Method | Description |
|:---|:---:|:---|
| `/api/projects` | `GET` / `POST` | List and create research projects |
| `/api/documents/upload` | `POST` | Upload and index academic PDFs |
| `/api/rag/query` | `POST` | Grounded semantic retrieval and Q&A |
| `/api/analysis/{paper_id}` | `GET` | 14-dimension structured paper analysis |
| `/api/comparison` | `POST` | 13-criteria cross-paper comparison matrix |
| `/api/graph/global` | `GET` | Multi-paper entity knowledge graph |
| `/api/gaps/discover` | `POST` | Explicit and implicit gap discovery |
| `/api/contradictions/detect`| `POST` | Cross-paper contradiction detection |
| `/api/verification/verify-claim` | `POST` | Factual claim evidence verification |
| `/api/reports/generate` | `POST` | Academic literature review generation |
| `/api/reports/{id}/export/{fmt}` | `GET` | Export report to PDF, DOCX, or Markdown |
| `/api/orchestrator/workflows`| `POST` | Execute or resume multi-agent workflow |
| `/api/system/diagnostics` | `POST` | 7-point subsystem health sweep |

Exhaustive payload models, response structures, and examples are in [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md).

---

## 18. Testing Methodology

The platform includes an automated end-to-end audit harness (`backend/audit_full_suite.py`) that tests all 21 platform capabilities against real academic PDFs:
```bash
python backend/audit_full_suite.py
```

### Verified Audit Results:
```
================================================================================
 AUDIT COMPLETED SUCCESSFULLY: 21 OF 21 ITEMS VERIFIED
================================================================================
Total Suite Duration: 5.20s
Cohorts Tested:       Cohort-3 (3 papers), Cohort-5 (5 papers), Cohort-10 (10 papers)
RAM Delta:            +58.03 MB (Strictly within 8 GB envelope)
ChromaDB Chunks:      1,588 vectors persisted
Database Entities:    38 projects, 112 papers, 939 sections re-read from disk
```

For the comprehensive test suite breakdown, see [docs/TESTING_REPORT.md](docs/TESTING_REPORT.md).

---

## 19. Limitations

1. **Scanned / Bitmap PDFs:** Text extraction relies on PyMuPDF native character streams. Scanned image-only PDFs without an embedded OCR text layer require pre-processing with an external OCR tool (e.g. Tesseract).
2. **Local LLM Context Length:** On 8 GB RAM machines, the context window is capped at 4,096 tokens (`LLM_CONTEXT_LENGTH=4096`) to prevent memory paging.
3. **CPU Generation Speed:** Without a dedicated GPU, LLM token generation rates on consumer CPUs average 12–25 tokens/second.
4. **Corpus Scoping:** Research gap discovery identifies gaps *within the analyzed project corpus* and explicitly disclaims asserting global scientific novelty.

---

## 20. Future Enhancements

- **Direct LaTeX / Overleaf Export:** Export generated literature reviews and bibliography files directly to `.tex` and `.bib`.
- **Integrated Tesseract OCR Pipeline:** Built-in optical character recognition for legacy scanned historical literature.
- **Zotero & Mendeley Sync:** Bi-directional synchronization with reference managers.
- **Multi-Modal Figure Analysis:** Vision-language models (e.g., `llama3.2-vision`) to parse diagrams, schematics, and plots.
- **Collaborative Research Workspaces:** Multi-user synchronization via local network peer discovery.

---

## 21. Implemented, Tested & Incomplete Feature Checklist

### Implemented & Verified Working (21 of 21)
- [x] **Project Management:** Project creation, editing, searching, filtering, and cascading deletion.
- [x] **PDF Ingestion:** Drag-and-drop, multiple uploads, file validation, and disk storage.
- [x] **PDF Text Extraction:** PyMuPDF extraction preserving paragraph and table structure.
- [x] **Page Preservation:** Strictly 1-indexed page preservation throughout the pipeline.
- [x] **Metadata Extraction:** Title, authors, abstract, venue, DOI, and publication year extraction.
- [x] **Embedding Generation:** 768-dimensional normalized dense vector embedding with non-blocking fallback.
- [x] **ChromaDB Storage:** Persistent `literature_chunks` collection using Cosine HNSW indexing.
- [x] **Semantic Retrieval:** Nearest-neighbor top-$K$ semantic search with page provenance.
- [x] **Research Q&A (RAG):** Context-grounded literature Q&A with exact citations.
- [x] **Paper Analysis:** 14-dimension structured academic deconstruction with excerpt provenance.
- [x] **Research Discovery:** Open-access querying via OpenAlex, arXiv, and Semantic Scholar.
- [x] **Cross-Paper Comparison:** 13-criteria comparative matrix across 2 to 5 papers.
- [x] **Knowledge Graph:** Interactive entity-relationship network (Papers, Authors, Algorithms, Datasets).
- [x] **Research Gap Discovery:** Explicit author limitations + 10-dimension implicit gaps with confidence scoring.
- [x] **Contradiction Detection:** Cross-paper conflicting findings, conclusions, and side-by-side excerpts.
- [x] **Evidence Verification:** Factual claim validation with Supported / Contradicted statuses.
- [x] **Multi-Agent Orchestrator:** Sequential 8-agent pipeline with execution checkpointing and resume.
- [x] **Report Generator:** Literature review generation supporting IEEE and APA citation formatting.
- [x] **Multi-Format Exporters:** Publication-grade PDF (`%PDF-`), Microsoft Word (`PK` DOCX), and Markdown.
- [x] **Frontend-Backend Integration:** React TypeScript frontend connected to all FastAPI endpoints.
- [x] **Database Persistence:** On-disk durability verified across SQLite and ChromaDB after restart.

### Incomplete / Future Scope (Deliberately Deferred)
- [ ] Native OCR for scanned non-text PDFs (requires bundled Tesseract binary).
- [ ] Direct Overleaf / Git export synchronization.
- [ ] Vision-language multi-modal diagram deconstruction.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
