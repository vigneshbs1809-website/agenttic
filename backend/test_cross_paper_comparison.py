import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import io
import time
import uuid
import asyncio
import pymupdf
import httpx
from httpx import ASGITransport

from backend.app.main import app
from backend.app.core.database import SessionLocal, init_db
from backend.app.models.entities import ResearchProject, ResearchPaper, PaperComparison
from backend.app.services.document_processing import document_processor

def build_pdf(title: str, sections_data: list) -> bytes:
    doc = pymupdf.open()
    current_page = doc.new_page(width=595, height=842)
    y = 50
    current_page.insert_text((50, y), title, fontsize=15, fontname="helv", color=(0, 0, 0))
    y += 35
    current_page.insert_text((50, y), "Academic Literature Intelligence Benchmark", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
    y += 35

    for sec_heading, sec_body in sections_data:
        if y > 680:
            current_page = doc.new_page(width=595, height=842)
            y = 50

        current_page.insert_text((50, y), sec_heading.upper(), fontsize=12, fontname="helv", color=(0, 0.2, 0.6))
        y += 20
        rect = pymupdf.Rect(50, y, 545, y + 140)
        current_page.insert_textbox(rect, sec_body, fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))
        y += 120

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

async def run_comparison_agent_tests():
    print("=" * 80)
    print("STARTING CROSS-PAPER COMPARISON AGENT VERIFICATION TESTS")
    print("=" * 80)
    init_db()

    pdf_dir = Path("backend/data/PDFs")
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # 1. Paper 1: Dense Multi-Agent Reinforcement Learning for Fleet Dispatch
    p1_title = "Centralized Value Factorization for Autonomous Multi-Agent Dispatch"
    p1_sections = [
        ("Abstract",
         "Decentralized coordination in dense fleets suffers from credit assignment failure. "
         "In this work, our objective is to propose CentralQ, a value-factorized multi-agent reinforcement learning algorithm. "
         "CentralQ achieves an 89.2% success rate and 28.4% latency reduction on the Fleet-Dispatch-Bench. "
         "However, coordination breaks down when communication packet loss exceeds 8%."),
        ("Introduction",
         "The bottleneck in urban fleet management arises from competitive reward maximization among independent agents. "
         "Motivated by monotonic value factorization, we introduce CentralQ to coordinate dispatching decisions. "
         "Our primary goal of this paper is to eliminate vehicle congestion in synchronized transit grids."),
        ("Methodology",
         "Our framework is based on monotonic value factorization using hypernetworks. "
         "The CentralQ algorithm computes centralized joint action-values while preserving decentralized policy execution. "
         "Data preprocessing consists of vehicle GPS coordinate normalization and demand matrix standardization."),
        ("Experiments",
         "Evaluated on the synthetic Fleet-Dispatch-Bench benchmark comprising 200 autonomous vehicles. "
         "The experimental setup utilized 2 NVIDIA RTX 3090 GPUs across 100 training epochs. "
         "Evaluation metrics include dispatch success rate, latency, queue length, and throughput."),
        ("Results",
         "Experimental results confirm that CentralQ achieved an 89.2% success rate and 28.4% latency reduction over QMIX. "
         "CentralQ outperformed independent DQN by a 2.5x speedup in convergence time."),
        ("Limitations",
         "A major limitation is that performance degrades sharply when inter-vehicle wireless packet loss exceeds 8%."),
        ("Conclusion",
         "In conclusion, centralized value factorization enables monotonic coordination in dense fleets. "
         "In future work, we plan to explore communication-free topological graph neural networks.")
    ]

    # 2. Paper 2: Sparse Graph Attention Routing for Dynamic Logistics
    p2_title = "Decentralized Sparse Graph Attention for Megacity Delivery Logistics"
    p2_sections = [
        ("Abstract",
         "Quadratic scaling in centralized routing algorithms precludes scaling beyond hundreds of logistics agents. "
         "In this work, our objective is to introduce RouteGAT, a decentralized sparse graph attention architecture. "
         "RouteGAT achieves an 84.6% delivery on-time rate and 31.2% fuel savings on the Urban-Logistics-1k benchmark. "
         "The policy maintains robust operation under wireless packet loss up to 18%."),
        ("Introduction",
         "The challenge of dynamic logistics routing requires scalable decentralized policy synthesis without central controllers. "
         "Motivated by localized spatial sparsity, we present RouteGAT. "
         "Our primary goal of this paper is to minimize delivery delays across complex megacity street networks."),
        ("Methodology",
         "Our framework is based on localized k-hop graph attention combined with temporal-difference policy updates. "
         "The RouteGAT algorithm routes delivery vehicles dynamically based on localized road network embeddings. "
         "Data preprocessing consists of road network graph Laplacian normalization and edge weight quantization."),
        ("Experiments",
         "Evaluated on the real-world Urban-Logistics-1k benchmark comprising 1,000 delivery couriers. "
         "The experimental setup used 4 NVIDIA A100 GPUs across 250 training epochs. "
         "Evaluation metrics include on-time rate, fuel savings, routing delay, and compute latency."),
        ("Results",
         "Experimental results demonstrate that RouteGAT achieved an 84.6% on-time delivery rate and 31.2% fuel savings. "
         "RouteGAT outperformed centralized genetic routing by a 4.1x speedup."),
        ("Limitations",
         "A key limitation is that routing efficiency degrades when road network graph topology changes dynamically during severe weather."),
        ("Conclusion",
         "In conclusion, decentralized sparse graph attention provides robust routing in megacity transit grids. "
         "In future work, we plan to incorporate stochastic weather forecasting into edge attention weights.")
    ]

    pdf1_bytes = build_pdf(p1_title, p1_sections)
    pdf2_bytes = build_pdf(p2_title, p2_sections)
    p1_path = pdf_dir / "test_comp_paper1.pdf"
    p2_path = pdf_dir / "test_comp_paper2.pdf"
    p1_path.write_bytes(pdf1_bytes)
    p2_path.write_bytes(pdf2_bytes)

    db = SessionLocal()
    # Create test research project
    test_proj = ResearchProject(
        title=f"Cross-Paper Comparison Study {uuid.uuid4().hex[:6]}",
        description="Testing Cross-Paper Comparison Agent",
        domain="Artificial Intelligence"
    )
    db.add(test_proj)
    db.commit()
    db.refresh(test_proj)
    project_id = test_proj.id

    # Ingest Paper 1
    doc1_id = f"test-p1-{uuid.uuid4().hex[:8]}"
    paper1 = await document_processor.process_pdf_document(
        db=db,
        doc_id=doc1_id,
        file_path=p1_path,
        original_filename="test_comp_paper1.pdf",
        file_size=len(pdf1_bytes),
        project_id=project_id
    )

    # Ingest Paper 2
    doc2_id = f"test-p2-{uuid.uuid4().hex[:8]}"
    paper2 = await document_processor.process_pdf_document(
        db=db,
        doc_id=doc2_id,
        file_path=p2_path,
        original_filename="test_comp_paper2.pdf",
        file_size=len(pdf2_bytes),
        project_id=project_id
    )
    print(f"[OK] Ingested Paper 1: '{paper1.title}' (ID: {doc1_id})")
    print(f"[OK] Ingested Paper 2: '{paper2.title}' (ID: {doc2_id})")
    db.close()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # TEST 1: Generate Cross-Paper Comparison (POST /api/comparison/compare)
        print("\n--- TEST 1: Generate Cross-Paper Comparison ---")
        res1 = await client.post("/api/comparison/compare", json={
            "paper_ids": [doc1_id, doc2_id],
            "project_id": project_id,
            "title": "CentralQ vs RouteGAT: Centralized vs Decentralized Fleet Coordination",
            "force_regenerate": True
        })
        assert res1.status_code == 200, f"Comparison failed: {res1.text}"
        data1 = res1.json()
        report = data1["report"]
        comp_id = data1["comparison_id"]
        print(f"Comparison ID: {comp_id}")
        print(f"Comparison Title: '{data1['comparison_title']}'")
        print(f"Total Papers Compared: {data1['total_papers_compared']}")
        assert len(report["compared_papers"]) == 2

        # TEST 2: Validate 13-Criteria Comparative Matrix
        print("\n--- TEST 2: Validate Comparative Matrix ---")
        matrix = report["matrix"]
        assert len(matrix) == 13, f"Expected 13 criteria rows, got {len(matrix)}"
        print(f"Matrix Rows Count: {len(matrix)}")
        for row in matrix:
            print(f"  Criterion: {row['criterion_label']} | Cells: {len(row['cells'])}")
            assert len(row["cells"]) == 2
            for cell in row["cells"]:
                assert cell["paper_id"] in [doc1_id, doc2_id]
                assert cell["value"]
                # Verify page citations
                if cell["evidence_quote"]:
                    assert cell["page_number"] is not None
        print("[PASS] Test 2: 13-criteria comparative matrix verified with page citations.")

        # TEST 3: Anti-Bias Comparability Assessment (Critical Requirement)
        print("\n--- TEST 3: Anti-Bias Comparability Assessment ---")
        comp_eval = report["comparability_assessment"]
        print(f"Verdict: {comp_eval['verdict']}")
        print(f"Dataset Comparability: {comp_eval['dataset_comparability']}")
        print(f"Warning / Caveat:\n  {comp_eval['warning_or_caveat']}")

        # Paper 1 used Fleet-Dispatch-Bench (200 vehicles), Paper 2 used Urban-Logistics-1k (1,000 couriers)
        # Even though Paper 1 reports 89.2% success while Paper 2 reports 84.6%, they are NOT directly comparable!
        assert comp_eval["is_directly_comparable"] is False
        assert "Different Datasets" in comp_eval["verdict"]
        assert "CANNOT be directly compared" in comp_eval["warning_or_caveat"]
        print("[PASS] Test 3: Anti-bias check strictly prevented false superiority claims across different datasets.")

        # TEST 4: Methodological Differences & Contradictions
        print("\n--- TEST 4: Methodological Differences & Contradictory Findings ---")
        diffs = report["methodological_differences"]
        assert len(diffs) == 2
        print(f"Paper 1 Paradigm: {diffs[0]['paradigm'][:60]}")
        print(f"Paper 2 Paradigm: {diffs[1]['paradigm'][:60]}")

        contradictions = report["contradictory_findings"]
        print(f"Contradictory Findings Count: {len(contradictions)}")
        assert len(contradictions) >= 1
        c = contradictions[0]
        print(f"Topic: {c['topic']}")
        print(f"  {c['paper_a_title']}: {c['finding_paper_a'][:80]} (Page {c['evidence_a']['page_number']})")
        print(f"  {c['paper_b_title']}: {c['finding_paper_b'][:80]} (Page {c['evidence_b']['page_number']})")
        # Notice Paper 1 degrades at 8% packet loss while Paper 2 maintains robust operation up to 18% packet loss!
        assert "8%" in c["finding_paper_a"]
        assert "18%" in c["finding_paper_b"] or "topology" in c["finding_paper_b"].lower()
        print("[PASS] Test 4: Contradictory degradation thresholds accurately identified with page citations.")

        # TEST 5: Underexplored Approaches & Comparative Summary Markdown
        print("\n--- TEST 5: Underexplored Approaches & Markdown Summary ---")
        underexplored = report["underexplored_approaches"]
        assert len(underexplored) >= 2
        print(f"Underexplored 1: {underexplored[0]['title']}")
        print(f"Underexplored 2: {underexplored[1]['title']}")

        summary_md = report["comparative_summary_markdown"]
        assert len(summary_md) > 500
        assert "# Cross-Paper Comparative Research Synthesis:" in summary_md
        assert "13-Criteria Head-to-Head Comparative Matrix" in summary_md
        assert "Comparability Assessment & Anti-Bias Verification" in summary_md
        print(f"Comparative Summary Generated ({len(summary_md)} characters).")
        print("[PASS] Test 5: Synthesis report and underexplored approaches verified.")

        # TEST 6: SQLite Persistence & Retrieval API Endpoints
        print("\n--- TEST 6: SQLite Persistence & Retrieval APIs ---")
        # Check SQLite record
        db = SessionLocal()
        saved_comp = db.query(PaperComparison).filter(PaperComparison.id == comp_id).first()
        assert saved_comp is not None
        assert saved_comp.project_id == project_id
        db.close()

        # GET /api/comparison/{id}
        res_get = await client.get(f"/api/comparison/{comp_id}")
        assert res_get.status_code == 200
        assert res_get.json()["comparison_id"] == comp_id

        # GET /api/comparison/{id}/markdown
        res_md = await client.get(f"/api/comparison/{comp_id}/markdown")
        assert res_md.status_code == 200
        assert res_md.headers["content-type"].startswith("text/markdown")

        # GET /api/comparison/project/{project_id}
        res_proj = await client.get(f"/api/comparison/project/{project_id}")
        assert res_proj.status_code == 200
        proj_comps = res_proj.json()
        assert len(proj_comps) >= 1
        assert proj_comps[0]["comparison_id"] == comp_id
        print(f"Listed Comparisons for Project: {len(proj_comps)} found.")
        print("[PASS] Test 6: Persistence in SQLite and all comparison endpoints verified.")

        # TEST 7: Input Validation (Must be between 2 and 5 papers)
        print("\n--- TEST 7: Input Validation (2 to 5 papers) ---")
        res_single = await client.post("/api/comparison/compare", json={
            "paper_ids": [doc1_id] # Only 1 paper
        })
        assert res_single.status_code == 422 or res_single.status_code == 400
        print("[PASS] Test 7: Validation prevents comparing fewer than 2 papers.")

        # Clean up temp test files
        if p1_path.exists():
            p1_path.unlink()
        if p2_path.exists():
            p2_path.unlink()

    print("\n" + "=" * 80)
    print("ALL CROSS-PAPER COMPARISON AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_comparison_agent_tests())

