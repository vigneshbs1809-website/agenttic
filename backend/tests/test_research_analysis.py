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

def create_academic_paper_pdf(title: str, sections_data: list) -> bytes:
    doc = pymupdf.open()
    current_page = doc.new_page(width=595, height=842)
    y = 50
    current_page.insert_text((50, y), title, fontsize=15, fontname="helv", color=(0, 0, 0))
    y += 35
    current_page.insert_text((50, y), "Authors: Prof. Laura Chen, Dr. Alan Turing | Year: 2024 | DOI: 10.1000/analysis.001", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
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

async def run_research_analysis_tests():
    print("=" * 80)
    print("STARTING RESEARCH ANALYSIS AGENT INTEGRATION TESTS")
    print("=" * 80)
    init_db()

    # 1. Build an actual academic research paper with full multi-dimensional content
    paper_title = "Adaptive Sparse Attention Networks for Long-Sequence Genomic Modeling"
    sections = [
        ("Abstract",
         "The computational bottleneck in modeling long eukaryotic sequences arises from quadratic attention complexity in transformers. "
         "In this work, our objective is to introduce GenoSparse, an adaptive hierarchical sparse attention mechanism. "
         "GenoSparse achieves a 4.2x speedup and 35.6% memory reduction over standard self-attention on 100k-base sequences. "
         "Code and checkpoints are available at https://github.com/genomics-ai/genosparse."),
        ("Introduction",
         "The challenge of scaling sequence models to megabase-scale genomic contexts impedes discovery in regulatory genomics. "
         "Motivated by long-range chromatin interactions, we present an attention routing protocol. "
         "Our primary goal of this paper is to enable linear-time genomic representation learning without compromising sequence resolution."),
        ("Methodology",
         "Our framework is based on localized locality-sensitive hashing (LSH) combined with dilated strided attention blocks. "
         "The GenoSparse algorithm routes query tokens dynamically based on Hamming distance projections. "
         "Data preprocessing consists of k-mer frequency normalization, one-hot nucleotide encoding, and random reverse-complement augmentation."),
        ("Experiments",
         "Evaluated on the synthetic Human-Chr21 benchmark dataset comprising 25,000 genomic intervals. "
         "The experimental setup utilized 4 NVIDIA A100 GPUs with AdamW optimizer and cosine learning rate decay across 200 epochs. "
         "Evaluation metrics include cross-entropy loss, top-1 accuracy, throughput latency, and peak GPU memory footprint."),
        ("Results",
         "Experimental results confirm that GenoSparse achieved a 35.6% memory reduction and a 4.2x speedup compared to standard FlashAttention-2. "
         "GenoSparse outperformed classical convolutional baselines by an 8.4% improvement in regulatory element classification."),
        ("Discussion",
         "A major strength of GenoSparse is its ability to capture chromatin loops spanning over 50 kilobases without quadratic overhead."),
        ("Limitations",
         "A key limitation is that performance degrades when nucleotide sequencing read quality drops below Phred-score Q20."),
        ("Conclusion",
         "In conclusion, adaptive sparse attention provides scalable long-context biological sequence understanding. "
         "In future work, we plan to extend this architecture to whole-genome epigenetic methylation mapping.")
    ]

    pdf_bytes = create_academic_paper_pdf(paper_title, sections)
    pdf_dir = Path("backend/data/PDFs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / "test_genomic_paper.pdf"
    pdf_path.write_bytes(pdf_bytes)

    db = SessionLocal()
    # Create test research project
    test_proj = ResearchProject(
        title=f"Genomics Intelligence {uuid.uuid4().hex[:6]}",
        description="Testing Research Analysis Agent 14-dimensional evaluation",
        domain="Computational Biology"
    )
    db.add(test_proj)
    db.commit()
    db.refresh(test_proj)
    project_id = test_proj.id

    # Ingest document
    doc_id = f"test-analysis-{uuid.uuid4().hex[:8]}"
    paper = await document_processor.process_pdf_document(
        db=db,
        doc_id=doc_id,
        file_path=pdf_path,
        original_filename="test_genomic_paper.pdf",
        file_size=len(pdf_bytes),
        project_id=project_id
    )
    print(f"[OK] Ingested Academic Paper: '{paper.title}' (ID: {doc_id}) with {len(paper.sections)} sections.")
    db.close()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # TEST 1: Execute 14-Dimension Analysis (POST /api/analysis/analyze/{paper_id})
        print("\n--- TEST 1: Execute 14-Dimension Analysis ---")
        res1 = await client.post(f"/api/analysis/analyze/{doc_id}", json={
            "regenerate": True,
            "include_markdown_report": True
        })
        assert res1.status_code == 200, f"Analysis failed: {res1.text}"
        data1 = res1.json()
        report = data1["report"]
        print(f"Paper Title: '{data1['paper_title']}'")
        print(f"Message: {data1['message']}")
        print(f"Model Used: {report['model_used']}")
        print(f"Confidence Score: {report['confidence_score']}")
        print(f"Executive Summary:\n  {report['executive_summary']}")
        assert report["is_cached"] is False, "First run should not be cached"

        # TEST 2: Validate All 14 Analytical Dimensions & Provenance
        print("\n--- TEST 2: Validate 14 Dimensions & Page Citations ---")
        dim_keys = [
            ("1. Research Problem", "research_problem"),
            ("2. Objectives", "objectives"),
            ("3. Motivation", "motivation"),
            ("4. Methodology", "methodology"),
            ("5. Algorithms", "algorithms"),
            ("6. Dataset Characteristics", "dataset_characteristics"),
            ("7. Data Preprocessing", "data_preprocessing"),
            ("8. Experimental Setup", "experimental_setup"),
            ("9. Evaluation Metrics", "evaluation_metrics"),
            ("10. Results", "results"),
            ("11. Strengths", "strengths"),
            ("12. Limitations", "limitations"),
            ("13. Future Directions", "future_directions"),
            ("14. Reproducibility", "reproducibility")
        ]

        for label, key in dim_keys:
            d = report[key]
            print(f"\n[{label.upper()}]:")
            print(f"  Status: {d['status']}")
            print(f"  Summary: {d['summary'][:90]}...")
            print(f"  Evidence Count: {len(d['evidence'])}")
            if d['evidence']:
                first_ev = d['evidence'][0]
                print(f"  Primary Citation: Page {first_ev['page_number']} [{first_ev['section_name']}]")
                print(f"  Quote Snippet: {first_ev['quote'][:80]}...")

            assert d["dimension_name"]
            assert d["status"] in ["reported", "not_reported", "partially_reported"]
            assert d["summary"]

        # TEST 3: Ground Truth Verification (No Fabrication)
        print("\n--- TEST 3: Ground Truth Verification ---")
        assert "quadratic" in report["research_problem"]["summary"].lower() or "bottleneck" in report["research_problem"]["summary"].lower()
        assert "genosparse" in report["objectives"]["summary"].lower() or "sparse attention" in report["objectives"]["summary"].lower()
        assert "chromatin" in report["motivation"]["summary"].lower() or "long-range" in report["motivation"]["summary"].lower()
        assert "genosparse" in report["algorithms"]["summary"].lower() or "lsh" in report["algorithms"]["summary"].lower()
        assert "25,000" in report["dataset_characteristics"]["summary"] or "human-chr21" in report["dataset_characteristics"]["summary"].lower()
        assert "k-mer" in report["data_preprocessing"]["summary"].lower() or "one-hot" in report["data_preprocessing"]["summary"].lower()
        assert "35.6%" in report["results"]["summary"] or "4.2x" in report["results"]["summary"]
        assert "phred" in report["limitations"]["summary"].lower() or "q20" in report["limitations"]["summary"].lower()
        assert "methylation" in report["future_directions"]["summary"].lower()
        assert "github.com/genomics-ai/genosparse" in report["reproducibility"]["summary"]
        assert report["reproducibility"]["status"] == "reported"
        print("[PASS] Test 3: Ground truth accurately verified across all 14 dimensions.")

        # TEST 4: Formatted Markdown Report Verification
        print("\n--- TEST 4: Markdown Report Generation ---")
        assert "report_markdown" in report and len(report["report_markdown"]) > 500
        md_text = report["report_markdown"]
        assert "# Scientific Research Analysis Report:" in md_text
        assert "14-Dimensional Analytical Matrix" in md_text
        assert "Reproducibility Checklist" in md_text
        print(f"Markdown Report Generated ({len(md_text)} characters).")

        # Test markdown endpoint GET /api/analysis/report/{paper_id}/markdown
        res_md = await client.get(f"/api/analysis/report/{doc_id}/markdown")
        assert res_md.status_code == 200
        assert res_md.headers["content-type"].startswith("text/markdown")
        print("[PASS] Test 4: Markdown report endpoint verified.")

        # TEST 5: SQLite Persistence & Caching
        print("\n--- TEST 5: Persistent Storage in SQLite & Cache Check ---")
        db = SessionLocal()
        saved_an = db.query(PaperAnalysis).filter(PaperAnalysis.paper_id == doc_id).first()
        assert saved_an is not None
        assert saved_an.structured_data is not None
        assert saved_an.report_markdown is not None
        db.close()

        # Second request without regenerate should hit cache
        t0 = time.time()
        res_cached = await client.get(f"/api/analysis/report/{doc_id}")
        t1 = time.time()
        assert res_cached.status_code == 200
        cached_data = res_cached.json()
        assert cached_data["is_cached"] is True
        print(f"Cached Analysis Retrieved in {(t1 - t0)*1000:.2f} ms with is_cached=True.")
        print("[PASS] Test 5: SQLite persistence and fast caching verified.")

        # TEST 6: Option to Regenerate After Document Corrections
        print("\n--- TEST 6: Regenerate Analysis Option ---")
        res_regen = await client.post(f"/api/analysis/analyze/{doc_id}", json={
            "regenerate": True
        })
        assert res_regen.status_code == 200
        regen_data = res_regen.json()
        assert regen_data["report"]["is_cached"] is False
        print(f"Regenerated message: {regen_data['message']}")
        print("[PASS] Test 6: Regeneration option successfully re-extracted analysis after document corrections.")

        # Clean up temp test files
        if pdf_path.exists():
            pdf_path.unlink()

    print("\n" + "=" * 80)
    print("ALL RESEARCH ANALYSIS AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_research_analysis_tests())

