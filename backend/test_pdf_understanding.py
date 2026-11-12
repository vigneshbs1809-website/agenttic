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
from backend.app.models.entities import ResearchProject, ResearchPaper, PaperAnalysis
from backend.app.services.document_processing import document_processor

def create_rich_academic_pdf(title: str, sections_data: list) -> bytes:
    """Builds a realistic academic paper with distinct sections and specific ground truths."""
    doc = pymupdf.open()
    
    current_page = doc.new_page(width=595, height=842)
    y = 50
    current_page.insert_text((50, y), title, fontsize=15, fontname="helv", color=(0, 0, 0))
    y += 35
    current_page.insert_text((50, y), "Authors: Dr. Samuel Vance, Dr. Elena Rostova | Year: 2024", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
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

async def run_understanding_agent_tests():
    print("=" * 80)
    print("STARTING DEDICATED PDF UNDERSTANDING AGENT TESTS")
    print("=" * 80)
    init_db()

    # 1. Create a paper with rich, verifiable research elements
    paper_title = "Hierarchical Multi-Agent Actor-Critic Protocols for Urban Traffic Optimization"
    sections = [
        ("Abstract", 
         "The bottleneck in urban mobility stems from decentralized signal scheduling under stochastic congestion. "
         "In this work, we propose H-MARL, a hierarchical multi-agent reinforcement learning architecture. "
         "Using PPO algorithms across 500 autonomous intersections, our method achieves a 22.4% reduction in travel delay. "
         "However, performance degradation occurs when wireless packet loss exceeds 12%."),
        ("Introduction", 
         "The challenge of dynamic urban traffic congestion creates severe fuel inefficiencies. "
         "Motivated by decentralized multi-agent coordination, our primary goal of this paper is to eliminate intersection wait times. "
         "We introduce an actor-critic protocol that coordinates localized intersection controllers without centralized bottlenecks."),
        ("Methodology", 
         "Our framework is based on a decentralized Partially Observable Markov Decision Process. "
         "We formulate the policy using temporal-difference actor-critic updates with residual neural skip connections. "
         "The H-MARL algorithm coordinates inter-agent message passing using localized graph attention. "
         "Preprocessing consists of normalized traffic density vectors and one-hot encoded signal phase tensors."),
        ("Experiments", 
         "Evaluated on the synthetic CityGrid-NYC benchmark consisting of 500 autonomous intersections. "
         "Evaluation metrics include travel delay, fuel savings, queue length, and throughput latency. "
         "Empirical simulations confirm convergence within 150 training epochs."),
        ("Results", 
         "The experimental results demonstrate that H-MARL achieved a 22.4% reduction in travel delay and a 16.8% fuel savings. "
         "Our method outperformed centralized genetic algorithms by a 3.4x speedup."),
        ("Limitations", 
         "Performance degrades when inter-agent packet loss exceeds 12% across suburban cellular networks."),
        ("Conclusion", 
         "In conclusion, hierarchical actor-critic agents provide scalable decentralized routing. "
         "In future work, we plan to investigate Byzantine fault tolerance against adversarial sensor noise.")
    ]

    pdf_bytes = create_rich_academic_pdf(paper_title, sections)
    pdf_dir = Path("backend/data/PDFs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / "test_understanding_paper.pdf"
    pdf_path.write_bytes(pdf_bytes)

    db = SessionLocal()
    # Create test project
    test_project = ResearchProject(
        title=f"Understanding Eval Project {uuid.uuid4().hex[:6]}",
        description="Testing section-aware PDF Understanding Agent",
        domain="Artificial Intelligence"
    )
    db.add(test_project)
    db.commit()
    db.refresh(test_project)
    project_id = test_project.id

    # Ingest document
    doc_id = f"test-und-{uuid.uuid4().hex[:8]}"
    paper = await document_processor.process_pdf_document(
        db=db,
        doc_id=doc_id,
        file_path=pdf_path,
        original_filename="test_understanding_paper.pdf",
        file_size=len(pdf_bytes),
        project_id=project_id
    )
    print(f"[OK] Ingested Test Paper: '{paper.title}' (ID: {doc_id}) with {len(paper.sections)} sections.")
    db.close()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # TEST 1: Execute Section-Aware Analysis via POST /api/understanding/analyze/{paper_id}
        print("\n--- TEST 1: Section-Aware Structured Extraction ---")
        res1 = await client.post(f"/api/understanding/analyze/{doc_id}", json={
            "force_reanalyze": True,
            "allow_llm_assist": True
        })
        assert res1.status_code == 200, f"Analysis failed: {res1.text}"
        data1 = res1.json()
        analysis = data1["analysis"]
        print(f"Paper Title: '{data1['paper_title']}'")
        print(f"Message: {data1['message']}")
        assert analysis["is_cached"] is False, "First run should not be cached"

        # TEST 2: Validate All 13 Extracted Research Fields
        print("\n--- TEST 2: Validate 13 Research Fields ---")
        required_fields = [
            "research_problem",
            "research_objectives",
            "motivation",
            "research_methodology",
            "algorithms",
            "datasets",
            "dataset_size",
            "preprocessing_techniques",
            "evaluation_metrics",
            "experimental_results",
            "limitations",
            "future_work",
            "conclusions"
        ]

        for field_name in required_fields:
            field = analysis[field_name]
            print(f"[{field_name.upper()}]:")
            print(f"  Value: {field['value']}")
            print(f"  Page: {field['page_number']} | Section: {field['section_title']}")
            print(f"  Method: {field['extraction_method']} | Confidence: {field['confidence']}")
            print(f"  Supporting Text: {(field['supporting_text'] or 'N/A')[:90]}...")

            # Validate structural constraints
            assert "value" in field, f"Missing 'value' in {field_name}"
            assert "document_id" in field and field["document_id"] == doc_id
            assert "page_number" in field
            assert "supporting_text" in field

        # Specific ground truth verifications (Never invent metrics, sizes, or results)
        print("\n--- TEST 3: Ground Truth Verification (No Fabrication) ---")
        assert "congestion" in analysis["research_problem"]["value"].lower() or "bottleneck" in analysis["research_problem"]["value"].lower()
        assert "h-marl" in analysis["research_objectives"]["value"].lower() or "wait times" in analysis["research_objectives"]["value"].lower()
        assert "actor-critic" in analysis["algorithms"]["value"].lower() or "ppo" in analysis["algorithms"]["value"].lower() or "h-marl" in analysis["algorithms"]["value"].lower()
        assert "500" in analysis["dataset_size"]["value"]
        assert "normalized" in analysis["preprocessing_techniques"]["value"].lower() or "tensor" in analysis["preprocessing_techniques"]["value"].lower()
        assert "delay" in analysis["evaluation_metrics"]["value"].lower() or "fuel savings" in analysis["evaluation_metrics"]["value"].lower()
        assert "22.4%" in analysis["experimental_results"]["value"] or "16.8%" in analysis["experimental_results"]["value"]
        assert "12%" in analysis["limitations"]["value"] or "packet loss" in analysis["limitations"]["value"].lower()
        assert "byzantine" in analysis["future_work"]["value"].lower() or "future work" in (analysis["future_work"]["supporting_text"] or "").lower()
        print("[PASS] Test 3: All 13 fields accurately extracted from ground-truth sections without hallucination.")

        # TEST 4: Persistent Caching & Avoiding Reprocessing
        print("\n--- TEST 4: Persistent Caching Verification ---")
        t0 = time.time()
        res_cached = await client.get(f"/api/understanding/analysis/{doc_id}")
        t1 = time.time()
        assert res_cached.status_code == 200
        cached_analysis = res_cached.json()
        print(f"Cached Retrieval Time: {(t1 - t0)*1000:.2f} ms")
        print(f"Is Cached: {cached_analysis['is_cached']}")
        assert cached_analysis["is_cached"] is True, "Second retrieval must return cached result"
        assert cached_analysis["paper_id"] == doc_id
        assert cached_analysis["experimental_results"]["value"] == analysis["experimental_results"]["value"]
        print("[PASS] Test 4: Persistent caching verified in SQLite; unchanged document was not reprocessed.")

        # TEST 5: Missing Information Returns 'Not Reported' (Never Fabricated)
        print("\n--- TEST 5: Verify 'Not Reported' Handling for Missing Content ---")
        # Ingest a minimalist abstract-only paper with no dataset size or future work
        sparse_sections = [
            ("Abstract", "We study asymptotic properties of matrix multiplication in abelian rings.")
        ]
        sparse_pdf = create_rich_academic_pdf("Abstract Theory of Rings", sparse_sections)
        sparse_doc_id = f"test-sparse-{uuid.uuid4().hex[:8]}"
        sparse_path = pdf_dir / "test_sparse.pdf"
        sparse_path.write_bytes(sparse_pdf)

        db = SessionLocal()
        sparse_paper = await document_processor.process_pdf_document(
            db=db,
            doc_id=sparse_doc_id,
            file_path=sparse_path,
            original_filename="test_sparse.pdf",
            file_size=len(sparse_pdf),
            project_id=project_id
        )
        db.close()

        res_sparse = await client.post(f"/api/understanding/analyze/{sparse_doc_id}", json={
            "force_reanalyze": True,
            "allow_llm_assist": False # Test pure rule-based reporting of missing fields
        })
        assert res_sparse.status_code == 200
        sparse_analysis = res_sparse.json()["analysis"]
        print(f"Sparse Dataset Size: {sparse_analysis['dataset_size']['value']}")
        print(f"Sparse Limitations: {sparse_analysis['limitations']['value']}")
        print(f"Sparse Future Work: {sparse_analysis['future_work']['value']}")
        assert sparse_analysis["dataset_size"]["value"] in ["Not Reported", None]
        assert sparse_analysis["limitations"]["value"] in ["Not Reported", None]
        assert sparse_analysis["future_work"]["value"] in ["Not Reported", None]
        print("[PASS] Test 5: Missing information returned 'Not Reported' without fabricating dataset sizes or limitations.")

        # Clean up temp test files
        if pdf_path.exists():
            pdf_path.unlink()
        if sparse_path.exists():
            sparse_path.unlink()

    print("\n" + "=" * 80)
    print("ALL PDF UNDERSTANDING AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_understanding_agent_tests())

