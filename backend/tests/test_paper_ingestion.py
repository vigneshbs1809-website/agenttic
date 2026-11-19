import asyncio
import io
import sys
import uuid
from pathlib import Path
import fitz  # PyMuPDF
import httpx

# Set up module path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.database import SessionLocal, init_db
from backend.app.models.entities import ResearchProject, ResearchPaper, PaperSection, Author
from backend.app.services.vector_service import vector_service
from backend.app.main import app

def create_sample_scientific_pdf() -> bytes:
    """Generates a realistic multi-page scientific PDF using PyMuPDF."""
    doc = fitz.open()

    # Page 1: Title, Authors, Abstract, Introduction
    p1 = doc.new_page()
    p1_text = """Quantized Local Transformer Architectures on Edge Compute

Dr. Elena Rostova, Marcus Vance
AI Systems Institute

Abstract:
We present a rigorous investigation into 4-bit weight quantization strategies for sub-2B parameter transformer models operating on edge compute platforms. Our findings confirm that INT4 representation preserves 97.4% of benchmark accuracy while slashing system memory requirements from 6.8 GB to 1.4 GB.

1. Introduction
Deploying modern language models on consumer-grade hardware with 8 GB of RAM introduces critical memory constraints. Standard floating-point 16-bit checkpoints rapidly exhaust physical memory, leading to page thrashing and catastrophic latency degradation."""
    p1.insert_text((50, 60), p1_text, fontsize=11)

    # Page 2: Methodology & Cache Optimization
    p2 = doc.new_page()
    p2_text = """2. Methodology and KV Cache Pruning
Our quantization framework applies group-wise quantization across key-value attention projections. By bounding the maximum dynamic context window to 4096 tokens and evicting low-attention tokens from the resident cache, we sustain uniform memory utilization throughout continuous autoregressive generation.

3. Experimental Setup
We test our framework against sub-2B models including Qwen and Gemma variants on Windows 11 host systems equipped with 8 GB RAM and AVX2 CPU extensions."""
    p2.insert_text((50, 60), p2_text, fontsize=11)

    # Page 3: Empirical Results & Conclusion
    p3 = doc.new_page()
    p3_text = """4. Experimental Results and Discussion
Our benchmark results demonstrate an average per-token generation latency of 74ms on Intel 12th Gen CPUs without dedicated GPU acceleration. The total memory footprint remained strictly under 1.6 GB, leaving ample operating headroom for host operating system background processes.

5. Conclusion
Local AI intelligence platforms can successfully deliver real-time literature synthesis on 8 GB RAM machines through careful combination of 4-bit quantization, lightweight vector indices, and streaming inference."""
    p3.insert_text((50, 60), p3_text, fontsize=11)

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes

async def run_paper_ingestion_test():
    print("=" * 70)
    print("  RESEARCH PAPER INGESTION & CHROMADB VECTOR PIPELINE TEST")
    print("=" * 70)

    init_db()

    # 1. Create a Project to attach papers to
    db = SessionLocal()
    try:
        project = ResearchProject(
            title="Local LLM Architecture Benchmarks",
            description="Testing scientific PDF parsing, section chunking, and ChromaDB vector search.",
            domain="Computer Science",
            status="active"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        project_id = project.id
        print(f"\n[1/6] Created Parent Project: ID={project_id}")
    finally:
        db.close()

    # 2. Generate PDF in memory
    print("\n[2/6] Generating Sample Scientific Research PDF (3 Pages)...")
    pdf_bytes = create_sample_scientific_pdf()
    print(f"  -> Generated PDF size: {len(pdf_bytes)} bytes")

    # 3. Upload via FastAPI HTTP API
    print("\n[3/6] Uploading PDF via POST /api/projects/{id}/papers/upload...")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        files = {
            "file": ("quantized_transformers_edge.pdf", io.BytesIO(pdf_bytes), "application/pdf")
        }
        res_upload = await client.post(
            f"/api/projects/{project_id}/papers/upload",
            files=files
        )
        print(f"  -> Upload Response: HTTP {res_upload.status_code}")
        assert res_upload.status_code == 201, f"Upload failed: {res_upload.text}"
        paper_data = res_upload.json()
        paper_id = paper_data["id"]
        print(f"  -> Paper Title:   \"{paper_data.get('title')}\"")
        print(f"  -> Paper ID:      {paper_id}")
        print(f"  -> Total Pages:   {paper_data.get('total_pages')}")
        print(f"  -> Authors:       {paper_data.get('authors')}")
        print(f"  -> Sections:      {paper_data.get('section_count')}")

        # 4. Verify Parsed Sections via GET /api/papers/{paper_id}/sections
        print("\n[4/6] Verifying Extracted Sections via GET /api/papers/{paper_id}/sections...")
        res_sections = await client.get(f"/api/papers/{paper_id}/sections")
        print(f"  -> Sections Response: HTTP {res_sections.status_code}")
        assert res_sections.status_code == 200
        sections = res_sections.json()
        print(f"  -> Total Sections Parsed: {len(sections)}")
        for idx, s in enumerate(sections):
            print(f"     [{idx+1}] Section: '{s.get('section_title')}' (Type: {s.get('section_type')}, Tokens: {s.get('token_count')})")
        assert len(sections) >= 3, "Expected at least 3 sections extracted"

        # 5. Semantic Vector Search Query on ChromaDB
        print("\n[5/6] Testing Semantic Vector Search on ChromaDB with nomic-embed-text...")
        query_text = "What is the per-token generation latency on an 8 GB RAM CPU system?"
        print(f"  -> Query: \"{query_text}\"")
        matches = await vector_service.query_similar(
            query_text=query_text,
            top_k=2,
            document_filter=[paper_id]
        )
        print(f"  -> Retrieved Chunks Count: {len(matches)}")
        assert len(matches) > 0, "No semantic chunks retrieved from ChromaDB!"
        top_match = matches[0]
        print(f"  -> Top Match Similarity: {top_match.get('similarity_score')}")
        print(f"  -> Section:             {top_match.get('section_name')}")
        print(f"  -> Snippet Preview:     \"{top_match.get('snippet')[:140]}...\"")
        assert "latency" in top_match.get("content", "").lower() or "74ms" in top_match.get("content", "").lower(), "Expected relevant latency excerpt"

        # 6. Test Cascade Deletion via DELETE /api/papers/{paper_id}
        print("\n[6/6] Testing Cascade Deletion via DELETE /api/papers/{paper_id}...")
        res_delete = await client.delete(f"/api/papers/{paper_id}")
        print(f"  -> Delete Response: HTTP {res_delete.status_code}")
        assert res_delete.status_code == 200

        # Verify deletion in SQLite
        res_get_deleted = await client.get(f"/api/papers/{paper_id}")
        assert res_get_deleted.status_code == 404
        print("  -> Verified 404 in SQLite after deletion.")

        # Verify ChromaDB chunks purged
        post_del_matches = await vector_service.query_similar(
            query_text=query_text,
            top_k=2,
            document_filter=[paper_id]
        )
        assert len(post_del_matches) == 0, "ChromaDB chunks were not purged!"
        print("  -> Verified ChromaDB vector embeddings purged.")

    print("\n" + "=" * 70)
    print("  SUCCESS: FULL RESEARCH PAPER INGESTION & VECTOR RETRIEVAL VERIFIED!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = asyncio.run(run_paper_ingestion_test())
    sys.exit(0 if success else 1)

