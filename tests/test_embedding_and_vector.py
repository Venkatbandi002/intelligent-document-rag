import pytest
from backend.app.schemas.document import DocumentChunk
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.vector_store import VectorStoreService


def test_embedding_service():
    embedder = EmbeddingService()
    texts = [
        "Annual leave is 20 days per year.",
        "Server hardware requires 8 GB RAM."
    ]
    vecs = embedder.embed_texts(texts)
    assert len(vecs) == 2
    assert len(vecs[0]) == embedder.dimension

    query_vec = embedder.embed_query("How many days leave?")
    assert len(query_vec) == embedder.dimension


def test_vector_store_indexing_and_search(tmp_path):
    chroma_dir = str(tmp_path / "chroma_test")
    embedder = EmbeddingService()
    store = VectorStoreService(persist_dir=chroma_dir, embedding_service=embedder)

    chunks = [
        DocumentChunk(
            chunk_id="chunk_1",
            document_name="Leave_Policy.pdf",
            page_number=1,
            chunk_index=0,
            content="Employees receive 20 days of annual paid leave every year.",
            metadata={"document_id": "doc_1", "document_name": "Leave_Policy.pdf", "page_number": 1}
        ),
        DocumentChunk(
            chunk_id="chunk_2",
            document_name="Hardware_Guide.pdf",
            page_number=4,
            chunk_index=1,
            content="The network switch requires dual 10 Gigabit Ethernet ports.",
            metadata={"document_id": "doc_2", "document_name": "Hardware_Guide.pdf", "page_number": 4}
        )
    ]

    indexed = store.add_chunks(chunks)
    assert indexed == 2

    # Query matching chunk 1
    results = store.similarity_search("How much annual leave do I get?", top_k=2)
    assert len(results) > 0
    top_result = results[0]
    assert top_result["document_name"] == "Leave_Policy.pdf"
    assert "20 days" in top_result["content"]
    assert top_result["page_number"] == 1

    # Metadata filtering test
    filtered = store.similarity_search("network switch", top_k=2, filter_dict={"document_name": "Hardware_Guide.pdf"})
    assert len(filtered) == 1
    assert filtered[0]["document_name"] == "Hardware_Guide.pdf"

    # Deletion test
    store.delete_document("doc_1")
    post_delete = store.similarity_search("annual leave", top_k=2, filter_dict={"document_name": "Leave_Policy.pdf"})
    assert len(post_delete) == 0
