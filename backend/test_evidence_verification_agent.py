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
from backend.app.models.entities import ResearchProject, ResearchPaper, VerificationResult
from backend.app.services.document_processing import document_processor

def build_pdf(title: str, sections_data: list) -> bytes:
    doc = pymupdf.open()
    current_page = doc.new_page(width=595, height=842)
    y = 50
    current_page.insert_text((50, y), title, fontsize=15, fontname="helv", color=(0, 0, 0))
    y += 35
    current_page.insert_text((50, y), "Evidence Verification Intelligence Benchmark Series", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
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

async def run_evidence_verification_tests():
    print("=" * 80)
    print("STARTING EVIDENCE VERIFICATION AGENT INTEGRATION TESTS")
    print("=" * 80)
    init_db()

    pdf_dir = Path("backend/data/PDFs")
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # Prepare ground-truth test academic paper
    p_title = "Centralized Value Factorization for Autonomous Multi-Agent Dispatch"
    p_sections = [
        ("Abstract",
         "Decentralized coordination in dense fleets suffers from credit assignment failure. "
         "In this work, our objective is to propose CentralQ, a value-factorized multi-agent reinforcement learning algorithm. "
         "CentralQ achieves an 89.2% success rate and 28.4% latency reduction on the Fleet-Dispatch-Bench."),
        ("Introduction",
         "Credit assignment failure in dense vehicle fleets prevents stable policy convergence. "
         "We address this by decomposing team reward signals into individual monotonic agent utilities."),
        ("Methodology",
         "Our methodology employs CentralQ with hypernetwork value mixing and AdamW gradient descent. "
         "We formulate decentralized observation histories into permutation-invariant agent embeddings."),
        ("Experiments",
         "Evaluated on Fleet-Dispatch-Bench across 500 stochastic scenarios. "
         "Metrics comprise Success Rate, Latency, and Throughput."),
        ("Results",
         "Experimental results demonstrate that CentralQ achieves an 89.2% success rate and 28.4% latency reduction on the Fleet-Dispatch-Bench, outperforming independent Q-learning by 14.8%."),
        ("Limitations",
         "A major limitation is that joint value monotonicity restricts expressiveness in asymmetric non-monotonic payoff games."),
        ("Conclusion",
         "CentralQ demonstrates scalable coordination in large vehicle fleets with verified convergence.")
    ]

    p_path = pdf_dir / "test_verification_paper.pdf"
    p_path.write_bytes(build_pdf(p_title, p_sections))

    db = SessionLocal()
    project = None
    try:
        # Create Research Project
        project = ResearchProject(
            title=f"Verification Benchmark Project {uuid.uuid4().hex[:6]}",
            description="Testing Evidence Verification Agent on supported and deliberately unsupported claims",
            domain="Multi-Agent Systems"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"[1/7] Created Research Project: '{project.title}' (ID: {project.id})")

        # Ingest Paper
        paper = await document_processor.process_pdf_document(
            db=db,
            doc_id=f"test-ver-p-{uuid.uuid4().hex[:8]}",
            file_path=p_path,
            original_filename="test_verification_paper.pdf",
            file_size=len(p_path.read_bytes()),
            project_id=project.id
        )
        print(f"[2/7] Ingested ground-truth paper: '{paper.title}' (ID: {paper.id})")

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # --------------------------------------------------------------
            # TEST 1: Directly Supported Claim
            # --------------------------------------------------------------
            print("\n[3/7] Testing Supported Claim Verification...")
            claim_supported = {
                "claim_text": "CentralQ achieves an 89.2% success rate and 28.4% latency reduction on the Fleet-Dispatch-Bench.",
                "paper_id": paper.id
            }
            res_supp = await client.post("/api/verification/verify-claim", json=claim_supported)
            assert res_supp.status_code == 200, f"Supported check failed: {res_supp.text}"
            data_supp = res_supp.json()

            print(f"-> Claim: \"{data_supp['claim_text']}\"")
            print(f"-> Status: {data_supp['verification_status']}")
            print(f"-> Evidence: \"{data_supp['original_evidence'][:90]}...\" (Page {data_supp['page_number']})")
            print(f"-> Explanation: {data_supp['explanation']}")
            print(f"-> Is Verified Finding: {data_supp['is_verified_finding']}")

            assert data_supp["verification_status"] == "Supported"
            assert data_supp["is_verified_finding"] is True
            assert data_supp["page_number"] is not None
            assert "89.2%" in data_supp["original_evidence"]
            assert "28.4%" in data_supp["original_evidence"]

            # --------------------------------------------------------------
            # TEST 2: Contradicted Claim (Fabricated Metric)
            # --------------------------------------------------------------
            print("\n[4/7] Testing Contradicted Claim (Fabricated Metric 99.4% vs Actual 89.2%)...")
            claim_contradicted_metric = {
                "claim_text": "CentralQ achieves a 99.4% success rate on the Fleet-Dispatch-Bench.",
                "paper_id": paper.id
            }
            res_contra_m = await client.post("/api/verification/verify-claim", json=claim_contradicted_metric)
            assert res_contra_m.status_code == 200
            data_contra_m = res_contra_m.json()

            print(f"-> Claim: \"{data_contra_m['claim_text']}\"")
            print(f"-> Status: {data_contra_m['verification_status']}")
            print(f"-> Explanation: {data_contra_m['explanation']}")
            print(f"-> Is Verified Finding: {data_contra_m['is_verified_finding']}")

            assert data_contra_m["verification_status"] == "Contradicted"
            assert data_contra_m["is_verified_finding"] is False
            assert "89.2" in data_contra_m["explanation"] or "99.4" in data_contra_m["explanation"]

            # --------------------------------------------------------------
            # TEST 3: Contradicted Claim (Directional Inversion)
            # --------------------------------------------------------------
            print("\n[5/7] Testing Contradicted Claim (Direction Inversion: increases latency)...")
            claim_contra_dir = {
                "claim_text": "CentralQ increases latency on the Fleet-Dispatch-Bench.",
                "paper_id": paper.id
            }
            res_contra_d = await client.post("/api/verification/verify-claim", json=claim_contra_dir)
            assert res_contra_d.status_code == 200
            data_contra_d = res_contra_d.json()

            print(f"-> Claim: \"{data_contra_d['claim_text']}\"")
            print(f"-> Status: {data_contra_d['verification_status']}")
            print(f"-> Explanation: {data_contra_d['explanation']}")
            print(f"-> Is Verified Finding: {data_contra_d['is_verified_finding']}")

            assert data_contra_d["verification_status"] == "Contradicted"
            assert data_contra_d["is_verified_finding"] is False

            # --------------------------------------------------------------
            # TEST 4: Insufficient Evidence Claim (No basis in paper)
            # --------------------------------------------------------------
            print("\n[6/7] Testing Insufficient Evidence Claim (Quantum annealing Josephson junctions)...")
            claim_insufficient = {
                "claim_text": "CentralQ utilizes superconducting quantum annealing flux qubits to optimize Josephson junction coupling.",
                "paper_id": paper.id
            }
            res_insuf = await client.post("/api/verification/verify-claim", json=claim_insufficient)
            assert res_insuf.status_code == 200
            data_insuf = res_insuf.json()

            print(f"-> Claim: \"{data_insuf['claim_text']}\"")
            print(f"-> Status: {data_insuf['verification_status']}")
            print(f"-> Explanation: {data_insuf['explanation']}")
            print(f"-> Is Verified Finding: {data_insuf['is_verified_finding']}")

            assert data_insuf["verification_status"] == "Insufficient Evidence"
            assert data_insuf["is_verified_finding"] is False

            # --------------------------------------------------------------
            # TEST 5: Batch Verification & SQLite History
            # --------------------------------------------------------------
            print("\n[7/7] Testing Batch Verification API & SQLite History Endpoint...")
            batch_req = {
                "claims": [
                    {"claim_text": "CentralQ achieves an 89.2% success rate on the Fleet-Dispatch-Bench.", "paper_id": paper.id},
                    {"claim_text": "CentralQ attains 99.4% accuracy.", "paper_id": paper.id},
                    {"claim_text": "CentralQ uses hypernetwork value mixing.", "paper_id": paper.id}
                ]
            }
            res_batch = await client.post("/api/verification/batch", json=batch_req)
            assert res_batch.status_code == 200
            data_batch = res_batch.json()

            print(f"-> Total Claims Batch Processed: {data_batch['total_claims']}")
            print(f"-> Verified: {data_batch['verified_count']}, Contradicted: {data_batch['contradicted_count']}")
            assert data_batch["total_claims"] == 3
            assert data_batch["verified_count"] >= 2
            assert data_batch["contradicted_count"] >= 1

            # Test History Endpoint (GET /api/verification/history)
            res_hist = await client.get(f"/api/verification/history?paper_id={paper.id}")
            assert res_hist.status_code == 200
            history_list = res_hist.json()
            print(f"-> Stored Verification Records in SQLite: {len(history_list)}")
            assert len(history_list) >= 4

        print("\n" + "=" * 80)
        print("ALL EVIDENCE VERIFICATION AGENT TESTS PASSED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        # Cleanup
        try:
            if project:
                p = db.query(ResearchProject).filter(ResearchProject.id == project.id).first()
                if p:
                    db.delete(p)
                    db.commit()
            if p_path.exists():
                p_path.unlink()
        except Exception as e:
            print(f"Cleanup error: {e}")
        db.close()

if __name__ == "__main__":
    asyncio.run(run_evidence_verification_tests())

