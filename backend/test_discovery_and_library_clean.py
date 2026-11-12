import os
import sys
sys.path.insert(0, os.path.abspath("."))
import json

from backend.app.core.database import SessionLocal
from backend.app.models.entities import ResearchPaper, ResearchProject, PaperSection, Author
from backend.app.models.discovery_schemas import DiscoverySearchRequest, DiscoveredPaper
from backend.app.services.discovery_agent import discovery_agent
from backend.app.api.documents import list_documents, get_document_details, get_academic_sections

def run_clean_tests():
    db = SessionLocal()
    print("=================================================================", flush=True)
    print("TESTING DISCOVER PAPERS & PDF LIBRARY", flush=True)
    print("=================================================================", flush=True)

    # 1. Setup or retrieve test project
    test_project = db.query(ResearchProject).first()
    assert test_project is not None, "No research projects found in SQLite"
    project_id = test_project.id
    print(f"Target Research Project: {project_id} ('{test_project.title}')", flush=True)

    # -------------------------------------------------------------------------
    # PART 1: DISCOVER PAPERS
    # -------------------------------------------------------------------------
    print("\n--- 1. DISCOVER PAPERS: Search Request & Multi-Filter Validation ---", flush=True)
    req = DiscoverySearchRequest(
        topic="Multi-Agent Reinforcement Learning",
        keywords=["traffic", "graph"],
        sources=["openalex", "arxiv", "semanticscholar"],
        year_start=2021,
        year_end=2026,
        author="Bengio",
        open_access_only=True,
        sort_by="relevance"
    )
    assert req.topic == "Multi-Agent Reinforcement Learning"
    assert "arxiv" in req.sources
    assert req.year_start == 2021
    assert req.open_access_only is True
    print("DiscoverySearchRequest validated with full filters (sources, year, author, open access).", flush=True)

    print("\n--- 2. DISCOVER PAPERS: Deduplication, Filtering & Relevance Ranking ---", flush=True)
    sample_papers = [
        DiscoveredPaper(
            id="doi:10.1145/test.1",
            title="Graph Attention Routing for Congested Multi-Agent Swarms",
            abstract="We propose a spatial attention mechanism for cooperative routing.",
            authors=["Alice Bengio", "Bob Chen"],
            doi="10.1145/test.1",
            year=2024,
            is_open_access=True,
            sources=["arxiv", "openalex"],
            citation_count=35,
            relevance_score=0.0
        ),
        DiscoveredPaper(
            id="doi:10.1145/test.1_dup",
            title="Graph Attention Routing for Congested Multi-Agent Swarms",
            abstract="Duplicate entry from Semantic Scholar.",
            authors=["Alice Bengio", "Bob Chen"],
            doi="10.1145/test.1",
            year=2024,
            is_open_access=True,
            sources=["semanticscholar"],
            citation_count=35,
            relevance_score=0.0
        ),
        DiscoveredPaper(
            id="doi:10.1145/test.2",
            title="Decentralized Collision Avoidance in Dense Robotics",
            abstract="Robotics obstacle avoidance using deep Q-learning.",
            authors=["Charlie Davis"],
            doi="10.1145/test.2",
            year=2022,
            is_open_access=False,
            sources=["openalex"],
            citation_count=10,
            relevance_score=0.0
        )
    ]

    # Test Deduplication
    deduped = discovery_agent.deduplicate_papers(sample_papers)
    print(f"Deduplication: {len(sample_papers)} papers -> {len(deduped)} unique papers.", flush=True)
    assert len(deduped) == 2, f"Expected 2 deduped papers, got {len(deduped)}"

    # Test Filtering
    filtered = discovery_agent.filter_papers(
        papers=deduped,
        year_start=2023,
        year_end=2025,
        author="Bengio",
        open_access_only=True
    )
    print(f"Filtered (Year 2023-2025, Author Bengio, OA True): {len(filtered)} papers.", flush=True)
    assert len(filtered) == 1, f"Expected 1 filtered paper, got {len(filtered)}"
    assert filtered[0].title == "Graph Attention Routing for Congested Multi-Agent Swarms"

    # Test Relevance Ranking
    ranked = discovery_agent.rank_papers(
        papers=filtered,
        query="Graph Attention Routing Multi-Agent",
        sort_by="relevance"
    )
    print(f"Ranked Relevance Score: {ranked[0].relevance_score:.2f}", flush=True)
    assert ranked[0].relevance_score > 0.5

    print("\n--- 3. DISCOVER PAPERS: Add Paper to Project in SQLite ---", flush=True)
    paper_to_add = ranked[0]
    doc_id = "test-disc-998877"
    
    # Clean up prior test if exists
    db.query(ResearchPaper).filter(ResearchPaper.id == doc_id).delete()
    db.commit()

    paper_record = ResearchPaper(
        id=doc_id,
        project_id=project_id,
        title=paper_to_add.title,
        doi=paper_to_add.doi,
        publication_year=paper_to_add.year,
        journal_or_conference="ICML 2024",
        abstract=paper_to_add.abstract,
        filename=None,
        file_path=None,
        file_size_bytes=None,
        processed_status="metadata_only",
        error_message=None
    )
    db.add(paper_record)
    
    # Link Authors
    for auth in paper_to_add.authors:
        author_obj = db.query(Author).filter(Author.name == auth).first()
        if not author_obj:
            author_obj = Author(name=auth)
            db.add(author_obj)
            db.flush()
        paper_record.authors.append(author_obj)

    db.commit()
    db.refresh(paper_record)
    print(f"Paper added to project '{test_project.title}' successfully:", flush=True)
    print(f"  - ID: {paper_record.id}", flush=True)
    print(f"  - Title: {paper_record.title}", flush=True)
    print(f"  - DOI: {paper_record.doi}", flush=True)
    print(f"  - Status: {paper_record.processed_status}", flush=True)
    print(f"  - Authors: {[a.name for a in paper_record.authors]}", flush=True)

    # -------------------------------------------------------------------------
    # PART 2: PDF LIBRARY
    # -------------------------------------------------------------------------
    print("\n--- 4. PDF LIBRARY: List & Filter Documents ---", flush=True)
    all_docs = list_documents(project_id=project_id, db=db)
    print(f"Documents in Project: {len(all_docs)}", flush=True)
    assert any(d["id"] == doc_id for d in all_docs)

    print("\n--- 5. PDF LIBRARY: View Extracted Metadata ---", flush=True)
    details = get_document_details(doc_id=doc_id, db=db)
    print(f"Metadata Title: {details['title']}", flush=True)
    print(f"Metadata DOI: {details['doi']}", flush=True)
    print(f"Metadata Authors: {details['authors']}", flush=True)
    print(f"Metadata Year: {details['publication_year']}", flush=True)
    print(f"Processing Status: {details['processed_status']}", flush=True)

    print("\n--- 6. PDF LIBRARY: View Extracted Sections ---", flush=True)
    # Check sections on an existing completed paper
    completed_paper = db.query(ResearchPaper).filter(ResearchPaper.processed_status == "completed").first()
    if completed_paper:
        secs = get_academic_sections(doc_id=completed_paper.id, db=db)
        print(f"Sections for '{completed_paper.title[:40]}...': {len(secs)} sections extracted", flush=True)
        if secs:
            s0 = secs[0]
            print(f"  - §{s0.section_index} {s0.section_title} (Page {s0.page_number})", flush=True)
            print(f"  - Content preview: {s0.content[:70]}...", flush=True)

    # Clean up test paper
    db.query(ResearchPaper).filter(ResearchPaper.id == doc_id).delete()
    db.commit()
    print("\nCleaned up test paper from SQLite.", flush=True)

    print("\n=================================================================", flush=True)
    print("ALL DISCOVER PAPERS & PDF LIBRARY TESTS PASSED 100%!", flush=True)
    print("=================================================================", flush=True)
    db.close()

if __name__ == "__main__":
    run_clean_tests()
