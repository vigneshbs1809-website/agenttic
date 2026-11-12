import chromadb
from chromadb.config import Settings as ChromaSettings
import logging
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        # Configure Chroma persistent client with telemetry disabled for offline performance
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
        )
        self.collection_name = "literature_chunks"
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    async def add_chunks(self, document_id: str, document_title: str, chunks: List[Dict[str, Any]]):
        """Generates embeddings via Ollama and indexes them into ChromaDB."""
        if not chunks:
            return

        texts = [c["content"] for c in chunks]
        chunk_ids = [c["id"] for c in chunks]
        metadatas = [
            {
                "document_id": document_id,
                "document_title": document_title[:100],
                "chunk_index": c.get("chunk_index", c.get("section_index", 0)),
                "section_name": c.get("section_name", c.get("section_title", "Content"))
            }
            for c in chunks
        ]

        # Batch embeddings in chunks of 16 to respect memory
        batch_size = 16
        for i in range(0, len(chunks), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_ids = chunk_ids[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]

            embeddings = await ollama_service.get_embeddings(batch_texts)

            self.collection.add(
                ids=batch_ids,
                embeddings=embeddings,
                documents=batch_texts,
                metadatas=batch_meta
            )
        logger.info(f"Indexed {len(chunks)} chunks into ChromaDB for document {document_id}")

    async def query_similar(
        self,
        query_text: str,
        top_k: int = 4,
        document_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Queries nearest literature chunks using nomic-embed-text embedding."""
        query_embeddings = await ollama_service.get_embeddings([query_text])
        if not query_embeddings or len(query_embeddings[0]) == 0:
            return []

        where_clause = None
        if document_filter and len(document_filter) == 1:
            where_clause = {"document_id": document_filter[0]}
        elif document_filter and len(document_filter) > 1:
            where_clause = {"document_id": {"$in": document_filter}}

        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=top_k,
            where=where_clause
        )

        formatted = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]

            for idx in range(len(docs)):
                dist = distances[idx] if idx < len(distances) else 0.5
                score = round(1.0 - dist, 4) if dist <= 1.0 else round(1.0 / (1.0 + dist), 4)
                meta = metas[idx]
                formatted.append({
                    "chunk_id": ids[idx],
                    "document_id": meta.get("document_id", ""),
                    "document_title": meta.get("document_title", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "section_name": meta.get("section_name", ""),
                    "snippet": docs[idx][:400] + "..." if len(docs[idx]) > 400 else docs[idx],
                    "content": docs[idx],
                    "similarity_score": score
                })

        return formatted

    def delete_document_chunks(self, document_id: str):
        """Removes all indexed chunks associated with a document."""
        try:
            self.collection.delete(where={"document_id": document_id})
            logger.info(f"Removed chunks from ChromaDB for doc: {document_id}")
        except Exception as e:
            logger.warning(f"Chroma delete warning: {e}")

vector_service = VectorService()

