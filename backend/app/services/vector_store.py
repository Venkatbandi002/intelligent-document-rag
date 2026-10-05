from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.document import DocumentChunk
from backend.app.services.embedding_service import EmbeddingService


class VectorStoreService:
    """
    Manages persistent ChromaDB vector storage, chunk indexing,
    metadata filtering, and similarity search.
    """

    COLLECTION_NAME = "enterprise_documents"

    def __init__(self, persist_dir: Optional[str] = None, embedding_service: Optional[EmbeddingService] = None):
        self.persist_dir = persist_dir or str(settings.CHROMA_PERSIST_DIR)
        self.embedding_service = embedding_service or EmbeddingService()
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """
        Embeds and indexes document chunks into ChromaDB collection with rich metadata.
        """
        if not chunks:
            return 0

        ids = [c.chunk_id for c in chunks]
        texts = [c.content for c in chunks]
        metadatas = [
            {
                "document_id": c.metadata.get("document_id", ""),
                "document_name": c.document_name,
                "page_number": int(c.page_number),
                "chunk_index": int(c.chunk_index),
                "doc_hash": c.metadata.get("doc_hash", ""),
                "source": c.metadata.get("source", f"{c.document_name}, Page {c.page_number}"),
            }
            for c in chunks
        ]

        # Generate embeddings
        embeddings = self.embedding_service.embed_texts(texts)

        # Batch upsert to ChromaDB
        BATCH_SIZE = 250
        for i in range(0, len(chunks), BATCH_SIZE):
            end = i + BATCH_SIZE
            self.collection.upsert(
                ids=ids[i:end],
                documents=texts[i:end],
                metadatas=metadatas[i:end],
                embeddings=embeddings[i:end],
            )

        logger.info(f"Indexed {len(chunks)} chunks into ChromaDB collection '{self.COLLECTION_NAME}'.")
        return len(chunks)

    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic vector search with optional metadata filtering.
        Returns list of matching chunks with similarity scores.
        """
        query_vector = self.embedding_service.embed_query(query)
        
        query_args = {
            "query_embeddings": [query_vector],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if filter_dict:
            query_args["where"] = filter_dict

        results = self.collection.query(**query_args)
        
        passages: List[Dict[str, Any]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return passages

        ids = results["ids"][0]
        docs = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for chunk_id, doc, meta, dist in zip(ids, docs, metadatas, distances):
            # Chroma returns cosine distance (0 to 2 for cosine space).
            # Convert distance to similarity score in [0, 1].
            similarity = max(0.0, 1.0 - (dist / 2.0))
            passages.append({
                "chunk_id": chunk_id,
                "document_name": meta.get("document_name", "Unknown"),
                "page_number": int(meta.get("page_number", 1)),
                "content": doc,
                "similarity_score": round(float(similarity), 4),
                "metadata": meta,
            })

        return passages

    def delete_document(self, document_id: str) -> None:
        """Removes all indexed chunks associated with a document ID."""
        try:
            self.collection.delete(where={"document_id": document_id})
            logger.info(f"Removed chunks for document_id '{document_id}' from vector store.")
        except Exception as e:
            logger.error(f"Error deleting chunks for document_id '{document_id}': {e}")

    def get_count(self) -> int:
        """Returns total chunks stored in the collection."""
        return self.collection.count()

    def reset_collection(self) -> None:
        """Clears all vectors from the collection."""
        self.client.delete_collection(self.COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
