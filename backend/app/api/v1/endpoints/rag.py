import time
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.app.models.schemas import RAGQueryRequest, RAGQueryResponse, Citation
from backend.app.services.vector_service import vector_service
from backend.app.services.ollama_service import ollama_service
from backend.app.core.config import settings
from backend.app.core.database import get_db

router = APIRouter()

SYSTEM_PROMPT = """You are an expert scientific literature intelligence assistant. 
Your role is to answer questions strictly based on the provided research context chunks.
Rules:
1. Ground your answers directly in the context.
2. Clearly cite papers and findings using [Paper Title, Section].
3. If the context does not contain enough information, state that clearly rather than hallucinating.
4. Keep answers concise, objective, and analytically structured.
"""

def build_context_prompt(query: str, retrieved_chunks: list) -> str:
    context_blocks = []
    for idx, c in enumerate(retrieved_chunks):
        doc_title = c.get("document_title", "Unknown Source")
        section = c.get("section_name", "General")
        snippet = c.get("content", "")
        context_blocks.append(f"--- [Source {idx+1}]: {doc_title} (Section: {section}) ---\n{snippet}\n")

    context_str = "\n".join(context_blocks)
    return f"""Context from Literature Library:
{context_str}

User Question: {query}

Synthesized Scientific Answer:"""

@router.post("/rag/query", response_model=RAGQueryResponse)
async def query_literature(req: RAGQueryRequest):
    start_time = time.time()
    
    # 1. Retrieve most relevant context from ChromaDB
    retrieved = await vector_service.query_similar(
        query_text=req.query,
        top_k=req.top_k or settings.TOP_K_RETRIEVAL,
        document_filter=req.document_filter
    )

    if not retrieved:
        return {
            "query": req.query,
            "answer": "No indexed literature matches were found in your library for this query. Please upload research papers first.",
            "citations": [],
            "duration_ms": int((time.time() - start_time) * 1000),
            "model_used": settings.OLLAMA_LLM_MODEL
        }

    # 2. Build synthesis prompt
    prompt = build_context_prompt(req.query, retrieved)

    # 3. Generate answer using Ollama
    answer = await ollama_service.generate_response(prompt=prompt, system_prompt=SYSTEM_PROMPT)
    duration_ms = int((time.time() - start_time) * 1000)

    # 4. Format citations
    citations = [
        Citation(
            document_id=c["document_id"],
            document_title=c["document_title"],
            chunk_index=c["chunk_index"],
            snippet=c["snippet"],
            similarity_score=c["similarity_score"]
        )
        for c in retrieved
    ]

    # 5. Log query to SQLite
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO query_history (id, query_text, response_text, referenced_chunks, duration_ms)
            VALUES (?, ?, ?, ?, ?)
            """, (
                str(time.time()),
                req.query,
                answer,
                json.dumps([c["chunk_id"] for c in retrieved]),
                duration_ms
            ))
    except Exception:
        pass

    return {
        "query": req.query,
        "answer": answer,
        "citations": citations,
        "duration_ms": duration_ms,
        "model_used": settings.OLLAMA_LLM_MODEL
    }

@router.post("/rag/query/stream")
async def stream_query_literature(req: RAGQueryRequest):
    retrieved = await vector_service.query_similar(
        query_text=req.query,
        top_k=req.top_k or settings.TOP_K_RETRIEVAL,
        document_filter=req.document_filter
    )

    prompt = build_context_prompt(req.query, retrieved)

    async def event_generator():
        # First send citation metadata
        citations_data = [
            {
                "document_id": c["document_id"],
                "document_title": c["document_title"],
                "chunk_index": c["chunk_index"],
                "snippet": c["snippet"],
                "similarity_score": c["similarity_score"]
            }
            for c in retrieved
        ]
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations_data})}\n\n"

        # Stream LLM tokens
        async for token in ollama_service.stream_response(prompt=prompt, system_prompt=SYSTEM_PROMPT):
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

