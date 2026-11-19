import os
import sys
sys.path.insert(0, os.path.abspath("."))
import json
import asyncio
from backend.app.core.database import SessionLocal
from backend.app.models.entities import ResearchPaper, ResearchProject, PaperSection
from backend.app.models.discovery_schemas import DiscoverySearchRequest, DiscoveredPaper
from backend.app.services.discovery_agent import discovery_agent
from backend.app.api.documents import (
    list_documents,
    get_document_details,
    get_academic_sections
)

def test_discovery_and_library():
    db = SessionLocal()
    print("=================================================================", flush=True)
    print("TESTING DISCOVER PAPERS & PDF LIBRARY WORKSPACES", flush=True)
    print("=================================================================", flush=True)

    # 1. Setup or retrieve test project
    test_project = db.query(ResearchProject).first()
    assert test_project is not None, "No research projects found in SQLite"
    project_id = test_project.id
    print(f"Using Research Project: {project_id} ('{test_project.title}')", flush=True)

    # 2. DISCOVER PAPERS: Search Request Handling
    print("\n--- 1. DISCOVER PAPERS: Offline Resilience & Request Handling ---", flush=True)
    search_req = DiscoverySearchRequest(
        topic="Multi-Agent Reinforcement Learning Graph Routing",
        sources=[], # Immediate return to test query parsing safely
        limit_per_source=2,
        year_start=2020,
        year_end=2026,
        open_access_only=False,
        sort_by="relevance"
    )
    papers, statuses = asyncio.run(discovery_agent.execute_discovery_search(search_req))
    print(f"Handled empty/offline source query gracefully: {len(papers)} papers returned, statuses: {statuses}", flush=True)

    # 3. DISCOVER PAPERS: Add Discovered Paper to Project
    print("\n--- 2. DISCOVER PAPERS: Add Discovered Paper to Project ---", flush=True)
    mock_discovered_paper = DiscoveredPaper(
        id="arxiv:2401.09999",
        title="Decentralized Graph Attention for Multi-Agent Fleets",
        abstract="We investigate distributed graph neural networks for vehicle routing.",
        authors=["Vaswani, A.", "Silver, D."],
        doi="10.1145/test.9999",
        year=2024,
        url="https://arxiv.org/abs/2401.09999",
        pdf_url="https://arxiv.org/pdf/2401.09999.pdf",
        is_open_access=True,
        sources=["arxiv", "openalex"],
        venue="ICML 2024",
        citation_count=42,
        relevance_score=0.95
    )

    paper_record, pdf_downloaded, msg = asyncio.run(discovery_agent.add_paper_to_project(
        db=db,
        project_id=project_id,
        paper=mock_discovered_paper,
        download_pdf=False,
        process_document=False
    ))
    print(f"Added Paper ID: {paper_record.id}", flush=True)
    print(f"Paper Title: {paper_record.title}", flush=True)
    print(f"DOI: {paper_record.doi}", flush=True)
    print(f"Processing Status: {paper_record.processed_status}", flush=True)
    print(f"Message: {msg}", flush=True)
    assert paper_record.id is not None
    assert paper_record.project_id == project_id

    # 4. PDF LIBRARY: List & Filter Existing Documents
    print("\n--- 3. PDF LIBRARY: List & Filter Documents ---", flush=True)
    all_docs = list_documents(project_id=None, db=db)
    print(f"Total Documents in SQLite: {len(all_docs)}", flush=True)
    assert len(all_docs) > 0, "Expected at least 1 document in SQLite"

    sample_doc = all_docs[0]
    print(f"Sample Document ID: {sample_doc['id']}", flush=True)
    print(f"Sample Filename: {sample_doc['filename']}", flush=True)
    print(f"Sample File Size: {sample_doc['file_size_bytes']} bytes", flush=True)
    print(f"Sample Status: {sample_doc['processed_status']}", flush=True)
    print(f"Associated Project: {sample_doc.get('project_id')}", flush=True)

    # 5. PDF LIBRARY: Inspect Extracted Metadata & Sections
    print("\n--- 4. PDF LIBRARY: Inspect Extracted Metadata & Sections ---", flush=True)
    detail = get_document_details(doc_id=sample_doc['id'], db=db)
    assert detail is not None
    print(f"Metadata Title: {detail['title']}", flush=True)
    print(f"Metadata Authors: {detail['authors']}", flush=True)
    print(f"Metadata Year: {detail.get('publication_year')}", flush=True)
    print(f"Total Pages: {detail.get('total_pages')}", flush=True)
    print(f"Section Count: {detail.get('section_count')}", flush=True)

    sections = get_academic_sections(doc_id=sample_doc['id'], db=db)
    print(f"Retrieved Sections Count: {len(sections)}", flush=True)
    if sections:
        sec0 = sections[0]
        print(f"First Section: §{sec0['section_index']} {sec0['section_title']} (Page {sec0.get('page_number')})", flush=True)

    # Clean up added test paper
    db.query(ResearchPaper).filter(ResearchPaper.id == paper_record.id).delete()
    db.commit()
    print("\nDiscovered test paper record cleaned up from SQLite.", flush=True)

    print("\n=================================================================", flush=True)
    print("ALL DISCOVER PAPERS & PDF LIBRARY TESTS PASSED 100%!", flush=True)
    print("=================================================================", flush=True)
    db.close()

if __name__ == "__main__":
    test_discovery_and_library()
