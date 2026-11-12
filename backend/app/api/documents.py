import logging
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.entities import ResearchPaper, PaperSection
from backend.app.models.document_schemas import (
    DocumentUploadResponse,
    DocumentBatchUploadResponse,
    DocumentSummaryResponse,
    DocumentDetailResponse,
    DocumentSectionSchema,
    DocumentPageSchema,
    ReprocessRequest
)
from backend.app.services.document_processing import document_processor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Document Processing & Understanding"])

def serialize_summary(db: Session, paper: ResearchPaper) -> dict:
    author_names = [a.name for a in paper.authors]
    section_count = db.query(PaperSection).filter(PaperSection.paper_id == paper.id).count()
    return {
        "id": paper.id,
        "project_id": paper.project_id,
        "title": paper.title,
        "authors": author_names,
        "publication_year": paper.publication_year,
        "doi": paper.doi,
        "abstract": paper.abstract,
        "filename": paper.filename,
        "file_size_bytes": paper.file_size_bytes or 0,
        "total_pages": paper.total_pages,
        "processed_status": paper.processed_status,
        "error_message": paper.error_message,
        "created_at": paper.created_at,
        "updated_at": paper.updated_at,
        "section_count": section_count
    }

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_single_pdf(
    file: UploadFile = File(..., description="PDF document to upload and understand"),
    project_id: Optional[str] = Query(None, description="Optional parent project ID"),
    db: Session = Depends(get_db)
):
    """
    Requirement 1, 2, 3, 4, 5:
    Upload a single PDF, validate format and size, save to data/PDFs, and process understanding pipeline.
    """
    doc_id, safe_path, file_size = await document_processor.save_uploaded_file(file)

    # Process understanding (single PDF at a time via internal lock)
    paper = await document_processor.process_pdf_document(
        db=db,
        doc_id=doc_id,
        file_path=safe_path,
        original_filename=file.filename,
        file_size=file_size,
        project_id=project_id
    )

    return DocumentUploadResponse(
        document_id=paper.id,
        filename=paper.filename,
        file_size_bytes=paper.file_size_bytes,
        processed_status=paper.processed_status,
        message="Document uploaded and understood successfully."
    )

@router.post("/batch-upload", response_model=DocumentBatchUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_multiple_pdfs(
    files: List[UploadFile] = File(..., description="List of PDF documents to upload and process"),
    project_id: Optional[str] = Query(None, description="Optional parent project ID"),
    db: Session = Depends(get_db)
):
    """
    Requirement 1: Batch upload multiple PDF files.
    Processes one PDF at a time through the internal lock to safeguard 8 GB RAM.
    """
    uploaded_docs = []
    errors = []

    for f in files:
        try:
            doc_id, safe_path, file_size = await document_processor.save_uploaded_file(f)
            paper = await document_processor.process_pdf_document(
                db=db,
                doc_id=doc_id,
                file_path=safe_path,
                original_filename=f.filename,
                file_size=file_size,
                project_id=project_id
            )
            uploaded_docs.append(DocumentUploadResponse(
                document_id=paper.id,
                filename=paper.filename,
                file_size_bytes=paper.file_size_bytes,
                processed_status=paper.processed_status,
                message="Processed successfully."
            ))
        except Exception as e:
            errors.append(f"Failed '{f.filename}': {str(e)}")

    return DocumentBatchUploadResponse(
        uploaded_count=len(uploaded_docs),
        documents=uploaded_docs,
        errors=errors
    )

@router.get("", response_model=List[DocumentSummaryResponse])
def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: pending, processing, completed, failed"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    db: Session = Depends(get_db)
):
    """
    Requirement: Listing documents with current processing status.
    """
    query = db.query(ResearchPaper)
    if status and isinstance(status, str):
        query = query.filter(ResearchPaper.processed_status == status)
    if project_id and isinstance(project_id, str):
        query = query.filter(ResearchPaper.project_id == project_id)
    
    skip_val = skip if isinstance(skip, int) else getattr(skip, "default", 0)
    limit_val = limit if isinstance(limit, int) else getattr(limit, "default", 50)
    papers = query.order_by(ResearchPaper.created_at.desc()).offset(skip_val).limit(limit_val).all()
    return [serialize_summary(db, p) for p in papers]

