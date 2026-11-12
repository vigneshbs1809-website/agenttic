import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.discovery_schemas import (
    DiscoverySearchRequest,
    DiscoverySearchResponse,
    AddPaperToProjectRequest,
    AddPaperToProjectResponse,
    ManualAttachPDFResponse
)
from backend.app.services.discovery_agent import discovery_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/discovery", tags=["Research Discovery Agent"])

@router.post("/search", response_model=DiscoverySearchResponse)
async def search_academic_literature(req: DiscoverySearchRequest):
    """
    Research Discovery Agent: Search academic literature across OpenAlex, arXiv, and Semantic Scholar.
    - Extracts title, abstract, authors, DOI, year, and URLs.
    - Detects cross-source duplicates and merges metadata.
    - Filters by year, author, and open-access status.
    - Ranks papers by multi-factor relevance.
    - Gracefully handles API downtime, rate limits, or network failures.
    """
    papers, statuses = await discovery_agent.execute_discovery_search(req)

    return DiscoverySearchResponse(
        topic=req.topic,
        total_found=len(papers),
        sources_queried=req.sources or ["openalex", "arxiv", "semanticscholar"],
        source_statuses=statuses,
        papers=papers
    )

@router.post("/add-to-project", response_model=AddPaperToProjectResponse)
async def add_discovered_paper_to_project(
    req: AddPaperToProjectRequest,
    db: Session = Depends(get_db)
):
    """
    Adds a discovered paper to an existing research project.
    - If 'download_pdf' is True and paper has an open-access PDF link, automatically downloads it.
    - If 'process_document' is True, runs section extraction and indexes chunks in ChromaDB.
    - If downloading is unavailable, catalogs the paper metadata with processed_status='metadata_only'.
    """
    paper_record, pdf_downloaded, msg = await discovery_agent.add_paper_to_project(
        db=db,
        project_id=req.project_id,
        paper=req.paper,
        download_pdf=req.download_pdf,
        process_document=req.process_document
    )

    return AddPaperToProjectResponse(
        paper_id=paper_record.id,
        project_id=req.project_id,
        title=paper_record.title,
        doi=paper_record.doi,
        pdf_downloaded=pdf_downloaded,
        processed_status=paper_record.processed_status,
        message=msg
    )

@router.post("/attach-pdf/{paper_id}", response_model=ManualAttachPDFResponse)
async def attach_manual_pdf_to_paper(
    paper_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Allows researchers to manually upload a PDF for a paper previously saved as metadata-only.
    Validates PDF format, extracts academic sections, and indexes chunks in ChromaDB.
    """
    processed_paper = await discovery_agent.attach_manual_pdf(
        db=db,
        paper_id=paper_id,
        file=file
    )

    return ManualAttachPDFResponse(
        paper_id=processed_paper.id,
        title=processed_paper.title,
        processed_status=processed_paper.processed_status,
        file_path=processed_paper.file_path or "",
        total_pages=processed_paper.total_pages,
        section_count=len(processed_paper.sections),
        message=f"Manual PDF successfully attached, parsed ({len(processed_paper.sections)} sections), and indexed in vector database."
    )

