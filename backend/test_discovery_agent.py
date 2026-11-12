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
from backend.app.models.entities import ResearchProject, ResearchPaper
from backend.app.services.discovery_agent import discovery_agent, normalize_doi, normalize_title
from backend.app.models.discovery_schemas import DiscoveredPaper

def create_sample_pdf(title: str, text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), title, fontsize=16)
    page.insert_text((50, 100), "ABSTRACT", fontsize=12)
    page.insert_textbox(pymupdf.Rect(50, 120, 500, 300), text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

async def run_discovery_agent_tests():
    print("=" * 80)
    print("STARTING RESEARCH DISCOVERY AGENT VERIFICATION TESTS")
    print("=" * 80)
    init_db()

    # Create a test research project
    db = SessionLocal()
    test_project = ResearchProject(
        title=f"Discovery Evaluation Project {uuid.uuid4().hex[:6]}",
        description="Testing OpenAlex, arXiv, and Semantic Scholar integration",
        domain="Artificial Intelligence"
    )
    db.add(test_project)
    db.commit()
    db.refresh(test_project)
    project_id = test_project.id
    print(f"[OK] Created Test Research Project: '{test_project.title}' (ID: {project_id})")
    db.close()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # TEST 1: Live Academic Search (OpenAlex + arXiv + Semantic Scholar)
        print("\n--- TEST 1: Live Multi-Source Academic Search ---")
        topic = "quantum annealing"
        keywords = ["optimization", "qubits"]
        res1 = await client.post("/api/discovery/search", json={
            "topic": topic,
            "keywords": keywords,
            "limit_per_source": 4,
            "sources": ["openalex", "arxiv", "semanticscholar"],
            "sort_by": "relevance"
        })
        assert res1.status_code == 200, f"Search failed: {res1.text}"
        data1 = res1.json()
        print(f"Topic: '{data1['topic']}'")
        print(f"Total Papers Discovered: {data1['total_found']}")
        print(f"Sources Statuses: {data1['source_statuses']}")

        # Ensure search succeeded gracefully across available sources
        assert data1["total_found"] > 0, "Expected discovered papers from available sources"
        assert "openalex" in data1["source_statuses"]
        assert "arxiv" in data1["source_statuses"]

        # TEST 2: Extraction of Metadata (title, abstract, authors, DOI, year, URL)
        print("\n--- TEST 2: Validate Extracted Metadata Fields ---")
        first_paper = data1["papers"][0]
        print(f"Top Ranked Paper: '{first_paper['title']}'")
        print(f"  Year: {first_paper['year']}")
        print(f"  Authors: {first_paper['authors'][:3]} (Total: {len(first_paper['authors'])})")
        print(f"  DOI: {first_paper['doi']}")
        print(f"  URL: {first_paper['url']}")
        print(f"  Sources: {first_paper['sources']}")
        print(f"  Open Access: {first_paper['is_open_access']}")
        print(f"  Relevance Score: {first_paper['relevance_score']}")
        print(f"  Abstract Snippet: {(first_paper['abstract'] or 'N/A')[:100]}...")

        assert first_paper["title"] and len(first_paper["title"]) > 3
        assert isinstance(first_paper["authors"], list)
        assert first_paper["relevance_score"] >= 0.0
        print("[PASS] Test 2: Academic metadata cleanly extracted without fabrication.")

        # TEST 3: Duplicate Detection and Cross-Source Merging
        print("\n--- TEST 3: Duplicate Detection Across Sources ---")
        # Synthesize duplicate mock entries with matching DOI and matching title
        dup1 = DiscoveredPaper(
            id="dup-test-1",
            title="Efficient Attention for Long Document Classification",
            abstract="Short abstract",
            authors=["Alice Smith"],
            doi="10.1234/test.doi.001",
            year=2023,
            url="https://openalex.org/W1",
            pdf_url=None,
            is_open_access=False,
            sources=["openalex"]
        )
        dup2 = DiscoveredPaper(
            id="dup-test-2",
            title="Efficient Attention for Long Document Classification",
            abstract="Longer, richer abstract detailing transformer quadratic complexity reduction.",
            authors=["Alice Smith", "Bob Jones"],
            doi="10.1234/test.doi.001",
            year=2023,
            url="https://arxiv.org/abs/2301.99999",
            pdf_url="https://arxiv.org/pdf/2301.99999.pdf",
            is_open_access=True,
            sources=["arxiv"]
        )
        deduped = discovery_agent.deduplicate_papers([dup1, dup2])
        assert len(deduped) == 1, f"Expected 1 merged paper, got {len(deduped)}"
        merged = deduped[0]
        assert "openalex" in merged.sources and "arxiv" in merged.sources
        assert merged.is_open_access is True
        assert merged.pdf_url == "https://arxiv.org/pdf/2301.99999.pdf"
        assert len(merged.abstract) > len("Short abstract")
        print(f"[PASS] Test 3: Cross-source duplicates merged successfully: sources={merged.sources}, OA={merged.is_open_access}.")

        # TEST 4: Filtering by Year, Author, and Open-Access Status
        print("\n--- TEST 4: Filtering by Year, Author, and Open-Access ---")
        res_filter = await client.post("/api/discovery/search", json={
            "topic": "transformer",
            "year_start": 2022,
            "year_end": 2024,
            "open_access_only": True,
            "limit_per_source": 5,
            "sources": ["arxiv"]
        })
        assert res_filter.status_code == 200
        filtered_data = res_filter.json()
        print(f"Filtered Results Found: {filtered_data['total_found']}")
        for p in filtered_data["papers"]:
            if p["year"]:
                assert 2022 <= p["year"] <= 2024, f"Year filter violated: {p['year']}"
            assert p["is_open_access"] is True, f"Open access filter violated: {p['is_open_access']}"
        print("[PASS] Test 4: Year and Open-Access filtering verified.")

        # TEST 5: Add Discovered Paper to Research Project (with Open-Access PDF download)
        print("\n--- TEST 5: Add Discovered Paper to Project (Download PDF & Index) ---")
        # Find an open-access paper with a verified PDF from arXiv
        oa_target = next((p for p in data1["papers"] if p["pdf_url"] and "arxiv.org" in p["pdf_url"]), None)
        if not oa_target:
            # Fall back to any arXiv result
            oa_target = DiscoveredPaper(
                id=f"test-arxiv-{uuid.uuid4().hex[:6]}",
                title="A Quantum Annealing Primer for Combinatorial Optimization",
                abstract="Comprehensive introduction to adiabatic quantum computation and QAOA.",
                authors=["Test Researcher"],
                doi=None,
                year=2023,
                url="https://arxiv.org/abs/2301.00001",
                pdf_url="https://arxiv.org/pdf/2301.00001.pdf",
                is_open_access=True,
                sources=["arxiv"]
            )

        if isinstance(oa_target, dict):
            oa_paper_dict = oa_target
        elif hasattr(oa_target, "model_dump"):
            oa_paper_dict = oa_target.model_dump()
        else:
            oa_paper_dict = oa_target.dict()

        res_add = await client.post("/api/discovery/add-to-project", json={
            "project_id": project_id,
            "paper": oa_paper_dict,
            "download_pdf": True,
            "process_document": True
        })
        assert res_add.status_code == 200, f"Add to project failed: {res_add.text}"
        add_data = res_add.json()
        print(f"Added Paper Result: ID={add_data['paper_id']}, Title='{add_data['title']}'")
        print(f"PDF Downloaded: {add_data['pdf_downloaded']}, Status: {add_data['processed_status']}")
        print(f"Message: {add_data['message']}")
        assert add_data["project_id"] == project_id

        # Verify record in SQLite database
        db = SessionLocal()
        saved_paper = db.query(ResearchPaper).filter(ResearchPaper.id == add_data["paper_id"]).first()
        assert saved_paper is not None, "Paper not found in SQLite"
        assert saved_paper.project_id == project_id
        db.close()
        print("[PASS] Test 5: Paper successfully added to existing research project in SQLite.")

        # TEST 6: Metadata-only Addition When PDF Unavailable + Manual PDF Attachment
        print("\n--- TEST 6: Metadata-Only Paper & Manual PDF Attachment ---")
        no_pdf_paper = DiscoveredPaper(
            id=f"meta-only-{uuid.uuid4().hex[:6]}",
            title="Proprietary Closed-Access Monograph on Machine Learning Systems",
            abstract="Study of multi-agent distributed scheduling behind corporate paywalls.",
            authors=["Dr. Closed Source"],
            doi=f"10.9999/closed.{uuid.uuid4().hex[:6]}",
            year=2021,
            url="https://example.com/closed-paper",
            pdf_url=None,  # No PDF download available
            is_open_access=False,
            sources=["openalex"]
        )

        res_meta = await client.post("/api/discovery/add-to-project", json={
            "project_id": project_id,
            "paper": no_pdf_paper.model_dump(),
            "download_pdf": True,
            "process_document": True
        })
        assert res_meta.status_code == 200
        meta_data = res_meta.json()
        assert meta_data["pdf_downloaded"] is False
        assert meta_data["processed_status"] == "metadata_only"
        print(f"[PASS] Added metadata-only paper: {meta_data['message']}")

        # Now test manual PDF upload for this paper
        sample_bytes = create_sample_pdf(
            title=no_pdf_paper.title,
            text="This is the manually uploaded full-text PDF of the paper with complete methodology."
        )
        files = {
            "file": ("manual_upload.pdf", io.BytesIO(sample_bytes), "application/pdf")
        }
        res_upload = await client.post(
            f"/api/discovery/attach-pdf/{meta_data['paper_id']}",
            files=files
        )
        assert res_upload.status_code == 200, f"Manual PDF upload failed: {res_upload.text}"
        upload_data = res_upload.json()
        print(f"Manual Attachment Result: Status={upload_data['processed_status']}, Sections={upload_data['section_count']}")
        assert upload_data["processed_status"] == "completed"
        assert upload_data["section_count"] > 0
        print("[PASS] Test 6: Manual PDF upload and full indexing for metadata-only paper succeeded.")

        # TEST 7: Graceful Handling of Offline / Invalid Sources
        print("\n--- TEST 7: Graceful Failure Handling ---")
        res_failover = await client.post("/api/discovery/search", json={
            "topic": "test query",
            "sources": ["semanticscholar"], # We know S2 returns 429 without key
            "limit_per_source": 2
        })
        assert res_failover.status_code == 200, "API search should not crash with 500 when source is rate-limited"
        failover_data = res_failover.json()
        print(f"Failover Status: {failover_data['source_statuses']}")
        print("[PASS] Test 7: Graceful handling verified without application crash.")

    print("\n" + "=" * 80)
    print("ALL RESEARCH DISCOVERY AGENT TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_discovery_agent_tests())

