import pytest
from backend.app.core.config import settings
from backend.app.schemas.document import DocumentChunk
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.rag_service import RAGService
from backend.app.services.reranker import RerankerService
from backend.app.services.vector_store import VectorStoreService


@pytest.fixture
def isolated_rag(tmp_path):
    chroma_dir = str(tmp_path / "chroma_rag_test")
    embedder = EmbeddingService()
    vector_store = VectorStoreService(persist_dir=chroma_dir, embedding_service=embedder)
    reranker = RerankerService(top_n=3)
    rag = RAGService(vector_store=vector_store, reranker=reranker)

    # Ingest test context
    chunks = [
        DocumentChunk(
            chunk_id="chunk_leave_1",
            document_name="Leave_Policy.pdf",
            page_number=4,
            chunk_index=0,
            content="Employees receive 20 days of annual paid leave every year. Leave requests must be submitted two weeks in advance.",
            metadata={"document_id": "doc_leave", "document_name": "Leave_Policy.pdf", "page_number": 4}
        )
    ]
    vector_store.add_chunks(chunks)
    return rag


def test_rag_grounded_answer_and_citations(isolated_rag):
    response = isolated_rag.query("How many days of annual paid leave do employees receive?")

    assert response.is_grounded is True
    assert "20 days" in response.answer or "20" in response.answer
    assert len(response.sources) >= 1
    assert response.sources[0].document_name == "Leave_Policy.pdf"
    assert response.sources[0].page_number == 4


def test_rag_hallucination_protection(isolated_rag):
    # Query completely unrelated to the ingested document
    response = isolated_rag.query("How do I assemble the Titan photovoltaic solar power inverter?")

    # System must refuse to answer rather than hallucinating
    assert response.is_grounded is False
    assert settings.NO_ANSWER_FALLBACK in response.answer
    assert len(response.sources) == 0
