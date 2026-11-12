from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time
import logging

from backend.app.services.ollama_service import ollama_service, OllamaServiceError
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ollama", tags=["Ollama Integration"])

class OllamaTestRequest(BaseModel):
    prompt: Optional[str] = Field(
        default="State in one short sentence what scientific research is.",
        description="Prompt to test qwen3:1.7b generation"
    )
    test_embedding: Optional[bool] = Field(
        default=True,
        description="Whether to also test nomic-embed-text embedding generation"
    )

class OllamaTestResponse(BaseModel):
    status: str
    llm_test: Dict[str, Any]
    embedding_test: Optional[Dict[str, Any]] = None
    total_latency_ms: float

@router.get("/status")
async def get_ollama_status():
    """Requirement: GET /api/ollama/status - Real connection check and installed model verification."""
    status_info = await ollama_service.get_connection_status()
    if not status_info.get("connected", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=status_info
        )
    return status_info

@router.get("/models")
async def get_ollama_models():
    """Requirement: GET /api/ollama/models - Lists detailed metadata for installed Ollama models."""
    try:
        models = await ollama_service.get_installed_models()
        return {
            "count": len(models),
            "models": models
        }
    except OllamaServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/test", response_model=OllamaTestResponse)
async def test_ollama_pipeline(req: OllamaTestRequest):
    """
    Requirement: POST /api/ollama/test - Tests live text generation and embedding with installed models.
    Does NOT return mock data; verifies live execution.
    """
    start_total = time.time()
    try:
        # 1. Test Text Generation with qwen3:1.7b
        llm_start = time.time()
        gen_result = await ollama_service.generate_text(
            prompt=req.prompt or "State in one short sentence what scientific research is.",
            override_max_tokens=100
        )
        llm_latency_ms = round((time.time() - llm_start) * 1000, 2)

        llm_summary = {
            "model": gen_result.get("model", settings.OLLAMA_LLM_MODEL),
            "prompt": req.prompt,
            "response": gen_result.get("response", "").strip(),
            "latency_ms": llm_latency_ms,
            "eval_count": gen_result.get("eval_count", 0)
        }

        # 2. Test Embedding Generation with nomic-embed-text
        embed_summary = None
        if req.test_embedding:
            embed_start = time.time()
            embeddings = await ollama_service.get_embeddings(["Literature Intelligence semantic test."])
            embed_latency_ms = round((time.time() - embed_start) * 1000, 2)
            first_vector = embeddings[0] if embeddings else []
            embed_summary = {
                "model": settings.OLLAMA_EMBED_MODEL,
                "dimension": len(first_vector),
                "sample_vector_preview": first_vector[:5] if first_vector else [],
                "latency_ms": embed_latency_ms
            }

        total_latency = round((time.time() - start_total) * 1000, 2)

        return OllamaTestResponse(
            status="success",
            llm_test=llm_summary,
            embedding_test=embed_summary,
            total_latency_ms=total_latency
        )

    except OllamaServiceError as e:
        logger.error(f"Ollama test failed: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in Ollama test: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test failed with unexpected error: {str(e)}"
        )

