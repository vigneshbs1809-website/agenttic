# Literature Intelligence Platform — API Documentation

## Base URL
```
http://127.0.0.1:8000/api
```

All requests expect and return `application/json` unless downloading binary report exports (`application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, or `text/markdown`).

---

## 1. Project Management (`/projects`)

### `GET /projects`
Returns a list of all research projects with aggregated counts of associated papers.
- **Response:** `200 OK`
```json
[
  {
    "id": "fd36eb60-15ae-4002-a218-2f993c8676d4",
    "title": "Autonomous Fleet Routing & Coordination",
    "domain": "Multi-Agent Robotics",
    "description": "Comparative literature study on graph attention vs. value factorization.",
    "paper_count": 3,
    "created_at": "2026-11-13T04:20:00",
    "updated_at": "2026-11-13T04:20:00"
  }
]
```

### `POST /projects`
Creates a new research project.
- **Request Body:**
```json
{
  "title": "Quantum Annealing for Combinatorial Optimization",
  "domain": "Quantum Computing",
  "description": "Analyzing qubit-resonator scalability."
}
```
- **Response:** `201 Created` — Returns the created `ResearchProjectResponse`.

### `DELETE /projects/{project_id}`
Cascading deletion of a research project and all associated papers, chunks, vector embeddings, analyses, and reports.
- **Response:** `200 OK`

---

## 2. Document Ingestion & PDF Library (`/documents`)

### `POST /documents/upload`
Uploads one or more academic research PDF files into a project.
- **Content-Type:** `multipart/form-data`
- **Form Fields:**
  - `project_id`: Target project UUID
  - `files`: PDF binary stream(s)
- **Response:** `200 OK` with list of uploaded paper metadata records.

### `GET /documents?project_id={project_id}`
Lists all papers associated with a project, including file sizes, page counts, and extraction statuses.

### `GET /documents/{paper_id}/text`
Retrieves raw extracted text and section breakdowns with 1-indexed page markers.

### `DELETE /documents/{paper_id}`
Deletes a paper, its extracted sections, and its ChromaDB vector chunks.

---

## 3. Semantic Retrieval & RAG (`/rag`)

### `POST /rag/query`
Executes semantic retrieval across project papers and synthesizes grounded answers with page citations.
- **Request Body:**
```json
{
  "project_id": "fd36eb60-15ae-4002-a218-2f993c8676d4",
  "query": "How does hierarchical graph attention scale compared to centralized factorization?",
  "top_k": 5
}
```
- **Response:** `200 OK`
```json
{
  "answer": "Hierarchical Graph Attention mitigates communication bottlenecks by clustering local fleets into regional sub-graphs [Hierarchical Graph Attention for Scalable Fleet Routing, Page 2]. In contrast, centralized value factorization enforces joint action coordination but suffers from scaling degradation in large dense networks [Centralized Value Factorization, Page 1].",
  "sources": [
    {
      "paper_id": "aud-0c8d1346",
      "paper_title": "Hierarchical Graph Attention for Scalable Fleet Routing",
      "page_number": 2,
      "section_title": "Methodology",
      "excerpt": "Local edge-level attention computes localized routing decisions without global synchronization..."
    }
  ]
}
```

---

## 4. Paper Analysis (`/analysis`)

### `GET /analysis/{paper_id}`
Retrieves 14-dimension structured academic analysis of an individual paper.
- **Dimensions returned:** Research Problem, Objectives, Methodology, Algorithms, Datasets, Results, Strengths, Limitations, Future Directions, etc.
- Each field includes: `summary`, `verbatim_passage`, and `page_number`.

---

## 5. Cross-Paper Comparison (`/comparison`)

### `POST /comparison`
Generates a comprehensive 13-criteria comparison matrix across 2 to 5 papers.
- **Request Body:**
```json
{
  "project_id": "fd36eb60-15ae-4002-a218-2f993c8676d4",
  "paper_ids": ["aud-0c8d1346", "aud-be1f2b64", "aud-14d249d9"],
  "title": "Scalable Fleet Coordination Comparison"
}
```
- **Response:** `200 OK` returning structured matrix rows and comparative written narrative.

---

## 6. Knowledge Graph (`/graph`)

### `GET /graph/global?max_papers=50`
Returns the global multi-project knowledge graph network.

### `GET /graph/project/{project_id}`
Returns the scoped project knowledge graph.
- **Response Structure:**
```json
{
  "nodes": [
    {"id": "paper-1", "label": "Hierarchical Graph Attention", "type": "paper"},
    {"id": "algo-1", "label": "HGAT Attention Mechanism", "type": "algorithm"}
  ],
  "edges": [
    {"source": "paper-1", "target": "algo-1", "label": "USES_ALGORITHM"}
  ]
}
```

---

## 7. Research Gap Discovery (`/gaps`)

### `POST /gaps/discover`
Discovers explicit author-stated and implicit cross-paper research gaps.
- **Request Body:**
```json
{
  "project_id": "fd36eb60-15ae-4002-a218-2f993c8676d4",
  "include_explicit": true,
  "include_implicit": true,
  "force_rediscover": false
}
```
- **Response:** `200 OK`
```json
{
  "project_id": "fd36eb60-15ae-4002-a218-2f993c8676d4",
  "total_gaps_found": 5,
  "explicit_gaps_count": 3,
  "implicit_gaps_count": 2,
  "gaps": [
    {
      "id": "gap-uuid",
      "title": "Limited Scalability Beyond 50-Agent Swarms",
      "gap_type": "scalability",
      "identification_method": "explicit_author_stated",
      "confidence_score": 0.85,
      "confidence_justification": "Heuristic evidence quality score: Base grounding (0.45) + Multi-paper confirmation (0.15) + Specificity bonus (0.25)",
      "suggested_direction": "Investigate dynamic sparse attention clustering.",
      "evidences": [
        {
          "paper_title": "Hierarchical Graph Attention for Scalable Fleet Routing",
          "page_number": 2,
          "quote_or_excerpt": "Performance degrades significantly when swarm size exceeds 50 agents due to message drop rates."
        }
      ]
    }
  ]
}
```

---

## 8. Contradiction Detection (`/contradictions`)

### `POST /contradictions/detect`
Detects conflicting findings, conclusions, and methodologies across papers.
- **Response:** `200 OK` returning side-by-side excerpts, titles, pages, and condition-divergence explanations.

---

## 9. Evidence Verification (`/verification`)

### `POST /verification/verify-claim`
Verifies an academic claim against paper evidence.
- **Request Body:**
```json
{
  "paper_id": "aud-0c8d1346",
  "claim_text": "Hierarchical attention diminishes communication latency by 42%."
}
```
- **Response:** `200 OK`
```json
{
  "paper_id": "aud-0c8d1346",
  "claim_text": "Hierarchical attention diminishes communication latency by 42%.",
  "verification_status": "Supported",
  "original_evidence": "Hierarchical graph attention achieves a 42% reduction in end-to-end communication latency across 100-vehicle topologies.",
  "page_number": 2,
  "similarity_score": 0.94,
  "is_verified_finding": true,
  "explanation": "Corroborated by empirical findings passage on Page 2."
}
```

---

## 10. Research Reports (`/reports`)

### `POST /reports/generate`
Generates a full academic report (literature review, comparison dossier, gap analysis).
- **Supported Citation Styles:** `IEEE`, `APA`.

### `GET /reports/{report_id}/export/{format}`
Exports the report in publication formats:
- `pdf`: Formatted PDF document (`application/pdf`)
- `docx`: Microsoft Word document (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
- `markdown`: Clean Markdown (`text/markdown`)

---

## 11. Multi-Agent Orchestrator (`/orchestrator`)

### `POST /orchestrator/workflows`
Initializes a complete sequential workflow.

### `POST /orchestrator/workflows/{workflow_id}/run`
Executes or resumes the workflow. Provides non-blocking execution status.

### `GET /orchestrator/workflows/{workflow_id}`
Returns honest real progress percentage and live timestamped execution logs.

---

## 12. System Health & Diagnostics (`/system`)

### `GET /system/status`
Returns real-time status of SQLite, ChromaDB, PDF Storage, RAM utilization, and Ollama connection.

### `POST /system/diagnostics`
Runs an itemized 7-point diagnostic sweep across host RAM, database connectivity, vector storage, and model endpoints.
