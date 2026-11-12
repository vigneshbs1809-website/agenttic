import os
import re
import json
import uuid
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import pymupdf
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status

from backend.app.core.config import settings
from backend.app.models.entities import ResearchProject, ResearchPaper, Author, PaperSection
from backend.app.services.pdf_service import pdf_service
from backend.app.services.ollama_service import ollama_service
from backend.app.services.vector_service import vector_service
from backend.app.services.chunking import chunker
from backend.app.services.chroma_service import chroma_service

logger = logging.getLogger(__name__)

class DocumentProcessingService:
    def __init__(self):
        # Requirement: Process one PDF at a time to protect system memory (8 GB RAM)
        self._processing_lock = asyncio.Lock()
        self.pdf_dir = Path(settings.PDF_STORAGE_DIR)
        self.extracted_dir = Path(settings.EXTRACTED_STORAGE_DIR)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_dir.mkdir(parents=True, exist_ok=True)

    async def save_uploaded_file(self, file: UploadFile, max_size_bytes: int = 50 * 1024 * 1024) -> Tuple[str, Path, int]:
        """
        Validates file extension, magic bytes, and size, saving to data/PDFs/{doc_id}.pdf.
        """
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension for '{file.filename}'. Only .pdf is allowed."
            )

        doc_id = str(uuid.uuid4())
        safe_path = self.pdf_dir / f"{doc_id}.pdf"

        file_bytes = await file.read()
        file_size = len(file_bytes)

        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{file.filename}' exceeds {max_size_bytes / (1024*1024)} MB limit."
            )

        if not pdf_service.validate_pdf(file_bytes):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' is corrupted or not a valid PDF document."
            )

        with open(safe_path, "wb") as f:
            f.write(file_bytes)

        return doc_id, safe_path, file_size

    async def process_pdf_document(
        self,
        db: Session,
        doc_id: str,
        file_path: Path,
        original_filename: str,
        file_size: int,
        project_id: Optional[str] = None,
        force_llm_assist: bool = False
    ) -> ResearchPaper:
        """
        Serial execution pipeline for document understanding:
        1. PyMuPDF page-by-page extraction preserving 1-indexed page numbers.
        2. Rule-based metadata extraction (title, authors, abstract, year).
        3. Targeted local LLM assistance if rule-based misses core metadata.
        4. Identification of the 10 canonical academic sections.
        5. SQLite persistence of paper, authors, and sections.
        6. Persistent JSON storage of extracted page texts in data/extracted/{doc_id}.json.
        7. Vector indexing in ChromaDB via nomic-embed-text.
        """
        async with self._processing_lock:
            # Ensure a valid project_id exists (Default Research Library if not provided)
            if not project_id:
                default_proj = db.query(ResearchProject).filter(ResearchProject.title == "Default Research Library").first()
                if not default_proj:
                    default_proj = ResearchProject(
                        title="Default Research Library",
                        description="Global repository for standalone uploaded papers and general literature.",
                        domain="General Science",
                        status="active"
                    )
                    db.add(default_proj)
                    db.flush()
                project_id = default_proj.id

            # Check or create initial paper record in SQLite
            paper = db.query(ResearchPaper).filter(ResearchPaper.id == doc_id).first()
            if not paper:
                paper = ResearchPaper(
                    id=doc_id,
                    project_id=project_id,
                    title=Path(original_filename).stem.replace("_", " ").title(),
                    filename=original_filename,
                    file_path=str(file_path),
                    file_size_bytes=file_size,
                    processed_status="processing"
                )
                db.add(paper)
                db.commit()
                db.refresh(paper)
            else:
                paper.processed_status = "processing"
                paper.error_message = None
                db.commit()

            try:
                # 1. Open document with PyMuPDF
                doc = pymupdf.open(str(file_path))
                total_pages = len(doc)

                # 2. Extract page-by-page text preserving original page numbers
                pages_data = pdf_service.extract_pages(doc)

                # 3. Rule-based metadata extraction
                metadata = pdf_service.extract_rule_based_metadata(doc, original_filename)
                title = metadata.get("title")
                authors = metadata.get("authors") or []
                abstract = metadata.get("abstract")
                year = metadata.get("publication_year")

                # 4. Local LLM assistance when necessary (never sends entire PDF)
                # If title or abstract is missing or force_llm_assist is requested:
                needs_llm_assist = force_llm_assist or (not title) or (not abstract) or (len(authors) == 0)
                if needs_llm_assist and len(pages_data) > 0:
                    try:
                        # Extract at most first 2 pages text (~800 words) for metadata disambiguation
                        header_sample = "\n".join([p["text"] for p in pages_data[:2]])[:2500]
                        prompt = f"""Extract academic paper metadata from this first page excerpt:
{header_sample}

Respond strictly in valid JSON with these keys:
{{"title": "...", "authors": ["..."], "abstract": "...", "publication_year": 2024}}"""

                        llm_res = await ollama_service.generate_text(prompt=prompt, override_max_tokens=300)
                        raw_json_str = llm_res.get("response", "")
                        
                        # Parse JSON from model output
                        json_match = re.search(r"\{.*\}", raw_json_str, re.DOTALL)
                        if json_match:
                            parsed_meta = json.loads(json_match.group(0))
                            if not title and parsed_meta.get("title"):
                                title = parsed_meta["title"]
                            if (not authors or len(authors) == 0) and parsed_meta.get("authors"):
                                authors = parsed_meta["authors"]
                            if not abstract and parsed_meta.get("abstract"):
                                abstract = parsed_meta["abstract"]
                            if not year and parsed_meta.get("publication_year"):
                                year = int(parsed_meta["publication_year"])
                    except Exception as llm_err:
                        logger.warning(f"Optional LLM assistance skipped or non-critical failure: {llm_err}")

                # 5. Identify the 10 academic sections
                sections = pdf_service.identify_academic_sections(pages_data)
                doc.close()

                # 6. Save persistent extracted JSON file in data/extracted/{doc_id}.json
                extracted_file_path = self.extracted_dir / f"{doc_id}.json"
                extracted_payload = {
                    "document_id": doc_id,
                    "filename": original_filename,
                    "total_pages": total_pages,
                    "metadata": {
                        "title": title,
                        "authors": authors,
                        "abstract": abstract,
                        "publication_year": year
                    },
                    "pages": pages_data,
                    "sections": [
                        {
                            "section_index": s["section_index"],
                            "section_title": s["section_title"],
                            "section_type": s["section_type"],
                            "page_number": s["page_number"],
                            "token_count": s["token_count"]
                        }
                        for s in sections
                    ]
                }
                with open(extracted_file_path, "w", encoding="utf-8") as ef:
                    json.dump(extracted_payload, ef, indent=2, ensure_ascii=False)

                # 7. Update SQLite ResearchPaper
                paper.title = title or Path(original_filename).stem.replace("_", " ").title()
                paper.abstract = abstract
                paper.publication_year = year or datetime.now().year
                paper.total_pages = total_pages
                paper.extracted_text_path = str(extracted_file_path)
                paper.processed_status = "completed"
                paper.error_message = None

                # 8. Link or create Authors in SQLite
                for author_name in authors:
                    clean_name = str(author_name).strip()
                    if len(clean_name) > 1:
                        author = db.query(Author).filter(Author.name == clean_name).first()
                        if not author:
                            author = Author(name=clean_name)
                            db.add(author)
                            db.flush()
                        if author not in paper.authors:
                            paper.authors.append(author)

                # 9. Clean existing sections if reprocessing, then insert PaperSections
                db.query(PaperSection).filter(PaperSection.paper_id == doc_id).delete()
                for s in sections:
                    paper_sec = PaperSection(
                        id=s["id"],
                        paper_id=doc_id,
                        section_index=s["section_index"],
                        section_title=s["section_title"],
                        section_type=s["section_type"],
                        page_number=s["page_number"],
                        content=s["content"],
                        token_count=s["token_count"]
                    )
                    db.add(paper_sec)

                db.commit()
                db.refresh(paper)

                # 10. Generate section-aware chunks and index in ChromaDB via nomic-embed-text
                try:
                    chunks = chunker.chunk_paper_sections(
                        paper_id=doc_id,
                        paper_title=paper.title,
                        sections=sections,
                        project_id=paper.project_id
                    )
                    await chroma_service.index_chunks(
                        paper_id=doc_id,
                        paper_title=paper.title,
                        chunks=chunks,
                        project_id=paper.project_id,
                        force_reindex=True
                    )
                except Exception as vec_err:
                    logger.warning(f"ChromaDB indexing warning: {vec_err}")

                logger.info(f"Successfully processed document '{paper.title}' ({doc_id}) with {len(sections)} sections.")
                return paper

            except Exception as e:
                db.rollback()
                paper.processed_status = "failed"
                paper.error_message = str(e)
                db.commit()
                logger.error(f"Failed processing document {doc_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Processing failed for document {doc_id}: {str(e)}"
                )

    async def reprocess_document(self, db: Session, doc_id: str, force_llm_assist: bool = False) -> ResearchPaper:
        """Reprocesses an existing PDF document stored on disk."""
        paper = db.query(ResearchPaper).filter(ResearchPaper.id == doc_id).first()
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found.")

        file_path = Path(paper.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Physical PDF file missing at {file_path}"
            )

        return await self.process_pdf_document(
            db=db,
            doc_id=doc_id,
            file_path=file_path,
            original_filename=paper.filename,
            file_size=paper.file_size_bytes or file_path.stat().st_size,
            project_id=paper.project_id,
            force_llm_assist=force_llm_assist
        )

    def delete_document(self, db: Session, doc_id: str) -> bool:
        """Cascade deletes document from SQLite, ChromaDB, extracted JSON, and data/PDFs."""
        paper = db.query(ResearchPaper).filter(ResearchPaper.id == doc_id).first()
        if not paper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found.")

        pdf_path = Path(paper.file_path) if paper.file_path else None
        extracted_path = Path(paper.extracted_text_path) if paper.extracted_text_path else None

        # 1. Delete from SQLite (cascades to sections, entities, claims)
        db.delete(paper)
        db.commit()

        # 2. Delete from ChromaDB
        try:
            chroma_service.delete_paper_chunks(doc_id)
            vector_service.delete_document_chunks(doc_id)
        except Exception:
            pass

        # 3. Delete physical PDF
        if pdf_path and pdf_path.exists():
            try:
                pdf_path.unlink()
            except Exception:
                pass

        # 4. Delete extracted JSON
        if extracted_path and extracted_path.exists():
            try:
                extracted_path.unlink()
            except Exception:
                pass

        return True

document_processor = DocumentProcessingService()
