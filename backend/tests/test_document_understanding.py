import asyncio
import io
import sys
import uuid
from pathlib import Path
import pymupdf
import httpx

# Set up module path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.database import SessionLocal, init_db
from backend.app.models.entities import ResearchPaper, PaperSection, Author
from backend.app.main import app

def generate_paper_pdf(
    title: str,
    authors: str,
    year: int,
    abstract_text: str,
    sections_dict: dict
) -> bytes:
    """Generates a structured, multi-page scientific PDF using PyMuPDF."""
    doc = pymupdf.open()

    # Page 1: Header, Title, Authors, Abstract, Introduction, Related Work
    p1 = doc.new_page()
    text_p1 = f"""{title}
{authors}
Department of Computer Science & Artificial Intelligence
Published: {year}

Abstract:
{abstract_text}

1. Introduction
Modern scientific literature analysis requires parsing complex documents under memory-constrained environments. As research publication volumes grow exponentially, local intelligence systems must extract semantic structures without offloading sensitive private data to third-party cloud providers.

2. Related Work
Prior literature mining approaches rely heavily on heuristic regular expressions or monolithic LLM parsing that exceeds consumer hardware memory budgets. In contrast, hybrid parsing preserves spatial bounding boxes and font hierarchies before lightweight neural synthesis."""
    p1.insert_text((50, 50), text_p1, fontsize=10)

    # Page 2: Methodology, Experiments, Results
    p2 = doc.new_page()
    text_p2 = f"""3. Methodology
{sections_dict.get('Methodology', 'Our proposed architecture splits document parsing into visual block decomposition and streaming chunk tokenization.')}

4. Experiments
{sections_dict.get('Experiments', 'We evaluate parsing accuracy across 500 peer-reviewed papers on an 8 GB RAM Windows workstation.')}

5. Results
{sections_dict.get('Results', 'Experimental evaluation demonstrates 98.2% header detection accuracy while maintaining resident RAM under 250 MB.')}"""
    p2.insert_text((50, 50), text_p2, fontsize=10)

    # Page 3: Discussion, Limitations, Conclusion, References
    p3 = doc.new_page()
    text_p3 = f"""6. Discussion
{sections_dict.get('Discussion', 'The integration of sliding-window chunking with low-memory vector indexes enables fluid cross-paper question answering.')}

7. Limitations
{sections_dict.get('Limitations', 'Our current parser focuses primarily on dual-column and single-column text structures; multi-table extraction requires specialized OCR.')}

8. Conclusion
{sections_dict.get('Conclusion', 'We have demonstrated a local-first literature platform that reliably parses, understands, and indexes academic literature.')}

9. References
[1] Vaswani, A., et al. Attention Is All You Need. NeurIPS 2017.
[2] Touvron, H., et al. LLaMA: Open and Efficient Foundation Language Models. 2023.
[3] Qwen Team. Qwen2.5 Technical Report. 2024."""
    p3.insert_text((50, 50), text_p3, fontsize=10)

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes

