import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from reportlab.pdfgen import canvas


def generate_pdf_buffer():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 700, "Enterprise Onboarding Manual. Standard work hours are 40 hours per week.")
    c.drawString(100, 650, "Full-time employees receive 20 days paid leave.")
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Enterprise Document Intelligence" in data["service"]


def test_document_upload_and_deduplication(client):
    pdf_buf = generate_pdf_buffer()
    files = {"file": ("Onboarding_Manual.pdf", pdf_buf, "application/pdf")}

    # Initial upload
    res1 = client.post("/api/v1/documents/upload", files=files)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["is_duplicate"] is False
    assert data1["document"]["filename"] == "Onboarding_Manual.pdf"
    doc_id = data1["document"]["id"]

    # Duplicate upload with identical content
    pdf_buf.seek(0)
    files2 = {"file": ("Onboarding_Manual_Copy.pdf", pdf_buf, "application/pdf")}
    res2 = client.post("/api/v1/documents/upload", files=files2)
    assert res2.status_code == 201
    data2 = res2.json()
    # Deduplication flag must be True because content hash matches
    assert data2["is_duplicate"] is True

    # List documents
    res_list = client.get("/api/v1/documents")
    assert res_list.status_code == 200
    docs = res_list.json()["documents"]
    assert any(d["id"] == doc_id for d in docs)

    # Chat query
    chat_payload = {
        "question": "What are the standard work hours?",
        "conversation_id": "test_conv",
        "top_k": 2
    }
    chat_res = client.post("/api/v1/chat", json=chat_payload)
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "40 hours" in chat_data["answer"] or chat_data["is_grounded"] is True

    # Chat history
    hist_res = client.get("/api/v1/chat/history?conversation_id=test_conv")
    assert hist_res.status_code == 200
    assert len(hist_res.json()["messages"]) >= 2

    # Clean up delete
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
