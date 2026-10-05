from typing import List, Optional
from pydantic import BaseModel, Field


class RetrievedPassage(BaseModel):
    chunk_id: str
    document_name: str
    page_number: int
    content: str
    similarity_score: float
    rerank_score: Optional[float] = None


class SourceCitation(BaseModel):
    document_name: str
    page_number: int
    snippet: str
    score: float


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, description="The user query to be answered from documents")
    conversation_id: Optional[str] = Field("default", description="Conversation session ID")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of context chunks to retrieve")
    enable_reranking: Optional[bool] = Field(None, description="Whether to apply secondary reranker")
    document_filter: Optional[str] = Field(None, description="Optional document name filter")


class ChatResponse(BaseModel):
    conversation_id: str
    question: str
    answer: str
    sources: List[SourceCitation] = Field(default_factory=list)
    retrieved_passages: List[RetrievedPassage] = Field(default_factory=list)
    is_grounded: bool = True
    latency_ms: float
    model_used: str


class ChatHistoryItem(BaseModel):
    id: str
    role: str
    content: str
    sources: List[SourceCitation] = Field(default_factory=list)
    retrieved_passages: List[RetrievedPassage] = Field(default_factory=list)
    created_at: str
    latency_ms: float


class ChatHistoryResponse(BaseModel):
    conversation_id: str
    messages: List[ChatHistoryItem]
