# Literature Intelligence Platform — Agent Architecture

## Overview

The platform coordinates a cooperative network of **ten specialized autonomous agents** orchestrated sequentially by the central **Multi-Agent Orchestrator**. Each agent executes a discrete, academically rigorous intelligence task, transforms structured inputs, and persists validated outputs to SQLite and ChromaDB.

```
                           +------------------------------+
                           |  Multi-Agent Orchestrator   |
                           +--------------+---------------+
                                          |
        +-------------------+-------------+-------------+--------------------+
        |                   |                           |                    |
        v                   v                           v                    v
+---------------+   +---------------+           +---------------+   +---------------+
| 1. Discovery  |   | 2. PDF Under- |           | 5. Comparison |   | 6. Knowledge  |
|     Agent     |   | standing Agent|           |     Agent     |   |  Graph Agent  |
+---------------+   +---------------+           +---------------+   +---------------+
        |                   |                           |                    |
        v                   v                           v                    v
+---------------+   +---------------+           +---------------+   +---------------+
| 3. Retrieval  |   | 4. Research   |           | 7. Gap        |   | 8. Evidence   |
|     Agent     |   | Analysis Agent|           | Discovery     |   | Verification  |
+---------------+   +---------------+           +---------------+   +---------------+
        |                   |                           |                    |
        +-------------------+-------------+-------------+--------------------+
                                          |
                                          v
                            +---------------------------+
                            | 9. Contradiction Detector |
                            | 10. Trend Analysis Agent  |
                            | Final Report Generator    |
                            +---------------------------+
```

---

## 1. Central Multi-Agent Orchestrator (`orchestrator.py`)

- **Role:** Execution coordinator and state manager.
- **Key Responsibilities:**
  - Enforces serialized execution order to prevent concurrent LLM memory collisions.
  - Tracks real progress percentages based on completed vs. total stages (no artificial percentages).
  - Maintains execution audit logs in `agent_execution_histories`.
  - Implements stage checkpointing in `backend/data/workflows/{workflow_id}.json` allowing resumes from failure points without repeating completed stages.
  - Supports individual agent invocation as well as full end-to-end autonomous runs.

---

## 2. Agent Catalog & Specifications

### Agent 1: Research Discovery Agent (`discovery_agent.py`)
- **Objective:** Discover relevant peer-reviewed literature across public open-access academic repositories.
- **External Data Providers:** arXiv API, OpenAlex API, Semantic Scholar API.
- **Input:** Search topic, user keywords, publication year filters, limit per source.
- **Output:** Normalized list of discovered papers with titles, authors, DOIs, publication venues, abstracts, and direct PDF download URLs.
- **Deduplication:** Automatic deduplication using DOI and normalized title Levenshtein similarity.

### Agent 2: PDF Understanding Agent (`pdf_understanding_agent.py`)
- **Objective:** Ingest raw academic PDFs, preserve page layout geometry, extract structured sections, and vectorize content.
- **Extraction Engine:** PyMuPDF (`fitz`) for memory-efficient text and tabular parsing.
- **Chunking Pipeline:** Token-aware sliding-window chunker (512 tokens, 64 overlap).
- **Page Attribution:** Enforces strictly 1-indexed page numbering for every generated chunk.
- **Output:** Extracted metadata (title, abstract, authors, year) stored in `research_papers`, text passages in `paper_sections`, and dense vectors in ChromaDB `literature_chunks`.

### Agent 3: Semantic Retrieval Agent (`retrieval_agent.py`)
- **Objective:** Retrieve highly relevant context passages for user queries and downstream agents.
- **Retrieval Mechanism:** Cosine similarity nearest-neighbor search over 768-dimensional dense vectors in ChromaDB.
- **Filtering:** Scopes queries to specific project IDs or paper subsets.
- **Output:** Top-$K$ relevant chunks ranked by relevance score, including verbatim passage text, source paper title, section name, and 1-indexed page number.

