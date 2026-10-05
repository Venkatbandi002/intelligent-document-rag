import json
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.models import get_db_connection
from backend.app.schemas.chat import ChatResponse, RetrievedPassage, SourceCitation
from backend.app.services.llm_service import LLMService
from backend.app.services.reranker import RerankerService
from backend.app.services.vector_store import VectorStoreService


class RAGService:
    """
    End-to-End RAG Pipeline Orchestrator:
    Query -> Vector Retrieval -> Optional Reranking -> Strict Grounding Prompt ->
    LLM Synthesis -> Citation Extraction -> SQLite Audit Log
    """

    def __init__(
        self,
        vector_store: Optional[VectorStoreService] = None,
        reranker: Optional[RerankerService] = None,
        llm_service: Optional[LLMService] = None,
    ):
        self.vector_store = vector_store or VectorStoreService()
        self.reranker = reranker or RerankerService(top_n=settings.RERANKER_TOP_N)
        self.llm_service = llm_service or LLMService()

    def query(
        self,
        question: str,
        conversation_id: str = "default",
        top_k: Optional[int] = None,
        enable_reranking: Optional[bool] = None,
        document_filter: Optional[str] = None,
    ) -> ChatResponse:
        t_start = time.time()
        k = top_k or settings.DEFAULT_TOP_K
        use_rerank = settings.ENABLE_RERANKING if enable_reranking is None else enable_reranking

        filter_dict = {"document_name": document_filter} if document_filter else None

        # 1. Retrieve candidates from ChromaDB
        t_retrieval_start = time.time()
        fetch_k = k * 2 if use_rerank else k
        raw_candidates = self.vector_store.similarity_search(
            query=question,
            top_k=fetch_k,
            filter_dict=filter_dict,
        )
        retrieval_ms = round((time.time() - t_retrieval_start) * 1000, 2)

        # 2. Apply reranking if enabled
        t_rerank_start = time.time()
        if use_rerank and raw_candidates:
            active_passages = self.reranker.rerank(
                query=question,
                passages=raw_candidates,
                top_n=k,
            )
        else:
            active_passages = raw_candidates[:k]
        rerank_ms = round((time.time() - t_rerank_start) * 1000, 2)

        # 3. Grounding check & empty context handling
        is_grounded = True
        synthesis_ms = 0.0
        if not active_passages:
            answer = settings.NO_ANSWER_FALLBACK
            is_grounded = False
            sources = []
        else:
            # Check maximum similarity / relevance score
            best_score = max(
                p.get("rerank_score", p.get("similarity_score", 0.0))
                for p in active_passages
            )
            if best_score < settings.SIMILARITY_THRESHOLD:
                # Irrelevant query, reject to avoid hallucinations
                answer = settings.NO_ANSWER_FALLBACK
                is_grounded = False
                sources = []
            else:
                # 4. Generate grounded LLM response
                t_synth_start = time.time()
                answer = self.llm_service.generate_grounded_answer(
                    query=question,
                    context_passages=active_passages,
                )
                synthesis_ms = round((time.time() - t_synth_start) * 1000, 2)

                if settings.NO_ANSWER_FALLBACK.lower() in answer.lower():
                    is_grounded = False
                    sources = []
                else:
                    sources = self._extract_citations(answer, active_passages)

        total_ms = round((time.time() - t_start) * 1000, 2)
        breakdown = {
            "retrieval_ms": retrieval_ms,
            "rerank_ms": rerank_ms,
            "synthesis_ms": synthesis_ms,
            "total_ms": total_ms,
        }

        # Format retrieved passages for frontend inspection
        retrieved_dto = [
            RetrievedPassage(
                chunk_id=p["chunk_id"],
                document_name=p["document_name"],
                page_number=p["page_number"],
                content=p["content"],
                similarity_score=p.get("similarity_score", 0.0),
                rerank_score=p.get("rerank_score"),
            )
            for p in active_passages
        ]

        # 5. Persist interaction in SQLite
        self._record_chat_history(
            conversation_id=conversation_id,
            question=question,
            answer=answer,
            sources=sources,
            passages=retrieved_dto,
            latency_ms=total_ms,
        )

        return ChatResponse(
            conversation_id=conversation_id,
            question=question,
            answer=answer,
            sources=sources,
            retrieved_passages=retrieved_dto,
            is_grounded=is_grounded,
            latency_ms=total_ms,
            latency_breakdown=breakdown,
            model_used=f"GEMINI ({settings.GEMINI_MODEL})" if settings.LLM_PROVIDER == "gemini" else (
                f"OPENAI ({settings.OPENAI_MODEL})" if settings.LLM_PROVIDER == "openai" else settings.LLM_PROVIDER.upper()
            ),
        )

    def _extract_citations(
        self,
        answer: str,
        passages: List[Dict[str, Any]]
    ) -> List[SourceCitation]:
        """
        Parses source citations from both inline bracket patterns like
        [Employee Handbook.pdf, Page 12] and matches against the retrieved passages.
        """
        citations_map: Dict[str, SourceCitation] = {}

        # 1. Regex parse [Document, Page X]
        pattern = r"\[([a-zA-Z0-9_\-\. ]+?)(?:,\s*(?:Page|page|p\.)\s*(\d+))?\]"
        matches = re.findall(pattern, answer)

        for doc_name, page_str in matches:
            clean_name = doc_name.strip()
            page_num = int(page_str) if page_str else 1
            key = f"{clean_name}_{page_num}"
            
            # Find matching passage text snippet
            snippet = ""
            score = 1.0
            for p in passages:
                if clean_name.lower() in p["document_name"].lower():
                    snippet = p["content"][:200] + "..."
                    score = p.get("rerank_score", p.get("similarity_score", 1.0))
                    break

            if key not in citations_map:
                citations_map[key] = SourceCitation(
                    document_name=clean_name,
                    page_number=page_num,
                    snippet=snippet,
                    score=round(float(score), 4),
                )

        # 2. If no inline citations were generated by LLM, fallback to top retrieved passages
        if not citations_map and passages:
            for p in passages[:2]:
                key = f"{p['document_name']}_{p['page_number']}"
                if key not in citations_map:
                    citations_map[key] = SourceCitation(
                        document_name=p["document_name"],
                        page_number=p["page_number"],
                        snippet=p["content"][:200] + "...",
                        score=round(float(p.get("rerank_score", p.get("similarity_score", 1.0))), 4),
                    )

        return list(citations_map.values())

    def _record_chat_history(
        self,
        conversation_id: str,
        question: str,
        answer: str,
        sources: List[SourceCitation],
        passages: List[RetrievedPassage],
        latency_ms: float,
    ) -> None:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()

            # Save user message
            cursor.execute(
                """
                INSERT INTO chat_messages (id, conversation_id, role, content, sources_json, retrieved_context_json, latency_ms, created_at)
                VALUES (?, ?, 'user', ?, '[]', '[]', 0.0, ?)
                """,
                (str(uuid.uuid4()), conversation_id, question, now),
            )

            # Save assistant message
            sources_json = json.dumps([s.model_dump() for s in sources])
            passages_json = json.dumps([p.model_dump() for p in passages])
            cursor.execute(
                """
                INSERT INTO chat_messages (id, conversation_id, role, content, sources_json, retrieved_context_json, latency_ms, created_at)
                VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), conversation_id, answer, sources_json, passages_json, latency_ms, now),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error persisting chat history to SQLite: {e}")
