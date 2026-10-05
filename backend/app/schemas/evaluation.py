from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvaluationQuery(BaseModel):
    id: Optional[str] = None
    question: str
    expected_answer: Optional[str] = None
    expected_sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of expected sources e.g. [{'document_name': 'Leave Policy.pdf', 'page_number': 4}]"
    )


class QueryEvalResult(BaseModel):
    question: str
    generated_answer: str
    expected_answer: Optional[str] = None
    retrieved_sources: List[Dict[str, Any]]
    expected_sources: List[Dict[str, Any]]
    hit: bool
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    faithfulness_score: float
    latency_ms: float


class EvaluationRunReport(BaseModel):
    id: str
    name: str
    config: Dict[str, Any]
    total_queries: int
    hit_rate: float
    precision_at_k: float
    recall_at_k: float
    mrr: float
    avg_latency_ms: float
    created_at: str
    query_results: List[QueryEvalResult] = Field(default_factory=list)


class BenchmarkComparison(BaseModel):
    runs: List[EvaluationRunReport]