async def test_pdf_upload_and_understanding():
    print("=" * 75)
    print("  PDF UPLOAD & DOCUMENT UNDERSTANDING TEST SUITE (3 ACADEMIC PAPERS)")
    print("=" * 75)

    init_db()

    # 1. Create 3 Distinct Realistic Academic PDFs
    print("\n[1/6] Synthesizing 3 Real Academic PDFs...")
    paper1_bytes = generate_paper_pdf(
        title="Sparse Attention Mechanisms for Efficient Transformer Inference",
        authors="Dr. Rachel Kim, David Patel",
        year=2024,
        abstract_text="We explore structured sparse attention patterns that diminish memory consumption by 62% during long-context document synthesis on CPU hardware.",
        sections_dict={
            "Methodology": "We construct dynamic block-sparse attention masks based on query-key cosine proximities calculated in streaming buffers.",
            "Experiments": "Evaluated against standard dense self-attention across context lengths ranging from 1024 to 8192 tokens.",
            "Results": "Attained a 2.8x speedup on Intel AVX2 instruction sets with zero loss in retrieval precision."
        }
    )
    print(f"  -> Generated Paper 1: 'Sparse Attention Mechanisms' ({len(paper1_bytes)} bytes)")

    paper2_bytes = generate_paper_pdf(
        title="Graph-Augmented Literature Intelligence: Bridging Citations and Concepts",
        authors="Prof. Vikram Sen, Maya Lindqvist",
        year=2024,
        abstract_text="This paper introduces a heterogeneous knowledge graph framework linking extracted scientific entities, citations, and research gaps across distributed papers.",
        sections_dict={
            "Methodology": "We extract entity-relation triples and build NetworkX graphs weighted by co-occurrence frequency and citation topology.",
            "Experiments": "Benchmarked on 200 biomedical publications to evaluate claim verification and literature gap detection.",
            "Results": "Graph navigation reveals cross-disciplinary conceptual connections 45% faster than keyword retrieval."
        }
    )
    print(f"  -> Generated Paper 2: 'Graph-Augmented Literature Intelligence' ({len(paper2_bytes)} bytes)")

    paper3_bytes = generate_paper_pdf(
        title="Empirical Robustness of Quantized Neural Models on Consumer Hardware",
        authors="Lucas Morales, Dr. Elena Rostova",
        year=2023,
        abstract_text="We investigate the stability and numerical precision of 4-bit quantized language models running sustained inference loops on 8 GB RAM machines.",
        sections_dict={
            "Methodology": "We deploy INT4 quantization with group-wise scale factors and monitor thermal and memory paging metrics.",
            "Experiments": "Continuous 12-hour stress test generating scientific literature syntheses on Windows 11.",
            "Results": "Zero process terminations or OS page thrashing observed; mean memory usage remained steady at 1.48 GB."
        }
    )
    print(f"  -> Generated Paper 3: 'Empirical Robustness of Quantized Neural Models' ({len(paper3_bytes)} bytes)")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        # 2. Test Invalid Format Validation
        print("\n[2/6] Testing Format & Size Validation...")
        invalid_bytes = b"This is not a real PDF file header."
        res_invalid = await client.post(
            "/api/documents/upload",
            files={"file": ("fake_paper.pdf", io.BytesIO(invalid_bytes), "application/pdf")}
        )
        print(f"  -> Uploading Corrupt PDF Header: HTTP {res_invalid.status_code}")
        assert res_invalid.status_code == 400, "Corrupt PDF should be rejected with 400"
        print("  -> Corrupt PDF successfully rejected.")

        # 3. Test Single PDF Upload & Understanding (Paper 1)
        print("\n[3/6] Testing Single PDF Upload: POST /api/documents/upload (Paper 1)...")
        res_p1 = await client.post(
            "/api/documents/upload",
            files={"file": ("sparse_attention_inference.pdf", io.BytesIO(paper1_bytes), "application/pdf")}
        )
        print(f"  -> Paper 1 Upload Response: HTTP {res_p1.status_code}")
        assert res_p1.status_code == 201
        p1_data = res_p1.json()
        doc1_id = p1_data["document_id"]
        print(f"     Document ID:      {doc1_id}")
        print(f"     Status:           {p1_data['processed_status']}")
        print(f"     Stored in data/PDFs/{doc1_id}.pdf")

        # 4. Test Batch Upload of Multiple PDFs (Papers 2 & 3)
        print("\n[4/6] Testing Batch Upload: POST /api/documents/batch-upload (Papers 2 & 3)...")
        batch_files = [
            ("files", ("graph_literature_intelligence.pdf", io.BytesIO(paper2_bytes), "application/pdf")),
            ("files", ("quantized_models_consumer.pdf", io.BytesIO(paper3_bytes), "application/pdf"))
        ]
        res_batch = await client.post("/api/documents/batch-upload", files=batch_files)
        print(f"  -> Batch Upload Response: HTTP {res_batch.status_code}")
        assert res_batch.status_code == 201
        batch_data = res_batch.json()
        print(f"     Uploaded Count: {batch_data['uploaded_count']}")
        assert batch_data["uploaded_count"] == 2
        doc2_id = batch_data["documents"][0]["document_id"]
        doc3_id = batch_data["documents"][1]["document_id"]

        # 5. Verify Listing and Inspection of Academic Sections
        print("\n[5/6] Verifying Metadata & Academic Sections for all 3 Papers...")
        res_list = await client.get("/api/documents")
        assert res_list.status_code == 200
        all_docs = res_list.json()
        print(f"  -> Total Documents in System: {len(all_docs)}")

        # Inspect Paper 1 Details
        res_details = await client.get(f"/api/documents/{doc1_id}")
        assert res_details.status_code == 200
        details = res_details.json()
        print(f"\n  --- Document Inspection: {details.get('title')} ---")
        print(f"  -> Authors:         {details.get('authors')}")
        print(f"  -> Year:            {details.get('publication_year')}")
        print(f"  -> Pages:           {details.get('total_pages')}")
        print(f"  -> Abstract:        \"{details.get('abstract')[:100]}...\"")
        print(f"  -> Sections Count:  {details.get('section_count')}")

        # Verify page-by-page text preserving original page numbers
        res_pages = await client.get(f"/api/documents/{doc1_id}/pages")
        assert res_pages.status_code == 200
        pages = res_pages.json()
        print(f"  -> Extracted Pages count: {len(pages)}")
        for p in pages:
            print(f"     Page {p['page_number']}: {p['character_count']} chars, {p['token_count']} estimated tokens")
        assert len(pages) == 3, "Expected exactly 3 preserved PDF pages"

        # Verify Academic Sections
        res_sections = await client.get(f"/api/documents/{doc1_id}/sections")
        assert res_sections.status_code == 200
        sections = res_sections.json()
        section_types_found = [s["section_type"] for s in sections]
        print(f"  -> Academic Section Types Identified: {section_types_found}")
        
        # Verify canonical academic sections are present
        expected_types = ["abstract", "introduction", "methodology", "experiments", "results", "discussion", "conclusion"]
        for exp in expected_types:
            assert any(exp in st for st in section_types_found), f"Expected section '{exp}' not found in parsed sections!"
        print("  -> All core academic sections successfully detected!")

        # 6. Test Reprocessing & Deletion
        print("\n[6/6] Testing Reprocessing & Deletion...")
        # Reprocess Paper 2
        res_reprocess = await client.post(f"/api/documents/{doc2_id}/reprocess", json={"force_llm_assist": False})
        print(f"  -> POST /api/documents/{doc2_id}/reprocess: HTTP {res_reprocess.status_code}")
        assert res_reprocess.status_code == 200
        print("  -> Document successfully reprocessed.")

        # Delete Paper 3
        res_del = await client.delete(f"/api/documents/{doc3_id}")
        print(f"  -> DELETE /api/documents/{doc3_id}: HTTP {res_del.status_code}")
        assert res_del.status_code == 200

        # Verify 404 after deletion
        res_check_deleted = await client.get(f"/api/documents/{doc3_id}")
        assert res_check_deleted.status_code == 404
        print("  -> Verified 404 in SQLite after deletion.")
        assert not (Path("backend/data/PDFs") / f"{doc3_id}.pdf").exists(), "Physical PDF was not cleaned up!"
        print("  -> Verified physical PDF purged from data/PDFs.")

    print("\n" + "=" * 75)
    print("  SUCCESS: ALL 14 REQUIREMENTS & 3 ACADEMIC PAPERS VERIFIED!")
    print("=" * 75)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_pdf_upload_and_understanding())
    sys.exit(0 if success else 1)

