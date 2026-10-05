import io
import uuid
from datetime import datetime
from pathlib import Path
from backend.app.core.config import settings
from backend.app.database.models import init_db, get_db_connection
from backend.app.services.document_processor import DocumentProcessor
from backend.app.services.vector_store import VectorStoreService

def ingest():
    init_db()
    processor = DocumentProcessor()
    vector_store = VectorStoreService()
    docs_dir = Path("evaluation/sample_docs")
    conn = get_db_connection()
    cursor = conn.cursor()

    for pdf_path in docs_dir.glob("*.pdf"):
        with open(pdf_path, "rb") as f:
            file_bytes = f.read()

        file_hash = DocumentProcessor.compute_sha256(file_bytes)
        cursor.execute("SELECT id FROM documents WHERE file_hash = ?", (file_hash,))
        if cursor.fetchone():
            print(f"Skipping already ingested {pdf_path.name}")
            continue

        doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        chunks = processor.process_pdf(
            document_id=doc_id,
            document_name=pdf_path.name,
            file_bytes=file_bytes,
            file_hash=file_hash,
        )
        vector_store.add_chunks(chunks)

        # Save to data/documents
        target_path = settings.DOCUMENTS_DIR / f"{doc_id}_{pdf_path.name}"
        with open(target_path, "wb") as f:
            f.write(file_bytes)

        page_count = max([c.page_number for c in chunks], default=1)
        now = datetime.utcnow().isoformat()
        cursor.execute(
            """
            INSERT INTO documents (id, filename, file_hash, file_size_bytes, page_count, chunk_count, uploaded_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, pdf_path.name, file_hash, len(file_bytes), page_count, len(chunks), now, "indexed")
        )
        for c in chunks:
            cursor.execute(
                """
                INSERT INTO document_chunks (id, document_id, document_name, page_number, chunk_index, content)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (c.chunk_id, doc_id, pdf_path.name, c.page_number, c.chunk_index, c.content)
            )
        print(f"Ingested {pdf_path.name}: {len(chunks)} chunks.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    ingest()
