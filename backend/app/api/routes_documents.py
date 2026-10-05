import io
import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.models import get_db_connection
from backend.app.schemas.document import (
    DocumentInfo,
    DocumentListResponse,
    DocumentUploadResponse,
)
from backend.app.services.document_processor import DocumentProcessor
from backend.app.services.vector_store import VectorStoreService

router = APIRouter(prefix="/documents", tags=["Documents"])
vector_store = VectorStoreService()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="PDF Document to ingest and index"),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported."
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # 1. Deduplication via SHA-256
    file_hash = DocumentProcessor.compute_sha256(file_bytes)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE file_hash = ?", (file_hash,))
    existing = cursor.fetchone()

    if existing:
        doc_info = DocumentInfo(
            id=existing["id"],
            filename=existing["filename"],
            file_hash=existing["file_hash"],
            file_size_bytes=existing["file_size_bytes"],
            page_count=existing["page_count"],
            chunk_count=existing["chunk_count"],
            uploaded_at=existing["uploaded_at"],
            status=existing["status"],
        )
        conn.close()
        return DocumentUploadResponse(
            message=f"Document '{file.filename}' already exists and is indexed (deduplication triggered).",
            document=doc_info,
            chunks_created=existing["chunk_count"],
            is_duplicate=True,
        )

    # 2. Parse and chunk document
    doc_id = f"doc_{uuid.uuid4().hex[:10]}"
    processor = DocumentProcessor(
        chunk_size=chunk_size or settings.DEFAULT_CHUNK_SIZE,
        chunk_overlap=chunk_overlap or settings.DEFAULT_CHUNK_OVERLAP,
    )

    try:
        chunks = processor.process_pdf(
            document_id=doc_id,
            document_name=file.filename,
            file_bytes=file_bytes,
            file_hash=file_hash,
        )
    except Exception as e:
        logger.error(f"Failed to process PDF {file.filename}: {e}")
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse PDF content: {str(e)}"
        )

    # Save original PDF to documents directory
    saved_path = settings.DOCUMENTS_DIR / f"{doc_id}_{file.filename}"
    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    # 3. Index chunks into ChromaDB
    indexed_count = vector_store.add_chunks(chunks)

    # 4. Save metadata into SQLite
    uploaded_at = datetime.utcnow().isoformat()
    page_count = max([c.page_number for c in chunks], default=1)

    cursor.execute(
        """
        INSERT INTO documents (id, filename, file_hash, file_size_bytes, page_count, chunk_count, uploaded_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (doc_id, file.filename, file_hash, len(file_bytes), page_count, indexed_count, uploaded_at, "indexed"),
    )

    # Insert individual chunk records for tracking
    for c in chunks:
        cursor.execute(
            """
            INSERT INTO document_chunks (id, document_id, document_name, page_number, chunk_index, content)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (c.chunk_id, doc_id, file.filename, c.page_number, c.chunk_index, c.content),
        )

    conn.commit()
    conn.close()

    doc_info = DocumentInfo(
        id=doc_id,
        filename=file.filename,
        file_hash=file_hash,
        file_size_bytes=len(file_bytes),
        page_count=page_count,
        chunk_count=indexed_count,
        uploaded_at=uploaded_at,
        status="indexed",
    )

    return DocumentUploadResponse(
        message=f"Successfully indexed '{file.filename}' into {indexed_count} vector chunks.",
        document=doc_info,
        chunks_created=indexed_count,
        is_duplicate=False,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
    rows = cursor.fetchall()
    
    docs = [
        DocumentInfo(
            id=r["id"],
            filename=r["filename"],
            file_hash=r["file_hash"],
            file_size_bytes=r["file_size_bytes"],
            page_count=r["page_count"],
            chunk_count=r["chunk_count"],
            uploaded_at=r["uploaded_at"],
            status=r["status"],
        )
        for r in rows
    ]
    
    cursor.execute("SELECT COUNT(*) as count FROM document_chunks")
    total_chunks = cursor.fetchone()["count"]
    conn.close()

    return DocumentListResponse(
        total_documents=len(docs),
        total_chunks=total_chunks,
        documents=docs,
    )


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(document_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()

    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove from ChromaDB
    vector_store.delete_document(document_id)

    # Remove from SQLite
    cursor.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
    cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    conn.commit()
    conn.close()

    return {"message": f"Document '{doc['filename']}' and all vector embeddings deleted successfully."}


@router.post("/{document_id}/index", response_model=DocumentUploadResponse)
async def reindex_document(document_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()

    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found.")

    # Locate saved file
    saved_path = settings.DOCUMENTS_DIR / f"{document_id}_{doc['filename']}"
    if not saved_path.exists():
        conn.close()
        raise HTTPException(status_code=404, detail="Original document file not found on disk.")

    with open(saved_path, "rb") as f:
        file_bytes = f.read()

    # Clear old vectors & chunk records
    vector_store.delete_document(document_id)
    cursor.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))

    # Re-chunk and re-embed
    processor = DocumentProcessor()
    chunks = processor.process_pdf(
        document_id=document_id,
        document_name=doc["filename"],
        file_bytes=file_bytes,
        file_hash=doc["file_hash"],
    )
    indexed_count = vector_store.add_chunks(chunks)

    cursor.execute("UPDATE documents SET chunk_count = ? WHERE id = ?", (indexed_count, document_id))
    for c in chunks:
        cursor.execute(
            """
            INSERT INTO document_chunks (id, document_id, document_name, page_number, chunk_index, content)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (c.chunk_id, document_id, doc["filename"], c.page_number, c.chunk_index, c.content),
        )

    conn.commit()
    conn.close()

    doc_info = DocumentInfo(
        id=document_id,
        filename=doc["filename"],
        file_hash=doc["file_hash"],
        file_size_bytes=doc["file_size_bytes"],
        page_count=doc["page_count"],
        chunk_count=indexed_count,
        uploaded_at=doc["uploaded_at"],
        status="indexed",
    )

    return DocumentUploadResponse(
        message=f"Document '{doc['filename']}' successfully re-indexed.",
        document=doc_info,
        chunks_created=indexed_count,
        is_duplicate=False,
    )
