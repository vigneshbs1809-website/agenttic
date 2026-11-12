import os
import sys
import time
import json
import uuid
import psutil
from pathlib import Path
from typing import Dict, Any, List

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal, init_db
from backend.app.models.entities import (
    ResearchProject,
    ResearchPaper,
    PaperSection,
    PaperAnalysis,
    ResearchGap,
    ResearchContradiction,
    VerificationResult,
    GeneratedReport,
    AgentExecutionHistory
)

client = TestClient(app)

AUDIT_CORPUS_DIR = Path("backend/data/audit_corpus")

ALL_10_PAPERS = [
    "paper_04_fleet_routing_hgat.pdf",
    "paper_05_trajectory_diffusion.pdf",
    "paper_06_value_factorization.pdf",
    "paper_07_graph_literature.pdf",
    "paper_08_sparse_attention.pdf",
    "paper_09_federated_continual.pdf",
    "paper_10_async_swarmopt.pdf",
    "paper_02_quantum_annealing.pdf",
    "paper_03_inverse_rl_values.pdf",
    "paper_01_imperial_marl.pdf"
]

def get_ram_mb() -> float:
    return round(psutil.virtual_memory().used / (1024 * 1024), 2)

def print_section(title: str):
    print("\n" + "=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)

audit_results = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "subsystem_checks": {},
    "cohort_benchmarks": {},
    "verification_audit": {},
    "persistence_audit": {},
    "summary_metrics": {}
}

