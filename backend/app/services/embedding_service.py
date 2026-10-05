import hashlib
import math
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger

_model_instance = None


class EmbeddingService:
    """
    Embedding service utilizing local SentenceTransformers model.
    Falls back gracefully if hardware acceleration is unavailable.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.dimension = 384  # default for all-MiniLM-L6-v2
        self._model = self._load_model()

    def _load_model(self):
        global _model_instance
        if _model_instance is not None:
            return _model_instance

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer embedding model '{self.model_name}' on {settings.EMBEDDING_DEVICE}...")
            _model_instance = SentenceTransformer(self.model_name, device=settings.EMBEDDING_DEVICE)
            return _model_instance
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer ('{e}'). Using high-entropy deterministic fallback.")
            return None

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates dense vector embeddings for a list of text passages."""
        if not texts:
            return []

        if self._model is not None:
            try:
                embeddings = self._model.encode(
                    texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                return embeddings.tolist()
            except Exception as e:
                logger.error(f"Error generating embeddings with SentenceTransformer: {e}")

        # Deterministic semantic hash fallback
        return [self._fallback_embed(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        """Embeds a single search query."""
        results = self.embed_texts([query])
        return results[0] if results else [0.0] * self.dimension

    def _fallback_embed(self, text: str) -> List[float]:
        """
        Deterministic pseudo-embedding based on n-gram and token hashing.
        Normalized to unit length for valid cosine distance calculations in ChromaDB.
        """
        vec = [0.0] * self.dimension
        words = text.lower().split()
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            val = (h % 1000) / 1000.0 - 0.5
            vec[idx] += val

        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        else:
            vec[0] = 1.0
        return vec
