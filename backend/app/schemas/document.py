from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_id: str
    document_name: str
    page_number: int
    chunk_index: int
    content: str
    metadata: dict = Field(default_factory=dict)


class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_hash: str
    file_size_bytes: int
    page_count: int
    chunk_count: int
    uploaded_at: str
    status: str


class DocumentUploadResponse(BaseModel):
    message: str
    document: DocumentInfo
    chunks_created: int
    is_duplicate: bool = False


class DocumentListResponse(BaseModel):
    total_documents: int
    total_chunks: int
    documents: List[DocumentInfo]
