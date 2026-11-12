import asyncio
import logging
from typing import List, Optional
import httpx
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/").replace("localhost", "127.0.0.1")
        self.embed_model = settings.OLLAMA_EMBED_MODEL
        self.batch_size = 8  # Small batches for 8 GB RAM protection
        self.timeout = httpx.Timeout(1.0, connect=0.5)
        self.keep_alive = "5m"
        self._lock: Optional[asyncio.Lock] = None

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _is_server_reachable(self, timeout: float = 0.15) -> bool:
        """Fast TCP probe to verify Ollama port before launching async HTTP requests."""
        import socket, urllib.parse
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

    @staticmethod
    def fallback_embedding(text: str, dim: int = 768) -> List[float]:
        """Deterministic 768-dim normalized embedding when local Ollama is offline."""
        import hashlib
        import numpy as np
        vec = np.zeros(dim, dtype=np.float32)
        words = text.lower().split()
        if not words:
            vec[0] = 1.0
            return vec.tolist()
        for w in words:
            h = int(hashlib.md5(w.encode('utf-8')).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if (h >> 16) & 1 else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        else:
            vec[0] = 1.0
        return vec.tolist()

    async def generate_single_embedding(self, client: httpx.AsyncClient, text: str) -> List[float]:
        """Generates a 768-dimensional embedding for a single text via Ollama with fallback."""
        payload = {
            "model": self.embed_model,
            "prompt": text,
            "keep_alive": self.keep_alive
        }
        try:
            res = await client.post(f"{self.base_url}/api/embeddings", json=payload)
            if res.status_code == 200:
                vec = res.json().get("embedding", [])
                if vec and len(vec) == 768:
                    return vec
            logger.debug(f"Ollama embedding unavailable (status {res.status_code if 'res' in locals() else 'unknown'}), using deterministic fallback")
            return self.fallback_embedding(text)
        except Exception as e:
            logger.debug(f"Ollama embedding unavailable ({e}), using deterministic fallback")
            return self.fallback_embedding(text)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of texts in small batches (one batch at a time) to prevent memory saturation.
        """
        if not texts:
            return []

        if not self._is_server_reachable():
            return [self.fallback_embedding(t) for t in texts]

        all_embeddings: List[List[float]] = []

        # Enforce one batch at a time across concurrent threads/tasks
        async with self.lock:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    for i in range(0, len(texts), self.batch_size):
                        batch = texts[i : i + self.batch_size]
                        batch_embeddings = []
                        for item in batch:
                            vec = await self.generate_single_embedding(client, item)
                            batch_embeddings.append(vec)
                        all_embeddings.extend(batch_embeddings)
                        # Yield CPU slice between batches
                        await asyncio.sleep(0.01)
            except Exception as e:
                logger.warning(f"Embedding batch error: {e}")

        return all_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Convenience method to embed a single research query."""
        res = await self.embed_texts([query])
        return res[0] if res else []

embedding_service = EmbeddingService()
