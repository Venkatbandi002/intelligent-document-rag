import hashlib
import io
import re
from typing import List, Tuple
from pypdf import PdfReader
from backend.app.schemas.document import DocumentChunk
from backend.app.core.logging import logger


class DocumentProcessor:
    """
    Handles PDF parsing, cleaning, metadata tagging, and recursive text chunking.
    Preserves exact page numbers and document provenance.
    """

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        """Computes SHA-256 hash of file content to detect duplicate uploads."""
        hasher = hashlib.sha256()
        hasher.update(file_bytes)
        return hasher.hexdigest()

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalizes whitespaces, removes non-printable characters, preserves structure."""
        if not text:
            return ""
        # Remove null bytes and non-printable control chars except tabs/newlines
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        # Normalize multiple horizontal whitespaces
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize excessive newlines (max 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def extract_pages_from_pdf(self, file_bytes: bytes) -> List[Tuple[int, str]]:
        """
        Extracts clean text per page from PDF bytes.
        Returns list of (page_number_1_indexed, text).
        """
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_content: List[Tuple[int, str]] = []
        
        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            extracted = page.extract_text() or ""
            cleaned = self.clean_text(extracted)
            if cleaned:
                pages_content.append((page_num, cleaned))
                
        return pages_content

    def recursive_split_text(self, text: str, separators: List[str] = None) -> List[str]:
        """
        Splits text hierarchically using natural boundary separators:
        paragraphs -> lines -> sentences -> words.
        """
        if separators is None:
            separators = ["\n\n", "\n", ". ", "; ", ", ", " "]

        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        # Find best separator
        sep = separators[-1]
        for s in separators:
            if s in text:
                sep = s
                break

        splits = text.split(sep)
        chunks: List[str] = []
        current_chunk = ""

        for part in splits:
            candidate = f"{current_chunk}{sep}{part}" if current_chunk else part
            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                # Handle single parts longer than chunk_size recursively with next separators
                if len(part) > self.chunk_size:
                    next_separators = separators[separators.index(sep) + 1 :] if sep in separators else []
                    if next_separators:
                        sub_chunks = self.recursive_split_text(part, next_separators)
                        chunks.extend(sub_chunks)
                        current_chunk = ""
                    else:
                        # Hard slice as last resort
                        for i in range(0, len(part), self.chunk_size - self.chunk_overlap):
                            slice_text = part[i : i + self.chunk_size]
                            if slice_text.strip():
                                chunks.append(slice_text.strip())
                        current_chunk = ""
                else:
                    # Apply overlap from previous chunk if available
                    if chunks and self.chunk_overlap > 0:
                        prev_text = chunks[-1]
                        overlap_text = prev_text[-self.chunk_overlap :] if len(prev_text) > self.chunk_overlap else prev_text
                        current_chunk = f"{overlap_text} {part}".strip()
                    else:
                        current_chunk = part

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def process_pdf(
        self,
        document_id: str,
        document_name: str,
        file_bytes: bytes,
        file_hash: str
    ) -> List[DocumentChunk]:
        """
        Full ingestion pipeline:
        Extracts pages -> cleans -> chunks with boundary awareness -> embeds metadata.
        """
        pages = self.extract_pages_from_pdf(file_bytes)
        all_chunks: List[DocumentChunk] = []
        chunk_idx = 0

        for page_num, page_text in pages:
            page_chunks = self.recursive_split_text(page_text)
            for c_text in page_chunks:
                if len(c_text.strip()) < 10:  # Skip degenerate small fragments
                    continue
                
                chunk_id = f"{document_id}_p{page_num}_c{chunk_idx}"
                metadata = {
                    "document_id": document_id,
                    "document_name": document_name,
                    "page_number": page_num,
                    "chunk_index": chunk_idx,
                    "doc_hash": file_hash,
                    "source": f"{document_name}, Page {page_num}",
                }
                
                all_chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_name=document_name,
                        page_number=page_num,
                        chunk_index=chunk_idx,
                        content=c_text,
                        metadata=metadata,
                    )
                )
                chunk_idx += 1

        logger.info(
            f"Processed document '{document_name}': {len(pages)} pages -> {len(all_chunks)} chunks."
        )
        return all_chunks
