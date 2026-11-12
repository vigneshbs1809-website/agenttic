import re
import math
import logging
from typing import List, Dict, Any, Optional
from collections import Counter

from backend.app.services.embedding_service import embedding_service
from backend.app.services.chroma_service import chroma_service

logger = logging.getLogger(__name__)

def tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer for keyword search."""
    return [w.lower() for w in re.findall(r"\b[A-Za-z0-9_]{2,}\b", text)]

class RetrievalAgent:
    def __init__(self, default_top_k: int = 4):
        self.default_top_k = default_top_k

    def calculate_bm25_scores(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculates BM25 keyword matching scores over a candidate set of chunks.
        """
        query_tokens = tokenize(query)
        if not query_tokens or not chunks:
            return []

        doc_tokens = [tokenize(c["original_text"]) for c in chunks]
        N = len(chunks)
        avg_dl = sum(len(dt) for dt in doc_tokens) / max(N, 1)

        # Calculate IDF for each query term
        idf = {}
        for qt in query_tokens:
            df = sum(1 for dt in doc_tokens if qt in dt)
            # Standard smoothed BM25 IDF formula
            idf[qt] = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

        k1 = 1.5
        b = 0.75

        scored_chunks = []
        for i, c in enumerate(chunks):
            dt = doc_tokens[i]
            dl = len(dt)
            freqs = Counter(dt)
            score = 0.0

            for qt in query_tokens:
                f = freqs.get(qt, 0)
                if f > 0:
                    numerator = f * (k1 + 1)
                    denominator = f + k1 * (1 - b + b * (dl / avg_dl))
                    score += idf.get(qt, 0.0) * (numerator / max(denominator, 1e-6))

            scored_chunks.append({
                **c,
                "keyword_raw_score": score
            })

        # Normalize keyword scores to [0.0, 1.0]
        max_score = max((sc["keyword_raw_score"] for sc in scored_chunks), default=1.0)
        for sc in scored_chunks:
            sc["keyword_score"] = round(sc["keyword_raw_score"] / max_score, 4) if max_score > 0 else 0.0

        scored_chunks.sort(key=lambda x: x["keyword_score"], reverse=True)
        return scored_chunks

    async def search_semantic(
        self,
        query: str,
        top_k: int = 4,
        project_id: Optional[str] = None,
        paper_id: Optional[str] = None,
        paper_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Requirement 5: Semantic similarity search."""
        query_embedding = await embedding_service.embed_query(query)
        if not query_embedding:
            return []

        return chroma_service.query_semantic(
            query_embedding=query_embedding,
            top_k=top_k,
            project_id=project_id,
            paper_id=paper_id,
            paper_ids=paper_ids
        )

    def search_keyword(
        self,
        query: str,
        top_k: int = 4,
        project_id: Optional[str] = None,
        paper_id: Optional[str] = None,
        paper_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Requirement 6: Keyword search using BM25 scoring."""
        chunks = chroma_service.get_all_chunks_for_filtering(
            project_id=project_id,
            paper_id=paper_id,
            paper_ids=paper_ids
        )
        scored = self.calculate_bm25_scores(query, chunks)
        top_matches = scored[:top_k]

        return [
            {
                "chunk_id": m["chunk_id"],
                "paper_id": m["paper_id"],
                "paper_title": m["paper_title"],
                "page_number": m["page_number"],
                "section_name": m["section_name"],
                "original_text": m["original_text"],
                "retrieval_score": m["keyword_score"],
                "retrieval_method": "keyword"
            }
            for m in top_matches
        ]

    async def search_hybrid(
        self,
        query: str,
        top_k: int = 4,
        project_id: Optional[str] = None,
        paper_id: Optional[str] = None,
        paper_ids: Optional[List[str]] = None,
        dense_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Requirement 7, 8, 9:
        Hybrid retrieval combining semantic similarity and BM25 keyword matching with Reciprocal Rank Fusion / Weighted Score.
        """
        # Fetch candidate pools from both methods
        semantic_results = await self.search_semantic(
            query=query,
            top_k=top_k * 2,
            project_id=project_id,
            paper_id=paper_id,
            paper_ids=paper_ids
        )

        keyword_results = self.search_keyword(
            query=query,
            top_k=top_k * 2,
            project_id=project_id,
            paper_id=paper_id,
            paper_ids=paper_ids
        )

        # Merge results by chunk_id
        merged: Dict[str, Dict[str, Any]] = {}

        # 1. Populate semantic candidates
        for r in semantic_results:
            cid = r["chunk_id"]
            merged[cid] = {
                "chunk_id": cid,
                "paper_id": r["paper_id"],
                "paper_title": r["paper_title"],
                "page_number": r["page_number"],
                "section_name": r["section_name"],
                "original_text": r["original_text"],
                "semantic_score": r["retrieval_score"],
                "keyword_score": 0.0,
            }

        # 2. Populate keyword candidates
        for r in keyword_results:
            cid = r["chunk_id"]
            if cid in merged:
                merged[cid]["keyword_score"] = r["retrieval_score"]
            else:
                merged[cid] = {
                    "chunk_id": cid,
                    "paper_id": r["paper_id"],
                    "paper_title": r["paper_title"],
                    "page_number": r["page_number"],
                    "section_name": r["section_name"],
                    "original_text": r["original_text"],
                    "semantic_score": 0.0,
                    "keyword_score": r["retrieval_score"],
                }

        # 3. Compute weighted hybrid score
        combined_list = []
        for cid, item in merged.items():
            sem = item["semantic_score"]
            kw = item["keyword_score"]
            # Weighted interpolation
            hybrid_score = round((dense_weight * sem) + ((1.0 - dense_weight) * kw), 4)

            combined_list.append({
                "chunk_id": item["chunk_id"],
                "paper_id": item["paper_id"],
                "paper_title": item["paper_title"],
                "page_number": item["page_number"],
                "section_name": item["section_name"],
                "original_text": item["original_text"],
                "retrieval_score": hybrid_score,
                "semantic_score": sem,
                "keyword_score": kw,
                "retrieval_method": "hybrid"
            })

        # Sort descending by hybrid score
        combined_list.sort(key=lambda x: x["retrieval_score"], reverse=True)
        return combined_list[:top_k]

retrieval_agent = RetrievalAgent(default_top_k=4)

