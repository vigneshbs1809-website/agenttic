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
from backend.app.models.entities import ResearchProject, ResearchPaper, ResearchGap, GapEvidence
from backend.app.services.document_processing import document_processor

def build_pdf(title: str, sections_data: list) -> bytes:
    doc = pymupdf.open()
    current_page = doc.new_page(width=595, height=842)
    y = 50
    current_page.insert_text((50, y), title, fontsize=15, fontname="helv", color=(0, 0, 0))
    y += 35
    current_page.insert_text((50, y), "Research Gap Intelligence Benchmark Series", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
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

async def run_research_gap_agent_tests():
    print("=" * 80)
    print("STARTING RESEARCH GAP DISCOVERY AGENT INTEGRATION TESTS")
    print("=" * 80)
    init_db()

    pdf_dir = Path("backend/data/PDFs")
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # 1. Paper 1: Centralized Dispatch
    p1_title = "Centralized Value Factorization for Autonomous Multi-Agent Dispatch"
    p1_sections = [
        ("Abstract",
         "Decentralized coordination in dense fleets suffers from credit assignment failure. "
         "In this work, our objective is to propose CentralQ, a value-factorized multi-agent reinforcement learning algorithm. "
         "CentralQ achieves an 89.2% success rate and 28.4% latency reduction on the Fleet-Dispatch-Bench."),
        ("Introduction",
         "Credit assignment failure in dense vehicle fleets prevents stable policy convergence. "
         "We address this by decomposing team reward signals into individual monotonic agent utilities."),
        ("Methodology",
         "Our methodology employs CentralQ with hypernetwork value mixing and AdamW gradient descent. "
         "We utilize Cross-Entropy loss combined with spectral regularization to preserve multi-hop topology."),
        ("Experiments",
         "Evaluated on the synthetic Fleet-Dispatch-Bench comprising 500 delivery vehicles."),
        ("Results",
         "CentralQ achieves 89.2% success rate, outperforming independent Q-learning by 14.8%."),
        ("Limitations",
         "A major author-stated limitation is that joint value monotonicity restricts expressiveness in asymmetric non-monotonic payoff games. "
         "Furthermore, the model fails to generalize when evaluated under severe weather disruptions."),
        ("Future Work",
         "In future iterations, we plan to investigate non-monotonic value decomposition and stochastic weather forecasting in edge weights.")
    ]

    # 2. Paper 2: Hierarchical Logistics
    p2_title = "Hierarchical Topological Clustering for Megacity Autonomous Logistics"
    p2_sections = [
        ("Abstract",
         "Scaling coordination to thousands of delivery agents introduces severe communication overhead. "
         "We propose HierarchicalQ, using spatial clustering to group agents into topological subgraphs. "
         "HierarchicalQ reduces communication overhead by 68% on the Fleet-Dispatch-Bench."),
        ("Introduction",
         "Centralized architectures incur quadratic communication latency in megacities. "
         "Our objective is to design hierarchical sub-networks to partition large dispatch zones."),
        ("Methodology",
         "HierarchicalQ incorporates dynamic topological graph partitioning with AdamW optimization."),
        ("Experiments",
         "Evaluated on Fleet-Dispatch-Bench and Urban-Grid-50k."),
        ("Results",
         "HierarchicalQ attains 93.6% success rate and reduces communication latency by 68%."),
        ("Limitations",
         "A key limitation is that sub-cluster repartitioning incurs high latency when transit network graph topology changes dynamically during peak rush hours."),
        ("Future Work",
         "Future research will explore predictive edge partitioning to anticipate rush-hour traffic blockages.")
    ]

    # 3. Paper 3: Neural Diffusion for Continuous Control
    p3_title = "Continuous Graph Neural Diffusion for Multi-Agent Path Planning"
    p3_sections = [
        ("Abstract",
         "Continuous-time trajectory generation requires scalable differential equations on spatial graphs. "
         "We introduce DiffPlan, a continuous neural diffusion solver for multi-agent trajectory planning."),
        ("Introduction",
         "Discrete message passing suffers from oversmoothing when trajectories span long horizons."),
        ("Methodology",
         "DiffPlan leverages neural ordinary differential equations (ODEs) with adaptive Runge-Kutta stepping."),
        ("Experiments",
         "We benchmark DiffPlan on Fleet-Dispatch-Bench and Continuous-Grid-100k."),
        ("Results",
         "DiffPlan reduces trajectory collision rates by 42.1% compared to discrete A* baselines."),
        ("Limitations",
         "Continuous ODE integration exhibits high inference latency on large macromolecules and high-density agent clusters, restricting real-time deployment."),
        ("Future Work",
         "We intend to investigate lightweight discrete neural ODE approximations for embedded microcontrollers.")
    ]

    p1_path = pdf_dir / "test_gap_paper1.pdf"
    p2_path = pdf_dir / "test_gap_paper2.pdf"
    p3_path = pdf_dir / "test_gap_paper3.pdf"

    p1_path.write_bytes(build_pdf(p1_title, p1_sections))
    p2_path.write_bytes(build_pdf(p2_title, p2_sections))
    p3_path.write_bytes(build_pdf(p3_title, p3_sections))

    db = SessionLocal()
    project = None
    try:
        # 1. Create Research Project
        project = ResearchProject(
            title=f"Autonomous Logistics Gap Study {uuid.uuid4().hex[:6]}",
            description="Evaluating Research Gap Discovery Agent across 3 multi-agent literature papers",
            domain="Multi-Agent Systems"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"[1/7] Created Research Project: '{project.title}' (ID: {project.id})")

        # 2. Ingest 3 real academic test papers
        paper1 = await document_processor.process_pdf_document(
            db=db,
            doc_id=f"test-gap-p1-{uuid.uuid4().hex[:8]}",
            file_path=p1_path,
            original_filename="test_gap_paper1.pdf",
            file_size=len(p1_path.read_bytes()),
            project_id=project.id
        )
        paper2 = await document_processor.process_pdf_document(
            db=db,
            doc_id=f"test-gap-p2-{uuid.uuid4().hex[:8]}",
            file_path=p2_path,
            original_filename="test_gap_paper2.pdf",
            file_size=len(p2_path.read_bytes()),
            project_id=project.id
        )
        paper3 = await document_processor.process_pdf_document(
            db=db,
            doc_id=f"test-gap-p3-{uuid.uuid4().hex[:8]}",
            file_path=p3_path,
            original_filename="test_gap_paper3.pdf",
            file_size=len(p3_path.read_bytes()),
            project_id=project.id
        )
        print(f"[2/7] Ingested 3 test papers: '{paper1.title}', '{paper2.title}', '{paper3.title}'")

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 3. Test Gap Discovery Endpoint (POST /api/gaps/discover/{project_id})
            print("\n[3/7] Testing Gap Discovery API (POST /api/gaps/discover/{project_id})...")
            req_body = {
                "include_explicit": True,
                "include_implicit": True,
                "force_rediscover": True
            }
            res_discover = await client.post(f"/api/gaps/discover/{project.id}", json=req_body)
            assert res_discover.status_code == 200, f"Discovery failed: {res_discover.text}"
            data = res_discover.json()

            print(f"-> Total Gaps Found: {data['total_gaps_found']}")
            print(f"-> Explicit Gaps: {data['explicit_gaps_count']}")
            print(f"-> Implicit Gaps: {data['implicit_gaps_count']}")
            print(f"-> Categories Breakdown: {data['categories_breakdown']}")
            print(f"-> Disclaimer present: {data['disclaimer'][:80]}...")

            assert data["total_gaps_found"] >= 5, "Expected at least 5 research gaps across 3 papers"
            assert data["explicit_gaps_count"] >= 1, "Expected at least 1 explicit gap"
            assert data["implicit_gaps_count"] >= 1, "Expected at least 1 implicit gap"

            # 4. Verify Approach A (Explicit Gaps) vs Approach B (Implicit Gaps)
            print("\n[4/7] Verifying Approach A (Explicit) vs Approach B (Implicit)...")
            gaps = data["gaps"]
            explicit_gaps = [g for g in gaps if g["identification_method"] == "explicit_author_stated"]
            implicit_gaps = [g for g in gaps if g["identification_method"] == "implicit_system_inferred"]

            print(f"-> Found {len(explicit_gaps)} explicit author-stated gaps:")
            for eg in explicit_gaps[:2]:
                print(f"   * [{eg['gap_type'].upper()}] {eg['title']}")
                print(f"     Passage: \"{eg['evidences'][0]['quote_or_excerpt'][:90]}...\" (Page {eg['evidences'][0]['page_number']})")
                assert eg["evidences"][0]["page_number"] is not None

            print(f"-> Found {len(implicit_gaps)} implicit system-inferred gaps:")
            for ig in implicit_gaps[:3]:
                print(f"   * [{ig['gap_type'].upper()}] {ig['title']}")
                print(f"     Supporting Papers: {ig['supporting_papers_count']}")
                assert ig["supporting_papers_count"] >= 1

            # 5. Verify Fields & Transparent Confidence Scoring
            print("\n[5/7] Verifying Gap Fields, Confidence Breakdown, and Counter-Evidence...")
            sample_gap = gaps[0]
            required_fields = [
                "id", "title", "gap_type", "description", "identification_method",
                "supporting_papers", "evidences", "confidence_score", "confidence_justification",
                "suggested_direction", "corpus_scope", "status"
            ]
            for field in required_fields:
                assert field in sample_gap, f"Missing required field: {field}"

            print(f"-> Sample Gap: '{sample_gap['title']}'")
            print(f"-> Confidence Score: {sample_gap['confidence_score']} (0.0 to 1.0 scale)")
            print(f"-> Confidence Justification: {sample_gap['confidence_justification']}")
            print(f"-> Suggested Direction: {sample_gap['suggested_direction'][:100]}...")
            print(f"-> Corpus Scope: {sample_gap['corpus_scope']}")

            assert 0.10 <= sample_gap["confidence_score"] <= 0.95
            assert "heuristic" in sample_gap["confidence_justification"].lower()
            assert "probability" in sample_gap["confidence_justification"].lower() or "not a statistically validated" in sample_gap["confidence_justification"].lower()

            # 6. Test Filtering Endpoints (GET /api/gaps/project/{project_id})
            print("\n[6/7] Testing Gap Filtering APIs (GET /api/gaps/project/{id}?gap_type=...)...")
            res_filtered = await client.get(f"/api/gaps/project/{project.id}?identification_method=explicit_author_stated")
            assert res_filtered.status_code == 200
            filtered_data = res_filtered.json()
            print(f"-> Explicitly filtered gaps count: {filtered_data['total_gaps_found']}")
            for g in filtered_data["gaps"]:
                assert g["identification_method"] == "explicit_author_stated"

            # 7. Test Gap Update Endpoint (PUT /api/gaps/{gap_id})
            print("\n[7/7] Testing Gap Update API (PUT /api/gaps/{gap_id})...")
            target_gap_id = sample_gap["id"]
            update_payload = {
                "status": "verified",
                "suggested_direction": "Execute high-density benchmark validation across 1,000 physical robotic couriers."
            }
            res_update = await client.put(f"/api/gaps/{target_gap_id}", json=update_payload)
            assert res_update.status_code == 200, f"Update failed: {res_update.text}"
            updated_gap = res_update.json()
            assert updated_gap["status"] == "verified"
            assert "1,000 physical robotic couriers" in updated_gap["suggested_direction"]
            print(f"-> Gap successfully updated: ID={target_gap_id}, Status='{updated_gap['status']}'")

        print("\n" + "=" * 80)
        print("ALL RESEARCH GAP DISCOVERY AGENT TESTS PASSED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        # Cleanup
        try:
            if project:
                p = db.query(ResearchProject).filter(ResearchProject.id == project.id).first()
                if p:
                    db.delete(p)
                    db.commit()
            if p1_path.exists():
                p1_path.unlink()
            if p2_path.exists():
                p2_path.unlink()
            if p3_path.exists():
                p3_path.unlink()
        except Exception as e:
            print(f"Cleanup error: {e}")
        db.close()

if __name__ == "__main__":
    asyncio.run(run_research_gap_agent_tests())

