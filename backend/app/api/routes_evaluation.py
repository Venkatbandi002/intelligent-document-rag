from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from backend.app.database.models import get_db_connection
from backend.app.schemas.evaluation import BenchmarkComparison, EvaluationRunReport
from backend.app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Benchmarks"])
eval_service = EvaluationService()


class RunEvalRequest(BaseModel):
    name: Optional[str] = "Manual RAG Evaluation"
    top_k: Optional[int] = 5
    enable_reranking: Optional[bool] = True


@router.post("/run", response_model=EvaluationRunReport)
async def run_evaluation(payload: Optional[RunEvalRequest] = None):
    req = payload or RunEvalRequest()
    try:
        report = eval_service.run_evaluation(
            name=req.name or "Manual RAG Evaluation",
            top_k=req.top_k or 5,
            enable_reranking=req.enable_reranking if req.enable_reranking is not None else True,
        )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )


@router.post("/benchmark", response_model=BenchmarkComparison)
async def run_benchmark():
    """
    Executes comparative experiment:
    1. Baseline (Top-K=3, No Rerank)
    2. Improved Chunking (Top-K=5, No Rerank)
    3. Chunking + Reranking (Top-K=5, BM25 Hybrid Rerank)
    """
    try:
        comparison = eval_service.run_benchmark_matrix()
        return comparison
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution failed: {str(e)}"
        )


@router.get("/results")
async def get_results(limit: int = Query(10, ge=1, le=50)):
    return eval_service.get_run_history(limit=limit)


@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """
    Returns high-level statistics for the RAG dashboard:
    - Number of documents
    - Number of chunks
    - Total queries logged
    - Average response latency
    - Latest evaluation metrics (Hit Rate, Precision, MRR)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as doc_count FROM documents")
    doc_count = cursor.fetchone()["doc_count"]

    cursor.execute("SELECT COUNT(*) as chunk_count FROM document_chunks")
    chunk_count = cursor.fetchone()["chunk_count"]

    cursor.execute("SELECT COUNT(*) as query_count, AVG(latency_ms) as avg_latency FROM chat_messages WHERE role = 'assistant'")
    chat_stat = cursor.fetchone()
    query_count = chat_stat["query_count"] or 0
    avg_latency = round(chat_stat["avg_latency"] or 0.0, 2)

    cursor.execute("SELECT * FROM evaluation_runs ORDER BY created_at DESC LIMIT 1")
    latest_run = cursor.fetchone()

    latest_eval = None
    if latest_run:
        latest_eval = {
            "hit_rate": latest_run["hit_rate"],
            "precision_at_k": latest_run["precision_at_k"],
            "recall_at_k": latest_run["recall_at_k"],
            "mrr": latest_run["mrr"],
            "avg_latency_ms": latest_run["avg_latency_ms"],
        }

    conn.close()

    return {
        "total_documents": doc_count,
        "total_chunks": chunk_count,
        "total_queries": query_count,
        "average_query_latency_ms": avg_latency,
        "latest_evaluation": latest_eval,
    }