@router.get("/{doc_id}", response_model=DocumentDetailResponse)
def get_document_details(
    doc_id: str,
    db: Session = Depends(get_db)
):
    """
    Requirement: Viewing full document metadata and parsed sections.
    """
    paper = db.query(ResearchPaper).filter(ResearchPaper.id == doc_id).first()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found.")

    summary = serialize_summary(db, paper)
    sections = db.query(PaperSection).filter(PaperSection.paper_id == doc_id).order_by(PaperSection.section_index).all()
    
    summary["sections"] = [
        DocumentSectionSchema(
            id=s.id,
            section_index=s.section_index,
            section_title=s.section_title,
            section_type=s.section_type or "content",
            page_number=s.page_number,
            content=s.content,
            token_count=s.token_count,
            created_at=s.created_at
        )
        for s in sections
    ]
    summary["extracted_text_path"] = paper.extracted_text_path
    return summary

@router.get("/{doc_id}/pages", response_model=List[DocumentPageSchema])
def get_document_pages(
    doc_id: str,
    db: Session = Depends(get_db)
):
    """
    Requirement: Retrieve original page-by-page text preserving PDF page numbers.
    """
    paper = db.query(ResearchPaper).filter(ResearchPaper.id == doc_id).first()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found.")

    if not paper.extracted_text_path or not Path(paper.extracted_text_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extracted page text file not found on disk."
        )

    with open(paper.extracted_text_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pages = data.get("pages", [])
    return [
        DocumentPageSchema(
            page_number=p["page_number"],
            text=p["text"],
            character_count=p["character_count"],
            token_count=p["token_count"]
        )
        for p in pages
    ]

@router.get("/{doc_id}/sections", response_model=List[DocumentSectionSchema])
def get_academic_sections(
    doc_id: str,
    db: Session = Depends(get_db)
):
    """
    Requirement: Retrieve the 10 academic sections identified in the document.
    """
    paper = db.query(ResearchPaper).filter(ResearchPaper.id == doc_id).first()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found.")

    sections = db.query(PaperSection).filter(PaperSection.paper_id == doc_id).order_by(PaperSection.section_index).all()
    return [
        DocumentSectionSchema(
            id=s.id,
            section_index=s.section_index,
            section_title=s.section_title,
            section_type=s.section_type or "content",
            page_number=s.page_number,
            content=s.content,
            token_count=s.token_count,
            created_at=s.created_at
        )
        for s in sections
    ]

@router.post("/{doc_id}/reprocess", response_model=DocumentDetailResponse)
async def reprocess_document(
    doc_id: str,
    req: ReprocessRequest = ReprocessRequest(),
    db: Session = Depends(get_db)
):
    """
    Requirement: Support document reprocessing with optional LLM assistance.
    """
    paper = await document_processor.reprocess_document(
        db=db,
        doc_id=doc_id,
        force_llm_assist=req.force_llm_assist
    )
    summary = serialize_summary(db, paper)
    sections = db.query(PaperSection).filter(PaperSection.paper_id == doc_id).order_by(PaperSection.section_index).all()
    summary["sections"] = [
        DocumentSectionSchema(
            id=s.id,
            section_index=s.section_index,
            section_title=s.section_title,
            section_type=s.section_type or "content",
            page_number=s.page_number,
            content=s.content,
            token_count=s.token_count,
            created_at=s.created_at
        )
        for s in sections
    ]
    return summary

@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db)
):
    """
    Requirement: Support document deletion with cascade cleanup of SQLite, ChromaDB, and disk files.
    """
    document_processor.delete_document(db, doc_id)
    return {
        "status": "success",
        "message": f"Document '{doc_id}' and all associated sections/vectors deleted successfully."
    }

