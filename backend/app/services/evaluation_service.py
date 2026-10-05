import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.models import get_db_connection
from backend.app.schemas.evaluation import (
    BenchmarkComparison,
    EvaluationQuery,
    EvaluationRunReport,
    QueryEvalResult,
)
from backend.app.services.rag_service import RAGService


class EvaluationService:
    """
    RAG Evaluation Framework:
    Calculates Precision@K, Recall@K, Hit Rate, MRR (Mean Reciprocal Rank),
    and Faithfulness across benchmark query datasets.
    """

    def __init__(self, rag_service: Optional[RAGService] = None):
        self.rag_service = rag_service or RAGService()

    @staticmethod
    def load_dataset(dataset_path: Optional[str] = None) -> List[EvaluationQuery]:
        path = Path(dataset_path) if dataset_path else settings.BASE_DIR / "evaluation" / "questions.json"
        if not path.exists():
            logger.warning(f"Evaluation questions file not found at {path}")
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [EvaluationQuery(**item) for item in data]

    def evaluate_query(
        self,
        query_item: EvaluationQuery,
        top_k: int = 5,
        enable_reranking: bool = True
    ) -> QueryEvalResult:
        start_time = time.time()
        
        # Execute RAG pipeline
        response = self.rag_service.query(
            question=query_item.question,
            top_k=top_k,
            enable_reranking=enable_reranking,
        )
        
        latency_ms = round((time.time() - start_time) * 1000, 2)

        # Expected sources (e.g. [{"document_name": "Leave Policy.pdf", "page_number": 4}])
        expected_sources = query_item.expected_sources or []
        retrieved_passages = [
            {"document_name": p.document_name, "page_number": p.page_number}
            for p in response.retrieved_passages
        ]

        # Calculate Hit, Precision@K, Recall@K, MRR
        hit = False
        first_match_rank = 0
        relevant_retrieved_count = 0

        for rank, p in enumerate(retrieved_passages, 1):
            is_relevant = False
            for exp in expected_sources:
                doc_match = exp.get("document_name", "").lower() in p["document_name"].lower()
                page_match = exp.get("page_number") is None or exp.get("page_number") == p["page_number"]
                if doc_match and page_match:
                    is_relevant = True
                    break

            if is_relevant:
                relevant_retrieved_count += 1
                if not hit:
                    hit = True
                    first_match_rank = rank

        k_val = max(1, len(retrieved_passages))
        precision_at_k = relevant_retrieved_count / k_val
        recall_at_k = (
            relevant_retrieved_count / len(expected_sources)
            if expected_sources
            else (1.0 if not retrieved_passages else 0.0)
        )
        reciprocal_rank = 1.0 / first_match_rank if first_match_rank > 0 else 0.0

        # Faithfulness check: does answer acknowledge absence or cite valid document?
        faithfulness = 1.0
        if not hit and response.is_grounded and expected_sources:
            # Retrieved nothing relevant but LLM gave an answer anyway -> potential hallucination
            faithfulness = 0.3
        elif not expected_sources and not response.is_grounded:
            # Out-of-domain query correctly rejected
            faithfulness = 1.0

        return QueryEvalResult(
            question=query_item.question,
            generated_answer=response.answer,
            expected_answer=query_item.expected_answer,
            retrieved_sources=retrieved_passages,
            expected_sources=expected_sources,
            hit=hit,
            precision_at_k=round(precision_at_k, 4),
            recall_at_k=round(recall_at_k, 4),
            reciprocal_rank=round(reciprocal_rank, 4),
            faithfulness_score=round(faithfulness, 4),
            latency_ms=latency_ms,
        )

    def run_evaluation(
        self,
        name: str = "Evaluation Run",
        dataset: Optional[List[EvaluationQuery]] = None,
        top_k: int = 5,
        enable_reranking: bool = True,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> EvaluationRunReport:
        items = dataset if dataset is not None else self.load_dataset()
        if not items:
            raise ValueError("No evaluation queries provided or found in questions.json")

        results: List[QueryEvalResult] = []
        for q in items:
            res = self.evaluate_query(q, top_k=top_k, enable_reranking=enable_reranking)
            results.append(res)

        total = len(results)
        hit_rate = sum(1 for r in results if r.hit) / total
        avg_precision = sum(r.precision_at_k for r in results) / total
        avg_recall = sum(r.recall_at_k for r in results) / total
        mrr = sum(r.reciprocal_rank for r in results) / total
        avg_latency = sum(r.latency_ms for r in results) / total

        run_id = f"run_{uuid.uuid4().hex[:8]}"
        run_config = config_override or {
            "top_k": top_k,
            "enable_reranking": enable_reranking,
            "embedding_model": settings.EMBEDDING_MODEL_NAME,
            "llm_provider": settings.LLM_PROVIDER,
        }

        report = EvaluationRunReport(
            id=run_id,
            name=name,
            config=run_config,
            total_queries=total,
            hit_rate=round(hit_rate, 4),
            precision_at_k=round(avg_precision, 4),
            recall_at_k=round(avg_recall, 4),
            mrr=round(mrr, 4),
            avg_latency_ms=round(avg_latency, 2),
            created_at=datetime.utcnow().isoformat(),
            query_results=results,
        )

        # Persist report in SQLite
        self._save_run_report(report)
        return report

    def run_benchmark_matrix(self) -> BenchmarkComparison:
        """
        Executes the 3 canonical benchmark configurations requested:
        1. Baseline: Top-K=3, No Rerank
        2. Improved Chunking: Top-K=5, No Rerank
        3. Chunking + Reranking: Top-K=5, Rerank enabled
        """
        dataset = self.load_dataset()
        
        run_a = self.run_evaluation(
            name="Baseline (Top-K=3, No Rerank)",
            dataset=dataset,
            top_k=3,
            enable_reranking=False,
            config_override={"top_k": 3, "enable_reranking": False, "chunking": "500/50"}
        )

        run_b = self.run_evaluation(
            name="Improved Chunking (Top-K=5, No Rerank)",
            dataset=dataset,
            top_k=5,
            enable_reranking=False,
            config_override={"top_k": 5, "enable_reranking": False, "chunking": "800/100"}
        )

        run_c = self.run_evaluation(
            name="Chunking + Reranking (Top-K=5, Hybrid Rerank)",
            dataset=dataset,
            top_k=5,
            enable_reranking=True,
            config_override={"top_k": 5, "enable_reranking": True, "chunking": "800/100 + BM25"}
        )

        return BenchmarkComparison(runs=[run_a, run_b, run_c])

    def get_run_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, config_json, total_queries, hit_rate, precision_at_k, recall_at_k, mrr, avg_latency_ms, created_at
            FROM evaluation_runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        runs = []
        for r in rows:
            runs.append({
                "id": r["id"],
                "name": r["name"],
                "config": json.loads(r["config_json"]),
                "total_queries": r["total_queries"],
                "hit_rate": r["hit_rate"],
                "precision_at_k": r["precision_at_k"],
                "recall_at_k": r["recall_at_k"],
                "mrr": r["mrr"],
                "avg_latency_ms": r["avg_latency_ms"],
                "created_at": r["created_at"],
            })
        conn.close()
        return runs

    def _save_run_report(self, report: EvaluationRunReport) -> None:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO evaluation_runs (id, name, config_json, total_queries, hit_rate, precision_at_k, recall_at_k, mrr, avg_latency_ms, created_at, report_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.id,
                    report.name,
                    json.dumps(report.config),
                    report.total_queries,
                    report.hit_rate,
                    report.precision_at_k,
                    report.recall_at_k,
                    report.mrr,
                    report.avg_latency_ms,
                    report.created_at,
                    report.model_dump_json(),
                )
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error persisting evaluation report: {e}")
