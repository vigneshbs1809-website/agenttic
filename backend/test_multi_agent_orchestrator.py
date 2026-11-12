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
from backend.app.models.entities import ResearchProject, ResearchPaper, GeneratedReport
from backend.app.services.document_processing import document_processor

def build_pdf(title: str, sections_data: list) -> bytes:
    """Builds a real multi-page academic PDF with PyMuPDF."""
    doc = pymupdf.open()
    current_page = doc.new_page(width=595, height=842)
    y = 50
    current_page.insert_text((50, y), title, fontsize=15, fontname="helv", color=(0, 0, 0))
    y += 35
    current_page.insert_text((50, y), "Journal of Autonomous Systems & Multi-Agent Intelligence", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
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

async def run_orchestrator_integration_tests():
    print("=" * 80)
    print("STARTING MULTI-AGENT ORCHESTRATOR INTEGRATION TESTS")
    print("=" * 80)
    init_db()

    pdf_dir = Path("backend/data/PDFs")
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------------------
    # 1. Prepare Three Real Academic PDFs
    # --------------------------------------------------------------------------
    p1_title = "Centralized Value Factorization for Autonomous Multi-Agent Dispatch"
    p1_sections = [
        ("Abstract",
         "Decentralized fleet routing suffers from credit assignment breakdown in crowded depots. "
         "We propose CentralQ, a value-factorized multi-agent reinforcement learning algorithm with monotonic mixing. "
         "CentralQ achieves an 89.2% success rate and 28.4% latency reduction on the Fleet-Dispatch-Bench."),
        ("Introduction",
         "Autonomous multi-robot systems require coordinated task allocation. Prior independent Q-learning converges slowly. "
         "Our central objective is to formulate joint action-value factorization while preserving decentralized execution."),
        ("Methodology",
         "CentralQ enforces joint action-value monotonicity through a feed-forward mixing network conditioned on state observations. "
         "Individual agents select greedy actions with parameter-shared actor networks."),
        ("Experiments",
         "Evaluated on Fleet-Dispatch-Bench with 50 autonomous robots in 2D grid environments over 1,000,000 timesteps."),
        ("Results",
         "CentralQ achieves an 89.2% task success rate, outperforming QMIX by 6.3% and independent Q-learning by 14.8%. "
         "Latency is reduced by 28.4%."),
        ("Limitations",
         "A notable limitation is that our method incurs quadratic communication overhead O(N^2) as the number of agents grows past 100."),
        ("Future Work",
         "Future research must investigate hierarchical sparse communication topologies to scale beyond 500 agents."),
        ("References",
         "[1] Rashid et al., QMIX: Monotonic Value-Function Factorisation for Deep Multi-Agent Reinforcement Learning, ICML 2018.")
    ]

    p2_title = "Hierarchical Graph Attention for Scalable Fleet Routing"
    p2_sections = [
        ("Abstract",
         "Dense spatial logistics require dynamic spatial graph modeling. We present H-GAT, a hierarchical graph attention network. "
         "H-GAT scales effectively up to 500 agents, achieving an 84.6% dispatch success rate on GridWorld-100k."),
        ("Introduction",
         "Traditional value factorization algorithms suffer from quadratic communication overhead. "
         "We propose spatial attention to restrict communication strictly to local K-hop spatial neighborhoods."),
        ("Methodology",
         "H-GAT builds dynamic spatial graphs using Delaunay triangulation. Layered multi-head attention computes node embeddings."),
        ("Experiments",
         "Simulated on GridWorld-100k with 200 to 500 delivery drones over 500,000 execution episodes."),
        ("Results",
         "H-GAT sustains an 84.6% dispatch success rate and demonstrates linear O(N) communication scaling. "
         "However, local message pruning slightly reduces coordination precision compared to full centralized mixing."),
        ("Limitations",
         "H-GAT requires accurate spatial coordinate telemetry and degrades under asynchronous sensor dropouts."),
        ("Future Work",
         "Extending H-GAT to handle temporal packet drops and out-of-order state updates in physical GPS-denied environments."),
        ("References",
         "[1] Veličković et al., Graph Attention Networks, ICLR 2018.\n"
         "[2] Centralized Value Factorization for Autonomous Multi-Agent Dispatch, Journal of Autonomous Systems 2024.")
    ]

    p3_title = "Diffusion-Based Trajectory Optimization under Partial Observability"
    p3_sections = [
        ("Abstract",
         "Non-stationary obstacles degrade deterministic multi-agent collision avoidance. We introduce DiffPath, a conditional diffusion model "
         "generating safe trajectory distributions. DiffPath achieves a 91.5% zero-collision navigation score on NavObs-Bench."),
        ("Introduction",
         "Trajectory planning under occluded sensor readings requires probabilistic trajectory forecasting rather than deterministic point estimates."),
        ("Methodology",
         "DiffPath formulates path planning as reverse diffusion conditioned on past LiDAR scans and target waypoints using a 1D U-Net."),
        ("Experiments",
         "Tested on NavObs-Bench with 30 mobile automated guided vehicles navigating narrow industrial warehouses."),
        ("Results",
         "DiffPath achieves a 91.5% zero-collision navigation score and outperforms classical MPC trajectories by 18.2% in dense occlusions."),
        ("Limitations",
         "Reverse diffusion inference requires 12 sampling steps, incurring a 45ms per-step inference latency bottleneck."),
        ("Future Work",
         "Investigating few-step distillation (e.g. consistency models) to achieve sub-10ms real-time robotic deployment."),
        ("References",
         "[1] Ho et al., Denoising Diffusion Probabilistic Models, NeurIPS 2020.\n"
         "[2] Centralized Value Factorization for Autonomous Multi-Agent Dispatch, Journal of Autonomous Systems 2024.")
    ]

    # --------------------------------------------------------------------------
    # 2. Setup Test Project & Ingest PDFs
    # --------------------------------------------------------------------------
    with SessionLocal() as db:
        test_project_id = str(uuid.uuid4())
        project = ResearchProject(
            id=test_project_id,
            title=f"Multi-Agent Orchestrator Test Project {test_project_id[:6]}",
            domain="Autonomous Multi-Agent Routing & Coordination",
            description="Testing end-to-end multi-agent orchestration across 8 specialized academic intelligence agents."
        )
        db.add(project)
        db.commit()

        print(f"\n[1/6] Created Project: '{project.title}' (ID: {test_project_id})")

        papers = []
        paper_ids = []
        for title, sec_data in [(p1_title, p1_sections), (p2_title, p2_sections), (p3_title, p3_sections)]:
            pdf_bytes = build_pdf(title, sec_data)
            doc_id = f"test-orch-{uuid.uuid4().hex[:8]}"
            pdf_path = pdf_dir / f"{doc_id}.pdf"
            pdf_path.write_bytes(pdf_bytes)

            paper = await document_processor.process_pdf_document(
                db=db,
                doc_id=doc_id,
                file_path=pdf_path,
                original_filename=f"{title[:30]}.pdf",
                file_size=len(pdf_bytes),
                project_id=test_project_id
            )
            papers.append(paper)
            paper_ids.append(paper.id)
            print(f"-> Ingested Real Research PDF: '{paper.title}' (ID: {paper.id})")

    # --------------------------------------------------------------------------
    # 3. Test Full Multi-Agent Workflow Execution via Orchestrator API
    # --------------------------------------------------------------------------
    print("\n[2/6] Triggering Complete Multi-Agent Workflow Execution...")
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        run_payload = {
            "project_id": test_project_id,
            "topic": "Autonomous Multi-Agent Routing and Coordination",
            "keywords": ["reinforcement learning", "graph attention", "diffusion trajectory"],
            "paper_ids": paper_ids,
            "force_restart": False
        }
        res_run = await client.post("/api/orchestrator/run", json=run_payload)
        assert res_run.status_code == 202, f"Failed starting workflow: {res_run.text}"
        data_run = res_run.json()
        workflow_id = data_run["workflow_id"]
        print(f"-> Workflow Launched! Handle: {workflow_id}")
        print(f"-> Initial Status: {data_run['status']} (Stages: {data_run['total_stages']})")

        # ----------------------------------------------------------------------
        # 4. Monitor Sequential Execution across all 9 Stages
        # ----------------------------------------------------------------------
        print("\n[3/6] Polling Real-Time Stage Progress (Sequential Execution across 8 Agents)...")
        max_wait_seconds = 180
        start_poll = time.time()
        final_status = None

        while time.time() - start_poll < max_wait_seconds:
            await asyncio.sleep(2.0)
            res_status = await client.get(f"/api/orchestrator/status/{workflow_id}")
            assert res_status.status_code == 200
            final_status = res_status.json()

            progress = final_status["progress_percent"]
            curr_stage = final_status.get("current_stage") or "Done"
            status_val = final_status["status"]

            print(f"-> Progress: {progress}% | Current Stage: {curr_stage} | Workflow Status: {status_val}")

            if status_val in ["completed", "failed", "cancelled"]:
                break

        print("\n[4/6] Verifying Workflow Completion & Usable Deliverables...")
        assert final_status is not None
        assert final_status["status"] == "completed", f"Workflow did not complete: {final_status.get('logs')}"
        assert final_status["progress_percent"] == 100.0, f"Expected 100% progress, got {final_status['progress_percent']}"
        assert final_status["completed_stages"] == final_status["total_stages"]

        # Verify all individual stages executed
        for st in final_status["stages"]:
            print(f"  * Stage '{st['stage_name']}': {st['status'].upper()} ({st['duration_ms']} ms) - {st['output_summary']}")
            assert st["status"] in ["completed", "skipped"]

        # Verify Final Research Dossier
        assert final_status["final_report_id"] is not None
        assert final_status["final_report_markdown"] is not None
        report_md = final_status["final_report_markdown"]
        print(f"-> Final Dossier Generated: {len(report_md)} characters")
        assert "Autonomous Literature Intelligence Dossier" in report_md
        assert "Cross-Paper Comparative Matrix" in report_md
        assert "Discovered Research Gaps" in report_md
        assert "Evidence Verification Ledger" in report_md

        # ----------------------------------------------------------------------
        # 5. Test Resumption Mechanism (Reuse Completed Stages)
        # ----------------------------------------------------------------------
        print("\n[5/6] Testing Workflow Resumption (Idempotency & Reusing Intermediate Outputs)...")
        res_resume = await client.post(f"/api/orchestrator/resume/{workflow_id}")
        assert res_resume.status_code == 200
        resume_data = res_resume.json()
        print(f"-> Resumed workflow: Status={resume_data['status']}, Progress={resume_data['progress_percent']}%")
        assert resume_data["progress_percent"] == 100.0

        # ----------------------------------------------------------------------
        # 6. Test Individual Agent Execution Endpoint
        # ----------------------------------------------------------------------
        print("\n[6/6] Testing Individual Stage Execution (POST /api/orchestrator/run-stage)...")
        ind_payload = {
            "project_id": test_project_id,
            "stage_id": "gap_discovery",
            "force": False
        }
        res_ind = await client.post("/api/orchestrator/run-stage", json=ind_payload)
        assert res_ind.status_code == 200
        ind_data = res_ind.json()
        print(f"-> Individual Stage Result: {ind_data['stage_id']} -> {ind_data['status']} ({ind_data['duration_ms']} ms)")
        assert ind_data["status"] == "completed"
        assert "Discovered" in ind_data["summary"]

    print("\n" + "=" * 80)
    print("ALL MULTI-AGENT ORCHESTRATOR INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_orchestrator_integration_tests())