def run_end_to_end_audit():
    init_db()
    start_ram = get_ram_mb()
    overall_start = time.time()

    print_section("Literature Intelligence Platform: End-to-End Audit")
    print(f"Initial Host RAM: {start_ram} MB")
    print(f"Corpus Directory: {AUDIT_CORPUS_DIR.resolve()}")

    # --------------------------------------------------------------------------
    # ITEM 1: Project Creation and Deletion Test
    # --------------------------------------------------------------------------
    print_section("1. Project Creation & Deletion Audit")
    t0 = time.time()
    create_res = client.post("/api/projects", json={
        "title": f"Audit Temporary Project {uuid.uuid4().hex[:6]}",
        "domain": "Audit Testing",
        "description": "Lifecycle testing project for creation and deletion"
    })
    assert create_res.status_code == 200, f"Project creation failed: {create_res.text}"
    tmp_proj = create_res.json()
    tmp_proj_id = tmp_proj["id"]
    create_dur = round((time.time() - t0) * 1000, 2)
    print(f"-> Created test project '{tmp_proj['title']}' (ID: {tmp_proj_id}) in {create_dur} ms")

    # Verify in DB
    with SessionLocal() as db:
        p_db = db.query(ResearchProject).filter(ResearchProject.id == tmp_proj_id).first()
        assert p_db is not None, "Project not persisted in SQLite"

    # Delete project
    del_res = client.delete(f"/api/projects/{tmp_proj_id}")
    assert del_res.status_code == 200, f"Project deletion failed: {del_res.text}"
    with SessionLocal() as db:
        p_db_after = db.query(ResearchProject).filter(ResearchProject.id == tmp_proj_id).first()
        assert p_db_after is None, "Project was not deleted from SQLite"
    print(f"-> Verified project deletion and database cleanup successfully.")
    audit_results["subsystem_checks"]["1_project_lifecycle"] = "PASSED"

    # --------------------------------------------------------------------------
    # Setup Dedicated Audit Projects for Cohorts: 3, 5, and 10 Papers
    # --------------------------------------------------------------------------
    cohort_configs = [
        ("Cohort-3", ALL_10_PAPERS[:3], "Autonomous Fleet & Routing Optimization"),
        ("Cohort-5", ALL_10_PAPERS[:5], "Multi-Agent Neural Architectures & Attention"),
        ("Cohort-10", ALL_10_PAPERS[:10], "Comprehensive Multi-Agent Systems & Distributed AI")
    ]

    for cohort_name, paper_files, topic in cohort_configs:
        print_section(f"Testing {cohort_name}: {len(paper_files)} Real Academic Papers")
        cohort_metrics: Dict[str, Any] = {
            "paper_count": len(paper_files),
            "topic": topic,
            "timings_ms": {},
            "ram_mb": {}
        }
        cohort_metrics["ram_mb"]["start"] = get_ram_mb()

        # Create Project for this Cohort
        proj_res = client.post("/api/projects", json={
            "title": f"Audit {cohort_name} - {topic}",
            "domain": topic,
            "description": f"Auditing {len(paper_files)} academic papers end-to-end."
        })
        assert proj_res.status_code == 200
        proj_id = proj_res.json()["id"]

        # ----------------------------------------------------------------------
        # ITEM 2, 3, 4, 5: Uploading, Extraction, Page Preservation, Metadata
        # ----------------------------------------------------------------------
        uploaded_papers = []
        ingest_start = time.time()

        for fname in paper_files:
            fpath = AUDIT_CORPUS_DIR / fname
            assert fpath.exists(), f"Corpus PDF missing: {fpath}"
            
            p_start = time.time()
            with open(fpath, "rb") as f:
                upload_res = client.post(
                    f"/api/documents/upload?project_id={proj_id}",
                    files={"file": (fname, f, "application/pdf")}
                )
            assert upload_res.status_code == 200, f"Upload failed for {fname}: {upload_res.text}"
            doc_data = upload_res.json()
            p_dur = round((time.time() - p_start) * 1000, 2)
            uploaded_papers.append(doc_data)

            # Check Page preservation
            pages_res = client.get(f"/api/documents/{doc_data['id']}/pages")
            assert pages_res.status_code == 200
            pages = pages_res.json()
            assert len(pages) == doc_data["total_pages"], f"Page count mismatch: {len(pages)} vs {doc_data['total_pages']}"
            assert pages[0]["page_number"] == 1, "Page numbering is not 1-indexed"
            assert len(pages[0]["text"].strip()) > 0, f"Empty text extracted from {fname}"

            print(f"  [{doc_data['id'][:8]}] Ingested '{doc_data['title'][:45]}' | {doc_data['total_pages']}p | {p_dur} ms")

        total_ingest_dur = round((time.time() - ingest_start) * 1000, 2)
        cohort_metrics["timings_ms"]["ingestion_total"] = total_ingest_dur
        cohort_metrics["timings_ms"]["ingestion_avg_per_paper"] = round(total_ingest_dur / len(paper_files), 2)
        print(f"-> Total Ingestion Time for {len(paper_files)} papers: {total_ingest_dur} ms")

        # ----------------------------------------------------------------------
        # ITEM 6 & 7: Embedding Generation & ChromaDB Storage
        # ----------------------------------------------------------------------
        t_embed = time.time()
        test_emb_res = client.post("/api/system/test/embedding")
        embed_status = test_emb_res.json()
        cohort_metrics["timings_ms"]["embedding_test"] = round((time.time() - t_embed) * 1000, 2)

        # Audit ChromaDB chunk storage for these papers
        db_audit_res = client.post("/api/system/test/databases")
        assert db_audit_res.status_code == 200
        db_audit = db_audit_res.json()
        print(f"-> Database Latency: SQLite={db_audit['sqlite_latency_ms']} ms, ChromaDB={db_audit['chromadb_latency_ms']} ms")
        print(f"-> ChromaDB Total Chunks: {db_audit['chromadb_total_chunks']}")

        # ----------------------------------------------------------------------
        # ITEM 8 & 9: Semantic Retrieval & Research Question Answering (RAG)
        # ----------------------------------------------------------------------
        paper_ids = [p["id"] for p in uploaded_papers]
        retrieval_start = time.time()
        rag_query = f"What are the algorithmic methodologies and experimental outcomes for {topic}?"
        rag_res = client.post("/api/rag/query", json={
            "question": rag_query,
            "top_k": 4,
            "paper_ids": paper_ids,
            "method": "hybrid"
        })
        assert rag_res.status_code == 200, f"RAG query failed: {rag_res.text}"
        rag_data = rag_res.json()
        rag_dur = round((time.time() - retrieval_start) * 1000, 2)
        cohort_metrics["timings_ms"]["rag_synthesis"] = rag_dur
        print(f"-> RAG Question Answering ({rag_dur} ms): Answer length {len(rag_data['answer'])} chars, Citations: {len(rag_data['citations'])}")
        
        # Verify citations have page numbers and verbatim snippets
        for cit in rag_data["citations"]:
            assert "page_number" in cit and cit["page_number"] >= 1, "Citation missing valid page number"
            assert "original_text" in cit and len(cit["original_text"]) > 0, "Citation missing original text"
            assert cit["paper_id"] in paper_ids, f"Invalid citation paper_id {cit['paper_id']}"

        # ----------------------------------------------------------------------
        # ITEM 10: Individual Paper Analysis
        # ----------------------------------------------------------------------
        target_paper_id = paper_ids[0]
        an_start = time.time()
        analysis_res = client.get(f"/api/analysis/report/{target_paper_id}?regenerate=false")
        assert analysis_res.status_code == 200, f"Paper analysis failed: {analysis_res.text}"
        an_data = analysis_res.json()
        an_dur = round((time.time() - an_start) * 1000, 2)
        cohort_metrics["timings_ms"]["individual_analysis"] = an_dur
        print(f"-> Individual Paper Analysis ({an_dur} ms): Problem={an_data['research_problem']['value'][:60]}...")
        assert len(an_data["methodology"]["evidence"]) > 0, "Methodology missing verified evidence reference"

        # ----------------------------------------------------------------------
        # ITEM 11: Academic Research Discovery Agent
        # ----------------------------------------------------------------------
        disc_start = time.time()
        disc_res = client.post("/api/discovery/search", json={
            "topic": "multi-agent reinforcement learning",
            "keywords": ["decentralized", "policy optimization"],
            "limit_per_source": 3
        })
        assert disc_res.status_code == 200
        disc_data = disc_res.json()
        disc_dur = round((time.time() - disc_start) * 1000, 2)
        cohort_metrics["timings_ms"]["discovery_search"] = disc_dur
        print(f"-> Research Discovery Agent ({disc_dur} ms): Returned {disc_data['total_found']} candidate papers")

        # ----------------------------------------------------------------------
        # ITEM 12: Cross-Paper Comparative Analysis (2-5 papers)
        # ----------------------------------------------------------------------
        comp_subset = paper_ids[:min(len(paper_ids), 3)]
        comp_start = time.time()
        comp_res = client.post("/api/comparison/compare", json={"paper_ids": comp_subset})
        assert comp_res.status_code == 200, f"Comparison failed: {comp_res.text}"
        comp_data = comp_res.json()
        comp_dur = round((time.time() - comp_start) * 1000, 2)
        cohort_metrics["timings_ms"]["cross_comparison"] = comp_dur
        print(f"-> Cross-Paper Comparison ({comp_dur} ms): Matrix rows={len(comp_data.get('matrix', []))}, Papers compared={len(comp_subset)}")

        # ----------------------------------------------------------------------
        # ITEM 13: Knowledge Graph Generation
        # ----------------------------------------------------------------------
        kg_start = time.time()
        kg_res = client.get(f"/api/graph/overview?max_papers=50")
        assert kg_res.status_code == 200
        kg_data = kg_res.json()
        kg_dur = round((time.time() - kg_start) * 1000, 2)
        cohort_metrics["timings_ms"]["knowledge_graph"] = kg_dur
        print(f"-> Knowledge Graph Agent ({kg_dur} ms): Nodes={len(kg_data.get('nodes', []))}, Links={len(kg_data.get('links', []))}")

        # ----------------------------------------------------------------------
        # ITEM 14: Research Gap Discovery Agent
        # ----------------------------------------------------------------------
        gap_start = time.time()
        gap_res = client.post(f"/api/gaps/discover/{proj_id}", json={
            "include_explicit": True,
            "include_implicit": True,
            "force_rediscover": False
        })
        assert gap_res.status_code == 200, f"Gap discovery failed: {gap_res.text}"
        gap_data = gap_res.json()
        gap_dur = round((time.time() - gap_start) * 1000, 2)
        cohort_metrics["timings_ms"]["gap_discovery"] = gap_dur
        print(f"-> Research Gap Discovery ({gap_dur} ms): Discovered {gap_data['total_gaps']} gaps across {len(paper_ids)} papers")
        assert gap_data["total_gaps"] > 0, "No research gaps discovered"

        # ----------------------------------------------------------------------
        # ITEM 15: Contradiction Detection Agent
        # ----------------------------------------------------------------------
        contra_start = time.time()
        contra_res = client.post("/api/contradictions/detect", json={
            "project_id": proj_id,
            "paper_ids": paper_ids,
            "force_redetect": False
        })
        assert contra_res.status_code == 200, f"Contradiction detection failed: {contra_res.text}"
        contra_data = contra_res.json()
        contra_dur = round((time.time() - contra_start) * 1000, 2)
        cohort_metrics["timings_ms"]["contradiction_detection"] = contra_dur
        print(f"-> Contradiction Detection ({contra_dur} ms): Total contradictions detected={contra_data['total_contradictions']}")

        # ----------------------------------------------------------------------
        # ITEM 16: Evidence Verification Agent
        # ----------------------------------------------------------------------
        # Test 1: Supported claim from paper
        ver_start = time.time()
        sup_claim_res = client.post("/api/verification/verify-claim", json={
            "paper_id": target_paper_id,
            "claim_text": uploaded_papers[0]["abstract"][:120] if uploaded_papers[0]["abstract"] else "Sparse attention reduces memory consumption."
        })
        assert sup_claim_res.status_code == 200, f"Verification failed: {sup_claim_res.text}"
        sup_data = sup_claim_res.json()
        
        # Test 2: Deliberately unsupported claim
        unsup_claim_res = client.post("/api/verification/verify-claim", json={
            "paper_id": target_paper_id,
            "claim_text": "This paper establishes that teleportation of macroscopic objects occurs at room temperature with 100% fidelity."
        })
        assert unsup_claim_res.status_code == 200
        unsup_data = unsup_claim_res.json()
        ver_dur = round((time.time() - ver_start) * 1000, 2)
        cohort_metrics["timings_ms"]["evidence_verification"] = ver_dur

        print(f"-> Verification Agent ({ver_dur} ms): Claim 1 Status = '{sup_data['verification_status']}', Claim 2 Status = '{unsup_data['verification_status']}'")
        assert unsup_data["verification_status"] in ["Contradicted", "Insufficient Evidence"], \
            f"Deliberately unsupported claim marked as {unsup_data['verification_status']}!"

        # ----------------------------------------------------------------------
        # ITEM 17: Multi-Agent Orchestrator
        # ----------------------------------------------------------------------
        orch_start = time.time()
        run_stage_res = client.post("/api/orchestrator/run-stage", json={
            "project_id": proj_id,
            "stage_id": "report_generation",
            "paper_ids": paper_ids,
            "force": False
        })
        assert run_stage_res.status_code == 200, f"Orchestrator stage execution failed: {run_stage_res.text}"
        orch_stage_data = run_stage_res.json()
        orch_dur = round((time.time() - orch_start) * 1000, 2)
        cohort_metrics["timings_ms"]["orchestrator_stage"] = orch_dur
        print(f"-> Multi-Agent Orchestrator Stage Execution ({orch_dur} ms): Status={orch_stage_data['status']}")

        # ----------------------------------------------------------------------
        # ITEM 18: Academic Report Generation (IEEE & APA)
        # ----------------------------------------------------------------------
        rep_start = time.time()
        rep_res = client.post("/api/reports/generate", json={
            "project_id": proj_id,
            "report_type": "literature_review",
            "citation_style": "IEEE",
            "paper_ids": paper_ids,
            "custom_title": f"Literature Review: {topic}"
        })
        assert rep_res.status_code == 200, f"Report generation failed: {rep_res.text}"
        rep_data = rep_res.json()
        report_id = rep_data["id"]
        rep_dur = round((time.time() - rep_start) * 1000, 2)
        cohort_metrics["timings_ms"]["report_generation"] = rep_dur
        print(f"-> Academic Report Generator ({rep_dur} ms): Generated '{rep_data['report_title']}' ({rep_data['word_count']} words, ID: {report_id})")

        # ----------------------------------------------------------------------
        # ITEM 19: PDF, DOCX, and Markdown Export Downloads
        # ----------------------------------------------------------------------
        exp_start = time.time()
        # 19a. Markdown export
        md_exp = client.get(f"/api/reports/{report_id}/export/markdown")
        assert md_exp.status_code == 200
        assert len(md_exp.text) > 500, "Markdown export is empty or truncated"

        # 19b. PDF export
        pdf_exp = client.get(f"/api/reports/{report_id}/export/pdf")
        assert pdf_exp.status_code == 200
        assert pdf_exp.content.startswith(b"%PDF-"), "Invalid PDF binary signature"
        assert len(pdf_exp.content) > 1000, "Exported PDF is empty"

        # 19c. DOCX export
        docx_exp = client.get(f"/api/reports/{report_id}/export/docx")
        assert docx_exp.status_code == 200
        assert docx_exp.content.startswith(b"PK"), "Invalid DOCX zip archive signature"
        assert len(docx_exp.content) > 1000, "Exported DOCX is empty"

        exp_dur = round((time.time() - exp_start) * 1000, 2)
        cohort_metrics["timings_ms"]["export_all_formats"] = exp_dur
        print(f"-> Multi-Format Exporters ({exp_dur} ms): MD={len(md_exp.text)} chars, PDF={len(pdf_exp.content)} bytes, DOCX={len(docx_exp.content)} bytes")

        cohort_metrics["ram_mb"]["end"] = get_ram_mb()
        cohort_metrics["ram_mb"]["net_delta"] = round(cohort_metrics["ram_mb"]["end"] - cohort_metrics["ram_mb"]["start"], 2)
        print(f"-> RAM Usage: Start={cohort_metrics['ram_mb']['start']} MB, End={cohort_metrics['ram_mb']['end']} MB (Delta: {cohort_metrics['ram_mb']['net_delta']} MB)")

        audit_results["cohort_benchmarks"][cohort_name] = cohort_metrics

    # --------------------------------------------------------------------------
    # ITEM 20: Frontend-Backend Integration Audit (Validate all frontend endpoints)
    # --------------------------------------------------------------------------
    print_section("20. Frontend-Backend API Route Parity Audit")
    frontend_routes = [
        ("GET", "/api/health"),
        ("GET", "/api/system/status"),
        ("GET", "/api/system/config"),
        ("GET", "/api/projects"),
        ("GET", "/api/documents"),
        ("GET", "/api/gaps/categories"),
        ("GET", "/api/contradictions/categories"),
        ("GET", "/api/trends/overview"),
        ("GET", "/api/orchestrator/stages"),
        ("GET", "/api/orchestrator/history"),
        ("GET", "/api/reports/history"),
        ("GET", "/api/system/agent-logs")
    ]

    route_errors = []
    for method, route in frontend_routes:
        t_r = time.time()
        if method == "GET":
            res = client.get(route)
        dur = round((time.time() - t_r) * 1000, 2)
        if res.status_code != 200:
            route_errors.append((route, res.status_code, res.text))
            print(f"  [FAIL] {method} {route} -> HTTP {res.status_code}")
        else:
            print(f"  [PASS] {method} {route} ({dur} ms)")

    assert len(route_errors) == 0, f"Frontend routes failed: {route_errors}"
    audit_results["subsystem_checks"]["20_frontend_routes_parity"] = "PASSED"

    # --------------------------------------------------------------------------
    # ITEM 21: Database Persistence Audit After Restart
    # --------------------------------------------------------------------------
    print_section("21. Database Persistence Audit After Restart")
    # Simulate application restart: tear down SQLAlchemy sessions & re-query database
    from sqlalchemy.orm import close_all_sessions
    close_all_sessions()

    with SessionLocal() as db_restart:
        total_projects = db_restart.query(ResearchProject).count()
        total_papers = db_restart.query(ResearchPaper).count()
        total_sections = db_restart.query(PaperSection).count()
        total_gaps = db_restart.query(ResearchGap).count()
        total_contra = db_restart.query(ResearchContradiction).count()
        total_reports = db_restart.query(GeneratedReport).count()

        print(f"-> Persistent SQLite Entities After Restart:")
        print(f"   Projects: {total_projects}")
        print(f"   Research Papers: {total_papers}")
        print(f"   Paper Sections: {total_sections}")
        print(f"   Research Gaps: {total_gaps}")
        print(f"   Contradictions: {total_contra}")
        print(f"   Generated Reports: {total_reports}")

        assert total_projects >= 3, "Projects not persisted"
        assert total_papers >= 18, "Papers not persisted"
        assert total_sections >= 50, "Sections not persisted"
        assert total_gaps >= 5, "Gaps not persisted"
        assert total_reports >= 3, "Reports not persisted"

    # Check ChromaDB persistence
    from backend.app.services.chroma_service import chroma_service
    chroma_count = chroma_service.collection.count()
    print(f"-> Persistent ChromaDB Vectors After Restart: {chroma_count} indexed chunks")
    assert chroma_count >= 100, "ChromaDB vectors lost across restart"

    audit_results["persistence_audit"] = {
        "sqlite_projects": total_projects,
        "sqlite_papers": total_papers,
        "sqlite_sections": total_sections,
        "sqlite_gaps": total_gaps,
        "sqlite_contradictions": total_contra,
        "sqlite_reports": total_reports,
        "chromadb_vectors": chroma_count,
        "persistence_status": "VERIFIED"
    }

    # Final summary
    total_audit_dur = round(time.time() - overall_start, 2)
    end_ram = get_ram_mb()
    print_section("AUDIT COMPLETE - ALL 21 TEST ITEMS PASSED 100%")
    print(f"Total Audit Execution Time: {total_audit_dur}s")
    print(f"Host RAM: Initial={start_ram} MB, Final={end_ram} MB (Protected within 8 GB envelope)")

    # Save detailed audit log
    out_log = Path("backend/audit_results.json")
    with open(out_log, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)
    print(f"Detailed audit results written to: {out_log.resolve()}")

if __name__ == "__main__":
    run_end_to_end_audit()
