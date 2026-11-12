import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.app.core.config import settings
from backend.app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

class ChromaService:
    def __init__(self):
        self.persist_path = Path(settings.CHROMA_PERSIST_DIR)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_path),
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
        )
        self.collection_name = "literature_chunks"
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=None
            )
        return self._collection

    def paper_is_indexed(self, paper_id: str) -> bool:
        """Requirement 10: Checks if a paper is already indexed to prevent duplicate indexing."""
        existing = self.collection.get(where={"paper_id": paper_id}, limit=1)
        return bool(existing and existing.get("ids"))

    async def index_chunks(
        self,
        paper_id: str,
        paper_title: str,
        chunks: List[Dict[str, Any]],
        project_id: Optional[str] = None,
        force_reindex: bool = False
    ) -> int:
        """
        Requirement 4, 10, 11:
        Indexes chunks into persistent ChromaDB with duplicate prevention and re-indexing support.
        """
        if not chunks:
            return 0

        # Duplicate indexing check
        if self.paper_is_indexed(paper_id):
            if force_reindex:
                logger.info(f"Re-indexing paper '{paper_id}': removing old chunks first.")
                self.delete_paper_chunks(paper_id)
            else:
                logger.info(f"Paper '{paper_id}' already indexed. Skipping duplicate insertion.")
                return 0

        # Prepare batch vectors
        texts = [c["content"] for c in chunks]
        ids = [c["chunk_id"] for c in chunks]
        metadatas = [
            {
                "paper_id": paper_id,
                "project_id": str(project_id or c.get("project_id", "default")),
                "paper_title": paper_title[:150],
                "chunk_index": int(c.get("chunk_index", 0)),
                "section_title": str(c.get("section_title", "General")),
                "section_type": str(c.get("section_type", "content")),
                "page_number": int(c.get("page_number", 1))
            }
            for c in chunks
        ]

        # Generate embeddings one batch at a time
        embeddings = await embedding_service.embed_texts(texts)

        # Insert into ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        logger.info(f"Indexed {len(chunks)} chunks into ChromaDB for paper '{paper_title}' ({paper_id}).")
        return len(chunks)

    def delete_paper_chunks(self, paper_id: str) -> bool:
        """Requirement 12: Removes all vectors for a paper from ChromaDB."""
        try:
            self.collection.delete(where={"paper_id": paper_id})
            logger.info(f"Deleted chunks from ChromaDB for paper {paper_id}")
            return True
        except Exception as e:
            logger.warning(f"Error deleting chunks from ChromaDB: {e}")
            return False

    def query_semantic(
        self,
        query_embedding: List[float],
        top_k: int = 4,
        project_id: Optional[str] = None,
        paper_id: Optional[str] = None,
        paper_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Requirement 5, 8, 9:
        Semantic similarity search with project/paper filtering and normalized similarity scores.
        """
        where_conditions = []
        if project_id:
            where_conditions.append({"project_id": project_id})
        if paper_id:
            where_conditions.append({"paper_id": paper_id})
        elif paper_ids and len(paper_ids) == 1:
            where_conditions.append({"paper_id": paper_ids[0]})
        elif paper_ids and len(paper_ids) > 1:
            where_conditions.append({"paper_id": {"$in": paper_ids}})

        where_clause = None
        if len(where_conditions) == 1:
            where_clause = where_conditions[0]
        elif len(where_conditions) > 1:
            where_clause = {"$and": where_conditions}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause
        )

        passages = []
        if results and "documents" in results and results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]

            for i in range(len(docs)):
                dist = distances[i] if i < len(distances) else 0.5
                # Normalize cosine distance to similarity score in [0.0, 1.0]
                similarity = round(max(0.0, min(1.0, 1.0 - dist)), 4) if dist <= 1.0 else round(1.0 / (1.0 + dist), 4)
                m = metas[i] if metas and i < len(metas) else {}
                passages.append({
                    "chunk_id": ids[i],
                    "paper_id": str(m.get("paper_id") or m.get("document_id") or "unknown"),
                    "paper_title": str(m.get("paper_title") or m.get("document_title") or "Untitled Document"),
                    "page_number": int(m.get("page_number", 1) or 1),
                    "section_name": str(m.get("section_title") or m.get("section_name") or "General"),
                    "original_text": docs[i],
                    "retrieval_score": similarity,
                    "retrieval_method": "semantic"
                })

        return passages

    def get_all_chunks_for_filtering(
        self,
        project_id: Optional[str] = None,
        paper_id: Optional[str] = None,
        paper_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves raw chunks for keyword search / BM25 evaluation."""
        where_conditions = []
        if project_id:
            where_conditions.append({"project_id": project_id})
        if paper_id:
            where_conditions.append({"paper_id": paper_id})
        elif paper_ids and len(paper_ids) == 1:
            where_conditions.append({"paper_id": paper_ids[0]})
        elif paper_ids and len(paper_ids) > 1:
            where_conditions.append({"paper_id": {"$in": paper_ids}})

        where_clause = None
        if len(where_conditions) == 1:
            where_clause = where_conditions[0]
        elif len(where_conditions) > 1:
            where_clause = {"$and": where_conditions}

        if where_clause:
            res = self.collection.get(where=where_clause, include=["documents", "metadatas"])
        else:
            res = self.collection.get(include=["documents", "metadatas"])

        chunks = []
        if res and res.get("documents"):
            for i in range(len(res["documents"])):
                m = res["metadatas"][i] if res.get("metadatas") and i < len(res["metadatas"]) else {}
                chunks.append({
                    "chunk_id": res["ids"][i],
                    "paper_id": str(m.get("paper_id") or m.get("document_id") or "unknown"),
                    "paper_title": str(m.get("paper_title") or m.get("document_title") or "Untitled Document"),
                    "page_number": int(m.get("page_number", 1) or 1),
                    "section_name": str(m.get("section_title") or m.get("section_name") or "General"),
                    "original_text": res["documents"][i],
                })
        return chunks

chroma_service = ChromaService()
