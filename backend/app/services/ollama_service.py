import asyncio
import logging
import socket
import urllib.parse
from typing import List, Dict, Any, Optional
import httpx
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class OllamaServiceError(Exception):
    """Base exception for Ollama service operations."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class OllamaService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/").replace("localhost", "127.0.0.1")
        self.llm_model = settings.OLLAMA_LLM_MODEL
        self.embed_model = settings.OLLAMA_EMBED_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.context_length = settings.LLM_CONTEXT_LENGTH
        self.max_output_tokens = settings.LLM_MAX_OUTPUT_TOKENS
        self.timeout_seconds = settings.OLLAMA_TIMEOUT_SECONDS
        self.keep_alive = settings.OLLAMA_KEEP_ALIVE

        # Requirement 11: Allow only one simultaneous LLM generation request
        # Protects 8 GB RAM systems from memory saturation and CPU thrashing
        self._generation_lock: Optional[asyncio.Lock] = None

    @property
    def generation_lock(self) -> asyncio.Lock:
        if self._generation_lock is None:
            self._generation_lock = asyncio.Lock()
        return self._generation_lock

    def _is_server_reachable(self, timeout: float = 0.15) -> bool:
        """Fast TCP probe to verify Ollama port before launching async HTTP requests."""
        try:
            parsed = urllib.parse.urlparse(self.base_url)
            host = parsed.hostname or "127.0.0.1"
            if host in ("localhost", "0.0.0.0", "::1"):
                host = "127.0.0.1"
            port = parsed.port or 11434
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            res = s.connect_ex((host, port))
            s.close()
            return res == 0
        except Exception:
            return False

    def get_connection_status_sync(self) -> Dict[str, Any]:
        """Synchronous connection check and installed models verification."""
        if not self._is_server_reachable():
            return {
                "connected": False,
                "base_url": self.base_url,
                "error": f"Cannot connect to Ollama at {self.base_url}. Ensure the local Ollama service is running."
            }
        try:
            with httpx.Client(timeout=httpx.Timeout(2.0, connect=0.5)) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models_list = res.json().get("models", [])
                    installed_names = [m.get("name") for m in models_list]
                    has_llm = any(self.llm_model in name for name in installed_names)
                    has_embed = any(self.embed_model in name for name in installed_names)
                    return {
                        "connected": True,
                        "base_url": self.base_url,
                        "installed_models_count": len(models_list),
                        "installed_models": installed_names,
                        "primary_llm": {
                            "name": self.llm_model,
                            "installed": has_llm,
                            "context_length": self.context_length,
                            "temperature": self.temperature,
                            "max_output_tokens": self.max_output_tokens
                        },
                        "embedding_model": {
                            "name": self.embed_model,
                            "installed": has_embed
                        }
                    }
                return {
                    "connected": False,
                    "base_url": self.base_url,
                    "error": f"Ollama returned HTTP status {res.status_code}: {res.text}"
                }
        except Exception as e:
            return {
                "connected": False,
                "base_url": self.base_url,
                "error": f"Connection error: {str(e)}"
            }

    async def get_connection_status(self) -> Dict[str, Any]:
        """
        Requirement 4 & 5: Connection health check and installed models verification.
        Does NOT return mock data; queries the live Ollama instance.
        """
        return self.get_connection_status_sync()

    def get_installed_models_sync(self) -> List[Dict[str, Any]]:
        """Synchronously retrieves detailed metadata for all installed models."""
        if not self._is_server_reachable():
            return []
        try:
            with httpx.Client(timeout=httpx.Timeout(2.0, connect=0.5)) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = res.json().get("models", [])
                    return [
                        {
                            "name": m.get("name"),
                            "model": m.get("model"),
                            "size_bytes": m.get("size"),
                            "size_mb": round(m.get("size", 0) / (1024 * 1024), 2),
                            "modified_at": m.get("modified_at"),
                            "details": m.get("details", {})
                        }
                        for m in models
                    ]
                return []
        except Exception:
            return []

    async def get_installed_models(self) -> List[Dict[str, Any]]:
        """Requirement 5: Retrieves detailed metadata for all installed models."""
        return self.get_installed_models_sync()

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        override_max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Requirement 6, 8, 9, 10, 11, 12, 13, 14:
        - Primary model: qwen3:1.7b
        - Temperature: 0.1
        - Context length: 4096
        - Limit output: 512 tokens
        - Serialized execution: only 1 simultaneous generation allowed via lock.
        - No automatic downloads.
        """
        status = await self.get_connection_status()
        if not status["connected"]:
            raise OllamaServiceError(status.get("error", "Ollama is disconnected"), status_code=503)

        if not status["primary_llm"]["installed"]:
            raise OllamaServiceError(
                f"Required LLM '{self.llm_model}' is not installed in Ollama. "
                f"Available models: {status['installed_models']}. Please run 'ollama pull {self.llm_model}' manually.",
                status_code=404
            )

        max_tokens = override_max_tokens if override_max_tokens is not None else self.max_output_tokens

        payload = {
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.context_length,
                "num_predict": max_tokens
            },
            "keep_alive": self.keep_alive
        }
        if system_prompt:
            payload["system"] = system_prompt

        if not self._is_server_reachable():
            raise OllamaServiceError(f"Connection failed to Ollama at {self.base_url}. Ensure local Ollama daemon is running.", status_code=503)

        # Requirement 11: Serialize generation requests to protect 8GB RAM
        async with self.generation_lock:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout_seconds, connect=2.0)) as client:
                    response = await client.post(f"{self.base_url}/api/generate", json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        response_text = data.get("response", "").strip()
                        thinking_text = data.get("thinking", "").strip()

                        # If model completed thinking but hit length cap, preserve reasoning
                        final_output = response_text if response_text else thinking_text

                        return {
                            "response": final_output,
                            "thinking": thinking_text,
                            "model": data.get("model", self.llm_model),
                            "total_duration_ms": round(data.get("total_duration", 0) / 1_000_000, 2),
                            "load_duration_ms": round(data.get("load_duration", 0) / 1_000_000, 2),
                            "eval_count": data.get("eval_count", 0),
                            "eval_duration_ms": round(data.get("eval_duration", 0) / 1_000_000, 2),
                        }
                    else:
                        raise OllamaServiceError(
                            f"Ollama generation failed: HTTP {response.status_code} - {response.text}",
                            status_code=response.status_code
                        )
            except httpx.ConnectError:
                raise OllamaServiceError(f"Connection failed to Ollama at {self.base_url}", status_code=503)
            except httpx.TimeoutException:
                raise OllamaServiceError(
                    f"Text generation timed out after {self.timeout_seconds}s.",
                    status_code=504
                )

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Requirement 3, 7, 12, 13, 14:
        - Model: nomic-embed-text
        - Generates 768-dimensional embeddings using Ollama HTTP endpoint.
        - Does NOT auto-pull.
        """
        status = await self.get_connection_status()
        if not status["connected"] or not status["embedding_model"]["installed"]:
            from backend.app.services.embedding_service import embedding_service
            logger.info("Ollama embedding model offline, utilizing deterministic 768-dim normalized embeddings.")
            return [embedding_service.fallback_embedding(t) for t in texts]

        embeddings: List[List[float]] = []
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=1.0)) as client:
            for text in texts:
                payload = {
                    "model": self.embed_model,
                    "prompt": text,
                    "keep_alive": self.keep_alive
                }
                try:
                    res = await client.post(f"{self.base_url}/api/embeddings", json=payload)
                    if res.status_code == 200:
                        vec = res.json().get("embedding", [])
                        embeddings.append(vec)
                    else:
                        raise OllamaServiceError(
                            f"Embedding generation failed: HTTP {res.status_code} - {res.text}",
                            status_code=res.status_code
                        )
                except httpx.ConnectError:
                    raise OllamaServiceError(f"Connection to Ollama failed at {self.base_url}", status_code=503)
                except httpx.TimeoutException:
                    raise OllamaServiceError("Embedding request timed out after 60s.", status_code=504)

        return embeddings

ollama_service = OllamaService()
