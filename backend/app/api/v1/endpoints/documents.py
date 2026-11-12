from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List, Optional
import os
import shutil
import uuid
import json
from pathlib import Path
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.schemas import DocumentResponse, ChunkResponse
from backend.app.services.pdf_service import pdf_service
from backend.app.services.vector_service import vector_service

router = APIRouter()

async def process_document_pipeline(doc_id: str, file_path: str, title: str):
    """Background task to extract text, chunks, embed to ChromaDB, and record to SQLite."""
    try:
        # Extract text & structure
        info = pdf_service.extract_document_info(file_path)
        actual_title = info["title"] or title
        authors_json = json.dumps(info["authors"])
        abstract = info["abstract"]
        pages = info["pages"]
        total_pages = info["total_pages"]

        # Generate semantic chunks
        chunks = pdf_service.chunk_document(
            pages,
            chunk_size=settings.MAX_CHUNK_TOKENS,
            overlap=settings.CHUNK_OVERLAP_TOKENS
        )

        # Store chunks in SQLite
        with get_db() as conn:
            cursor = conn.cursor()
            for c in chunks:
                cursor.execute("""
                INSERT INTO document_chunks (id, document_id, chunk_index, section_name, content, token_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (c["id"], doc_id, c["chunk_index"], c["section_name"], c["content"], c["token_count"]))

            # Update document status
            cursor.execute("""
            UPDATE documents
            SET title = ?, authors = ?, abstract = ?, total_pages = ?, processed_status = 'completed', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (actual_title, authors_json, abstract, total_pages, doc_id))

        # Vector Embeddings in ChromaDB
        await vector_service.add_chunks(doc_id, actual_title, chunks)

    except Exception as e:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE documents SET processed_status = 'failed' WHERE id = ?", (doc_id,))
        raise e

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents():
    docs = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT d.id, d.title, d.authors, d.publication_year, d.abstract, d.filename,
               d.file_size_bytes, d.total_pages, d.processed_status, d.created_at, d.updated_at,
               COUNT(c.id) as chunk_count
        FROM documents d
        LEFT JOIN document_chunks c ON d.id = c.document_id
        GROUP BY d.id
        ORDER BY d.created_at DESC
        """)
        rows = cursor.fetchall()
        for r in rows:
            authors = json.loads(r["authors"]) if r["authors"] else []
            docs.append({
                "id": r["id"],
                "title": r["title"],
                "authors": authors,
                "publication_year": r["publication_year"],
                "abstract": r["abstract"],
                "filename": r["filename"],
                "file_size_bytes": r["file_size_bytes"],
                "total_pages": r["total_pages"],
                "processed_status": r["processed_status"],
                "created_at": str(r["created_at"]),
                "updated_at": str(r["updated_at"]),
                "chunk_count": r["chunk_count"]
            })
    return docs

@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported.")

    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}_{Path(file.filename).name}"
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_filename

    # Save to disk streamingly to conserve RAM
    file_size = 0
    with open(file_path, "wb") as buffer:
        while content := await file.read(1024 * 1024):  # 1MB buffer
            file_size += len(content)
            buffer.write(content)

    title_guess = Path(file.filename).stem.replace("_", " ").replace("-", " ").title()

    # Create pending record in SQLite
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO documents (id, title, filename, file_path, file_size_bytes, processed_status)
        VALUES (?, ?, ?, ?, ?, 'processing')
        """, (doc_id, title_guess, file.filename, str(file_path), file_size))

    # Trigger background pipeline
    background_tasks.add_task(process_document_pipeline, doc_id, str(file_path), title_guess)

    return {
        "id": doc_id,
        "title": title_guess,
        "authors": [],
        "publication_year": None,
        "abstract": None,
        "filename": file.filename,
        "file_size_bytes": file_size,
        "total_pages": None,
        "processed_status": "processing",
        "created_at": "Just now",
        "updated_at": "Just now",
        "chunk_count": 0
    }

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT d.*, COUNT(c.id) as chunk_count
        FROM documents d
        LEFT JOIN document_chunks c ON d.id = c.document_id
        WHERE d.id = ?
        GROUP BY d.id
        """, (doc_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Document not found.")

        authors = json.loads(r["authors"]) if r["authors"] else []
        return {
            "id": r["id"],
            "title": r["title"],
            "authors": authors,
            "publication_year": r["publication_year"],
            "abstract": r["abstract"],
            "filename": r["filename"],
            "file_size_bytes": r["file_size_bytes"],
            "total_pages": r["total_pages"],
            "processed_status": r["processed_status"],
            "created_at": str(r["created_at"]),
            "updated_at": str(r["updated_at"]),
            "chunk_count": r["chunk_count"]
        }

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM documents WHERE id = ?", (doc_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Document not found.")

        file_path = r["file_path"]
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

    # Delete chunks from ChromaDB
    vector_service.delete_document_chunks(doc_id)

    # Delete physical file
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    return {"message": "Document deleted successfully", "id": doc_id}