### Agent 4: Research Analysis Agent (`research_analysis_agent.py`)
- **Objective:** Perform in-depth academic deconstruction of individual research papers.
- **14 Structured Dimensions Analyzed:**
  1. Title & Abstract
  2. Research Problem / Gap Addressed
  3. Research Objectives
  4. Theoretical Framework
  5. Methodology / Architecture
  6. Algorithms & Formulations
  7. Datasets & Benchmarks
  8. Experimental Results & Metrics
  9. Key Findings
  10. Strengths & Innovations
  11. Limitations & Assumptions
  12. Future Research Directions
  13. Practical Applications
  14. Bibliography & Citations
- **Output:** Persisted in `paper_analyses` with verbatim quotes and page numbers for each dimension.

### Agent 5: Cross-Paper Comparison Agent (`comparison_agent.py`)
- **Objective:** Synthesize comparative insights across cohorts of 2 to 5 papers.
- **13-Criteria Matrix:** Objectives, algorithms, methodologies, datasets, evaluation metrics, empirical results, strengths, limitations, hardware constraints, scalability, explainability, reproducibility, and future directions.
- **Output:** Formats a structured matrix table and a coherent written comparative narrative highlighting critical differences.

### Agent 6: Research Knowledge Graph Agent (`graph_service.py`)
- **Objective:** Map interconnected entities and conceptual relationships across the research corpus.
- **Entity Types:** Papers, Authors, Algorithms, Datasets, Research Topics, Venues.
- **Relationship Types:** `AUTHORED_BY`, `USES_ALGORITHM`, `EVALUATED_ON`, `ADDRESSES_TOPIC`, `CITES`, `CONTRASTS_WITH`.
- **Output:** Directed graph network exported in D3/Canvas-compatible JSON format with node centrality metrics and cluster assignments.

### Agent 7: Research Gap Discovery Agent (`gap_agent.py`)
- **Objective:** Uncover under-explored research questions and methodological blind spots.
- **Two-Tier Identification:**
  - *Explicit Gaps:* Extracted directly from author-stated limitations, failure cases, and future work sections.
  - *Implicit Gaps:* Inferred via cross-paper comparison across 10 academic dimensions (e.g., conflicting trade-offs, mismatched evaluation benchmarks, dataset coverage limitations).
- **Confidence Scoring:** Transparent heuristic evidence-grounding index based on number of supporting papers, verbatim granularity, and absence of counter-evidence.
- **Output:** Persisted in `research_gaps` and `gap_evidences` with counter-evidence checks and suggested research directions.

### Agent 8: Evidence Verification Agent (`verification_agent.py`)
- **Objective:** Validate research claims against source literature to prevent hallucination.
- **Verification Classifications:**
  - `Supported`: Directly backed by verbatim evidence from the paper.
  - `Partially Supported`: Partially corroborated with minor scope differences.
  - `Contradicted`: Directly contradicted by the empirical data or author statements.
  - `Insufficient Evidence`: No corresponding evidence found in the corpus.
- **Output:** Persisted in `verification_results` with the original passage excerpt, exact page number, and reasoning.

### Agent 9: Contradiction Detection Agent (`contradiction_detector.py`)
- **Objective:** Detect contradictory findings, opposing conclusions, and divergent results across papers.
- **Conflict Categories:** Experimental results, conclusions, methodologies, dataset findings, algorithmic claims.
- **Condition Analysis:** Distinguishes genuine theoretical contradictions from differences caused by varying experimental conditions, hyperparameters, or dataset shifts.
- **Output:** Persisted in `research_contradictions` with side-by-side excerpts and root-cause analyses.

### Agent 10: Research Trend Analysis Agent (`trend_agent.py`)
- **Objective:** Compute empirical historical trends and statistical trajectories across the ingested literature.
- **Analytics:** Publication distribution by year, algorithm adoption frequencies, dataset usage distributions, recurring limitations, and emergent research clusters.
- **Data Integrity:** Driven strictly by SQLite relational queries; never generates fabricated statistics.

---

## 3. Agent Communication & Data Contracts

All agents communicate via strictly typed Pydantic models:

```python
# Standard Agent Invocation Pattern
class AgentRequest(BaseModel):
    project_id: str
    paper_ids: Optional[List[str]] = None
    force_recompute: bool = False

class AgentResponse(BaseModel):
    status: str
    duration_ms: int
    data: Any
    evidence_citations: List[EvidenceCitation]
```
