import os
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, UploadFile, status

from backend.app.core.config import settings
from backend.app.models.entities import (
    ResearchProject,
    ResearchPaper,
    Author,
    PaperSection,
    ExtractedEntity,
    ResearchClaim
)
from backend.app.services.pdf_service import pdf_service
from backend.app.services.vector_service import vector_service

logger = logging.getLogger(__name__)

class PaperService:
    @staticmethod
    def get_paper_by_id(db: Session, paper_id: str) -> Optional[ResearchPaper]:
        """Retrieves a research paper by its UUID."""
        return db.query(ResearchPaper).filter(ResearchPaper.id == paper_id).first()

    @staticmethod
    def list_papers(
        db: Session,
        project_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[str] = None
    ) -> List[ResearchPaper]:
        """Lists papers filtered by project or status."""
        query = db.query(ResearchPaper)
        if project_id:
            query = query.filter(ResearchPaper.project_id == project_id)
        if status_filter:
            query = query.filter(ResearchPaper.processed_status == status_filter)
        return query.order_by(ResearchPaper.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    async def ingest_paper_pdf(
        db: Session,
        project_id: str,
        file: UploadFile
    ) -> ResearchPaper:
        """
        Processes and indexes a research PDF:
        1. Checks project validity.
        2. Saves PDF file to data/uploads.
        3. PyMuPDF text & section extraction.
        4. Saves ResearchPaper, Authors, and PaperSections to SQLite.
        5. Generates nomic-embed-text embeddings & stores in ChromaDB.
        """
        # 1. Verify project exists
        project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target project with ID '{project_id}' not found."
            )

        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF documents are supported for ingestion."
            )

        # 2. Save file streamingly to disk
        paper_id = str(uuid.uuid4())
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{paper_id}_{Path(file.filename).name}"
        file_path = upload_dir / safe_filename

        file_size = 0
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB buffer
                file_size += len(chunk)
                buffer.write(chunk)

        try:
            # 3. Extract text, metadata & sections via PyMuPDF
            extracted_info = pdf_service.extract_document_info(str(file_path))
            title = extracted_info.get("title") or Path(file.filename).stem.replace("_", " ").title()
            abstract = extracted_info.get("abstract")
            total_pages = extracted_info.get("total_pages", 1)
            raw_authors = extracted_info.get("authors", [])

            # Generate semantic chunks for sections
            chunks = pdf_service.chunk_document(
                extracted_info["pages"],
                chunk_size=settings.MAX_CHUNK_TOKENS,
                overlap=settings.CHUNK_OVERLAP_TOKENS
            )

            # 4. Save ResearchPaper in SQLite
            db_paper = ResearchPaper(
                id=paper_id,
                project_id=project_id,
                title=title,
                doi=None,
                publication_year=datetime.now().year,
                abstract=abstract,
                filename=file.filename,
                file_path=str(file_path),
                file_size_bytes=file_size,
                total_pages=total_pages,
                processed_status="completed"
            )
            db.add(db_paper)
            db.flush()

            # 5. Link or create Authors
            for author_name in raw_authors:
                clean_name = author_name.strip()
                if not clean_name:
                    continue
                author = db.query(Author).filter(Author.name == clean_name).first()
                if not author:
                    author = Author(name=clean_name)
                    db.add(author)
                    db.flush()
                if author not in db_paper.authors:
                    db_paper.authors.append(author)

            # 6. Save PaperSections
            for c in chunks:
                section_type = "content"
                s_name_lower = c["section_name"].lower()
                if "abstract" in s_name_lower:
                    section_type = "abstract"
                elif "intro" in s_name_lower:
                    section_type = "introduction"
                elif "method" in s_name_lower:
                    section_type = "methodology"
                elif "result" in s_name_lower or "eval" in s_name_lower:
                    section_type = "results"
                elif "conclu" in s_name_lower:
                    section_type = "conclusion"

                section = PaperSection(
                    id=c["id"],
                    paper_id=paper_id,
                    section_index=c["chunk_index"],
                    section_title=c["section_name"],
                    section_type=section_type,
                    content=c["content"],
                    token_count=c["token_count"]
                )
                db.add(section)

            db.commit()
            db.refresh(db_paper)

            # 7. Index in ChromaDB using nomic-embed-text
            await vector_service.add_chunks(paper_id, title, chunks)
            logger.info(f"Ingested paper '{title}' with {len(chunks)} sections into project {project_id}.")
            return db_paper

        except Exception as e:
            db.rollback()
            # Clean up uploaded file on failure
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass
            logger.error(f"Paper ingestion failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to ingest paper PDF: {str(e)}"
            )

    @staticmethod
    def get_paper_sections(db: Session, paper_id: str) -> List[PaperSection]:
        """Retrieves all parsed sections for a paper."""
        paper = PaperService.get_paper_by_id(db, paper_id)
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paper with ID '{paper_id}' not found."
            )
        return db.query(PaperSection).filter(PaperSection.paper_id == paper_id).order_by(PaperSection.section_index).all()

    @staticmethod
    def delete_paper(db: Session, paper_id: str) -> bool:
        """Deletes paper, its sections, ChromaDB vectors, and local file."""
        paper = PaperService.get_paper_by_id(db, paper_id)
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paper with ID '{paper_id}' not found."
            )

        file_path = paper.file_path

        try:
            # Delete from SQLite
            db.delete(paper)
            db.commit()

            # Delete from ChromaDB
            vector_service.delete_document_chunks(paper_id)

            # Delete physical file
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass

            logger.info(f"Deleted paper {paper_id} and purged vector embeddings.")
            return True
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error deleting paper {paper_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while deleting paper: {str(e)}"
            )

    @staticmethod
    def serialize_paper(db: Session, paper: ResearchPaper) -> Dict[str, Any]:
        """Formats research paper with authors and count statistics."""
        author_names = [a.name for a in paper.authors]
        section_count = db.query(PaperSection).filter(PaperSection.paper_id == paper.id).count()
        entity_count = db.query(ExtractedEntity).filter(ExtractedEntity.paper_id == paper.id).count()
        claim_count = db.query(ResearchClaim).filter(ResearchClaim.paper_id == paper.id).count()

        return {
            "id": paper.id,
            "project_id": paper.project_id,
            "title": paper.title,
            "doi": paper.doi,
            "authors": author_names,
            "publication_year": paper.publication_year,
            "journal_or_conference": paper.journal_or_conference,
            "abstract": paper.abstract,
            "filename": paper.filename,
            "file_size_bytes": paper.file_size_bytes,
            "total_pages": paper.total_pages,
            "processed_status": paper.processed_status,
            "created_at": paper.created_at,
            "updated_at": paper.updated_at,
            "section_count": section_count,
            "entity_count": entity_count,
            "claim_count": claim_count
        }

paper_service = PaperService()
