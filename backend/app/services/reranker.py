import math
import re
from typing import Any, Dict, List
from backend.app.core.logging import logger

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False


class RerankerService:
    """
    Reranks retrieved candidate chunks to prioritize high-precision context passages.
    Combines dense semantic similarity with exact keyword lexical relevance (Hybrid RRF / BM25 scoring).
    """

    def __init__(self, top_n: int = 3):
        self.top_n = top_n

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def rerank(
        self,
        query: str,
        passages: List[Dict[str, Any]],
        top_n: int = None
    ) -> List[Dict[str, Any]]:
        """
        Reranks a list of candidate passages for the query.
        Returns top_n items sorted with 'rerank_score'.
        """
        target_n = top_n or self.top_n
        if not passages:
            return []

        if len(passages) <= 1:
            passages[0]["rerank_score"] = passages[0].get("similarity_score", 1.0)
            return passages[:target_n]

        query_tokens = self.tokenize(query)
        corpus = [self.tokenize(p["content"]) for p in passages]

        # Calculate BM25 scores if available
        bm25_scores = [0.0] * len(passages)
        if BM25_AVAILABLE and any(corpus):
            try:
                bm25 = BM25Okapi(corpus)
                raw_bm25 = bm25.get_scores(query_tokens)
                max_bm25 = max(raw_bm25) if len(raw_bm25) > 0 and max(raw_bm25) > 0 else 1.0
                bm25_scores = [s / max_bm25 for s in raw_bm25]
            except Exception as e:
                logger.warning(f"BM25 rerank computation fallback: {e}")

        # Compute hybrid combined score (Dense semantic score * 0.6 + Lexical BM25 score * 0.4)
        for idx, p in enumerate(passages):
            semantic_score = p.get("similarity_score", 0.5)
            lexical_score = bm25_scores[idx]
            
            # Bonus if direct query terms appear consecutively in chunk
            exact_phrase_bonus = 0.15 if query.lower() in p["content"].lower() else 0.0
            
            combined_score = (0.55 * semantic_score) + (0.35 * lexical_score) + exact_phrase_bonus
            p["rerank_score"] = round(min(1.0, float(combined_score)), 4)

        # Sort descending by rerank_score
        reranked = sorted(passages, key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:target_n]
