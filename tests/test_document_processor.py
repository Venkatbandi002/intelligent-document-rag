import io
import pytest
from backend.app.services.document_processor import DocumentProcessor
from reportlab.pdfgen import canvas


def create_dummy_pdf_bytes(num_pages: int = 2) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(1, num_pages + 1):
        c.drawString(100, 700, f"Page {i} Header: Enterprise Policy Documentation.")
        c.drawString(100, 650, f"Section {i}: Employees must adhere to guideline {i}. Annual leave is granted.")
        c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def test_sha256_computation():
    content1 = b"Sample Document A"
    content2 = b"Sample Document A"
    content3 = b"Sample Document B"

    hash1 = DocumentProcessor.compute_sha256(content1)
    hash2 = DocumentProcessor.compute_sha256(content2)
    hash3 = DocumentProcessor.compute_sha256(content3)

    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64


def test_clean_text():
    dirty = "Line 1   with   spaces.\x00\x05\n\n\n\nLine 2 with \t tabs."
    cleaned = DocumentProcessor.clean_text(dirty)

    assert "\x00" not in cleaned
    assert "\x05" not in cleaned
    assert "   " not in cleaned
    assert "\n\n\n" not in cleaned


def test_recursive_split_text():
    processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
    sample_text = (
        "Paragraph 1 contains some standard facts about company operations. "
        "It provides guidelines for regular working routines.\n\n"
        "Paragraph 2 discusses annual leaves and healthcare insurance provisions. "
        "All full-time staff members are eligible."
    )

    chunks = processor.recursive_split_text(sample_text)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 120  # account for minor boundary adjustments


def test_process_pdf_metadata_preservation():
    pdf_bytes = create_dummy_pdf_bytes(num_pages=3)
    file_hash = DocumentProcessor.compute_sha256(pdf_bytes)
    processor = DocumentProcessor(chunk_size=300, chunk_overlap=50)

    chunks = processor.process_pdf(
        document_id="doc_test123",
        document_name="Test_Policy.pdf",
        file_bytes=pdf_bytes,
        file_hash=file_hash,
    )

    assert len(chunks) >= 3
    # Check page preservation
    pages = {c.page_number for c in chunks}
    assert 1 in pages
    assert 2 in pages
    assert 3 in pages

    for c in chunks:
        assert c.document_name == "Test_Policy.pdf"
        assert c.metadata["document_id"] == "doc_test123"
        assert c.metadata["doc_hash"] == file_hash
        assert f"Page {c.page_number}" in c.metadata["source"]
