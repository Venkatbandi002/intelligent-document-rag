# ⚡ Enterprise Intelligent Document RAG Agent

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6633?style=for-the-badge)](https://www.trychroma.com/)
[![Gemini](https://img.shields.io/badge/Google_Gemini-1.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-000000?style=for-the-badge)](https://ollama.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**A Production-Grade, Evaluation-Driven Document Intelligence Retrieval-Augmented Generation (RAG) Platform.**  
*Engineered for enterprise knowledge discovery, strict anti-hallucination guardrails, verifiable page-level citation provenance, and multi-model LLM orchestration (Gemini, OpenAI, Ollama, & Offline Grounded Extractor).*

[Architecture](#architecture-diagram) • [Key Features](#key-features) • [Quickstart](#quickstart-guide) • [Multi-Model Setup](#multi-model-llm-support) • [Evaluation](#empirical-evaluation-framework) • [API Docs](#api-reference)

</div>

---

## 📌 Executive Summary

Enterprise document search frequently suffers from two critical flaws: **hallucinatory answers** and **loss of provenance** (not knowing which exact sentence or page justified a response).

This project solves both problems with an end-to-end, audit-ready RAG system:
- **Zero Hallucination Guarantee**: Strict similarity threshold gating and prompt constraints ensure the system explicitly refuses out-of-domain queries when evidence is absent.
- **Verifiable Citations**: Every generated fact is anchored to exact document pages `[Document Name, Page X]` with interactive passage inspection.
- **Hybrid Retrieval**: Combines dense vector semantics (`all-MiniLM-L6-v2` in **ChromaDB**) with **BM25 lexical reranking** to eliminate false-positive vector collisions.
- **Flexible LLM Runtime**: Seamlessly switch at runtime between **Google Gemini**, **OpenAI**, local private **Ollama** (Llama 3/Mistral), or the built-in deterministic offline extractor (0 API cost).
- **Production UI**: Ultra-clean glassmorphism desktop web experience featuring a floating dock, collapsible sidebar, multi-session chat history, and document management.

---

## 🏛️ Architecture Diagram

```
                                      ┌─────────────────────────────────────────────────────────┐
                                      │              DOCUMENT INGESTION PIPELINE                │
                                      └─────────────────────────────────────────────────────────┘
   Uploaded PDF                                                                                             ChromaDB
 [Policy/Manual] ──> [Page Detection] ──> [Clean & Normalize] ──> [Recursive Chunking] ──> [Embeddings] ──> [Vector Store]
                            │                     │                  (600 chars, 100 ovl)   (all-MiniLM-L6-v2)     │
                            ▼                     ▼                                                                 │
                   [Metadata Extraction: Doc Name, Page, SHA-256 Hash] ──> [SQLite App Store]                       │
                                                                                                                    │
════════════════════════════════════════════════════════════════════════════════════════════════════════════════════│════════
                                                                                                                    │
                                      ┌─────────────────────────────────────────────────────────┐                   │
                                      │                 RAG RETRIEVAL & SYNTHESIS               │                   │
                                      └─────────────────────────────────────────────────────────┘                   ▼
 User Question ──> [Query Embedding] ───────────────────────────> [Vector Cosine Search] ────────────> [Top-K Candidates]
                                                                  (Metadata Filter Scoping)                     │
                                                                                                                ▼
                                                                                                      [Hybrid BM25 Reranker]
                                                                                                      (Dense Sim + Lexical)
                                                                                                                │
                                                                                                                ▼
 [Grounded Answer + Provenance Badges] <── [Citation Extractor] <── [Strict Grounded LLM] <── [Top-3 Context Passages]
  - Verified Sources: Page numbers         - Regex & passage match   (Gemini / OpenAI / Ollama)
  - Passage Text Inspection Modal          - Refuses if out-of-domain
```

---

## 🚀 Key Features

### 1. Document Parsing & Cryptographic Deduplication
- **Page-Aware PDF Processing**: Uses `pypdf` to extract text while strictly preserving 1-indexed page offsets.
- **SHA-256 Deduplication**: Hashes file content prior to ingestion; prevents redundant indexing and vector drift.
- **Structured SQLite Audit Log**: Maintains metadata records of all ingested files, chunk counts, and indexing timestamps.

### 2. Hierarchical Recursive Text Chunking
- Configurable chunk size (default: **600 characters**) with **100-character overlap**.
- Natural delimiter hierarchy (`\n\n` $\to$ `\n` $\to$ `. ` $\to$ ` `) preventing mid-sentence semantic truncation.

### 3. Two-Stage Hybrid Retrieval & Reranking
- **Stage 1 (Coarse Retrieval)**: Dense vector similarity search via `sentence-transformers` (`all-MiniLM-L6-v2`) in **ChromaDB** with HNSW indexing.
- **Stage 2 (Fine Reranking)**: Hybrid BM25Okapi scoring combining semantic similarity with lexical term frequencies and exact query match bonuses:
  $$\text{Score}_{\text{hybrid}} = 0.55 \cdot \text{Sim}_{\text{dense}} + 0.35 \cdot \text{Score}_{\text{BM25}} + \text{Bonus}_{\text{exact}}$$

### 4. Anti-Hallucination & Provenance Guardrails
- **Cosine Threshold Gating**: Queries with maximum similarity below `0.25` trigger an automated refusal (*"I could not find sufficient information in the uploaded documents to answer your question"*).
- **Strict Evidence Prompting**: Prohibits extrapolation or external training bias.
- **Citation Badges**: Answers cite sources as `[Document, Page X]`. The UI allows one-click inspection of retrieved passages, chunk IDs, and similarity scores.

### 5. Multi-Model LLM Orchestration
- **Google Gemini API**: Direct REST and official SDK fallback (`gemini-1.5-flash`, `gemini-1.5-pro`).
- **OpenAI API**: Full GPT-4o / GPT-4o-mini support.
- **Ollama (Local & Free)**: Zero cloud dependency; runs `llama3`, `mistral`, `phi3`, or `deepseek-r1` directly on `http://localhost:11434`.
- **Deterministic Extractive Fallback**: If no API keys or local LLMs are active, a built-in extractive synthesizer extracts grounded answers directly from context passages with 100% uptime and zero crashes.

### 6. Modern Glassmorphism Web Interface
- **Floating Bottom Dock**: Fast switching between **Chat & Grounding**, **Document Repository**, and **System Diagnostics & Evaluation**.
- **Collapsible Sidebar**: Real-time chat session history with "New Chat" and "Delete Chat" management.
- **Live LLM Switcher**: Change providers and model names on-the-fly without restarting the server.
- **Telemetry Breakdown**: Visual latency breakdown (Retrieval Time + Reranking Time + Synthesis Time).

---

## 🛠️ Tech Stack

| Layer | Component | Technology | Rationale |
|---|---|---|---|
| **API Backend** | Web Framework | **FastAPI** (Python 3.11+) | Async performance, automated OpenAPI / Swagger docs |
| **Vector DB** | Vector Store | **ChromaDB** | Embedded HNSW indexing, persistent local storage, metadata filtering |
| **Embeddings** | Dense Embedder | **SentenceTransformers (`all-MiniLM-L6-v2`)** | 384-dimensional embeddings, high throughput, zero API latency |
| **Reranker** | Lexical Scorer | **BM25Okapi** | High-precision second-stage ranking without requiring GPU compute |
| **Database** | Relational DB | **SQLite 3** | Lightweight ACID store for chat sessions, file hashes, and benchmark logs |
| **LLM Runtime** | Multi-Provider | **Gemini / OpenAI / Ollama / Local Extractor** | Flexible choice between top-tier cloud models and 100% offline local privacy |
| **Frontend** | User Interface | **Vanilla HTML5, CSS3 & JavaScript** | Glassmorphism aesthetics, responsive, zero bulky frontend dependencies |
| **DevOps** | Containerization | **Docker & Docker Compose** | Reproducible builds, non-root security, healthcheck monitoring |

---

## ⚡ Quickstart Guide

### Prerequisites
- **Python 3.11+** installed
- **Git** installed

### 1. Clone the Repository
```bash
git clone https://github.com/Venkatbandi002/intelligent-document-rag.git
cd intelligent-document-rag
```

### 2. Create and Activate Virtual Environment
```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` to customize settings or add optional API keys:
```env
# Optional: Provide if you want to use Google Gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# Optional: Provide if you want to use OpenAI
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Optional: Configure Ollama local endpoint
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Default active provider: gemini | openai | ollama | mock
LLM_PROVIDER=ollama
```
*(Note: If no API key is provided and Ollama is not running, the system will seamlessly use the built-in Grounded Extractor with 100% uptime!)*

### 5. Launch the Application
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser at:
👉 **Web Application**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)  
👉 **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🦙 Multi-Model LLM Support

### Running with Ollama (100% Local & Free)
1. Download and install [Ollama](https://ollama.com/).
2. Pull and start your preferred model in a terminal:
   ```bash
   ollama run llama3
   ```
   *(Or `ollama run mistral`, `ollama run phi3`, `ollama run qwen2.5`)*
3. In the DocRAG UI, click **⚙️ Configure LLM** in the dock, select **🦙 Ollama Local (Free / Offline)**, enter `llama3`, and click **Save & Activate**.

### Running with Google Gemini
1. Get a free API key from [Google AI Studio](https://aistudio.google.com/).
2. Click **⚙️ Configure LLM** in the UI dock, select **✨ Google Gemini**, paste your key, and click **Save & Activate**.

---

## 📊 Empirical Evaluation Framework

This repository includes a quantitative evaluation framework for measuring retrieval and generation quality against a golden enterprise test set (`evaluation/questions.json`).

### Running the Evaluation CLI
```bash
python evaluation/run_evaluation.py
```

### Measured RAG Metrics
- **Hit Rate**: Probability that at least one ground-truth passage appears in Top-K.
- **Precision@K**: Ratio of retrieved passages that are genuinely relevant to the query.
- **Recall@K**: Proportion of total expected reference pages successfully retrieved.
- **MRR (Mean Reciprocal Rank)**: Position penalty measuring rank placement of the first relevant chunk ($1 / \text{rank}$).
- **Faithfulness Score**: Measures whether the synthesized answer contains only facts verifiable against retrieved chunks.

### Evaluation Results (Sample Run)
| Metric | Score | Benchmark Target | Status |
|---|---|---|---|
| **Hit Rate** | **100%** | > 85% | 🟢 Passing |
| **Precision@3** | **83.3%** | > 70% | 🟢 Passing |
| **Recall@3** | **90.0%** | > 75% | 🟢 Passing |
| **MRR** | **0.95** | > 0.80 | 🟢 Passing |
| **Faithfulness** | **1.00** | > 0.90 | 🟢 Passing |

---

## 📁 Repository Structure

```
intelligent-document-rag/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application entry & lifespans
│   │   ├── api/
│   │   │   ├── routes_documents.py     # PDF upload, listing, chunk inspection & deletion
│   │   │   ├── routes_chat.py          # Grounded RAG query & conversation history
│   │   │   ├── routes_settings.py      # Runtime LLM provider & API key management
│   │   │   └── routes_evaluation.py    # Metric benchmarks & evaluation runner
│   │   ├── core/
│   │   │   ├── config.py               # Pydantic Settings & environment validation
│   │   │   └── logging.py              # Structured application logger
│   │   ├── database/
│   │   │   └── models.py               # SQLite schemas (documents, chunks, sessions, evals)
│   │   ├── schemas/
│   │   │   ├── chat.py                 # Pydantic models for chat requests and responses
│   │   │   ├── document.py             # Pydantic models for documents & chunks
│   │   │   └── evaluation.py           # Evaluation models & metrics
│   │   └── services/
│   │       ├── document_processor.py   # PDF text extraction & recursive chunker
│   │       ├── embedding_service.py    # SentenceTransformer dense embeddings
│   │       ├── vector_store.py         # ChromaDB persistence & HNSW search
│   │       ├── reranker.py             # BM25Okapi + semantic hybrid reranker
│   │       ├── llm_service.py          # Unified LLM provider (Gemini, OpenAI, Ollama, Mock)
│   │       ├── rag_service.py          # Master RAG pipeline orchestrator
│   │       └── evaluation_service.py   # RAG metric evaluator
├── frontend/
│   ├── index.html                      # Single-page glassmorphism dashboard
│   └── static/
│       ├── css/style.css               # Modern enterprise dark styling system
│       └── js/app.js                   # Reactive controller for chat, docs & settings
├── evaluation/
│   ├── questions.json                  # Golden benchmark questions & expected citations
│   ├── sample_docs/                    # Sample enterprise policies & technical documents
│   └── run_evaluation.py               # CLI benchmark runner
├── tests/
│   ├── conftest.py                     # Pytest fixtures and mocks
│   ├── test_document_processor.py      # PDF parsing & chunking tests
│   ├── test_embedding_and_vector.py    # ChromaDB & embedding tests
│   ├── test_reranker.py                # Hybrid reranking tests
│   ├── test_rag_pipeline.py            # Hallucination guard & citation tests
│   └── test_api_endpoints.py           # Full API integration tests
├── Dockerfile                          # Multi-stage production container build
├── docker-compose.yml                  # Container orchestration
├── requirements.txt                    # Project Python dependencies
├── .env.example                        # Template environment variables
├── .gitignore                          # Git ignore specification
└── README.md                           # Project documentation
```

---

## 🧪 Testing & Quality Assurance

Run the test suite with `pytest`:
```bash
pytest -v
```

All 11 unit and integration tests validate:
- PDF text extraction and recursive chunking boundary preservation
- Vector store embeddings and similarity retrieval
- BM25 reranking scoring logic and exact term matches
- Grounded citation parsing and fallback extraction
- Full API endpoint operations (upload, search, settings, evaluation)

---

## 🐳 Docker Deployment

Run the complete application via Docker:

```bash
# Build and start container
docker-compose up --build -d

# Check logs
docker-compose logs -f

# Stop container
docker-compose down
```

The container includes healthcheck monitoring and runs under an unprivileged user for security compliance.

---

## 📄 License

This project is licensed under the **MIT License** — feel free to use, modify, and distribute it for personal and commercial projects.
