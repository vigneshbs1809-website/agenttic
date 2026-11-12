import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.paper_schemas import PaperResponse, SectionResponse
from backend.app.services.paper_service import paper_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Research Papers"])

@router.post("/api/projects/{project_id}/papers/upload", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def upload_paper_to_project(
    project_id: str,
    file: UploadFile = File(..., description="PDF research paper to ingest"),
    db: Session = Depends(get_db)
):
    """Uploads and indexes a scientific research paper PDF within a project."""
    paper = await paper_service.ingest_paper_pdf(db, project_id, file)
    return paper_service.serialize_paper(db, paper)

@router.get("/api/projects/{project_id}/papers", response_model=List[PaperResponse])
def list_project_papers(
    project_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Lists all papers uploaded to a specific project."""
    papers = paper_service.list_papers(db, project_id=project_id, skip=skip, limit=limit, status_filter=status_filter)
    return [paper_service.serialize_paper(db, p) for p in papers]

@router.get("/api/papers", response_model=List[PaperResponse])
def list_all_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Lists all research papers across all projects."""
    papers = paper_service.list_papers(db, skip=skip, limit=limit, status_filter=status_filter)
    return [paper_service.serialize_paper(db, p) for p in papers]

@router.get("/api/papers/{paper_id}", response_model=PaperResponse)
def get_paper(
    paper_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves metadata for a specific research paper."""
    paper = paper_service.get_paper_by_id(db, paper_id)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper with ID '{paper_id}' not found."
        )
    return paper_service.serialize_paper(db, paper)

@router.get("/api/papers/{paper_id}/sections", response_model=List[SectionResponse])
def get_paper_sections(
    paper_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves all parsed sections for a paper."""
    return paper_service.get_paper_sections(db, paper_id)

@router.delete("/api/papers/{paper_id}", status_code=status.HTTP_200_OK)
def delete_paper(
    paper_id: str,
    db: Session = Depends(get_db)
):
    """Deletes paper, its sections, its vector embeddings from ChromaDB, and PDF file."""
    paper_service.delete_paper(db, paper_id)
    return {
        "status": "success",
        "message": f"Paper '{paper_id}' and vector embeddings purged successfully."
    }

