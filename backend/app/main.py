from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.app.api.routes_chat import router as chat_router
from backend.app.api.routes_documents import router as documents_router
from backend.app.api.routes_evaluation import router as evaluation_router
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.models import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite tables & ensure storage directories
    logger.info("Initializing Enterprise Document Intelligence RAG Engine...")
    init_db()
    logger.info("Application initialized and ready to serve queries.")
    yield
    logger.info("Shutting down RAG Engine...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-Grade Enterprise Document Intelligence RAG System with Citations and Evaluation Framework",
    lifespan=lifespan,
)

# Enable CORS for cross-origin client apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(evaluation_router, prefix=settings.API_V1_PREFIX)


# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
    }


# Frontend Static Files & SPA serving
frontend_dir = settings.BASE_DIR / "frontend"
static_dir = frontend_dir / "static"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", tags=["Frontend"])
async def serve_index():
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}. Visit /docs for the interactive API documentation."
    }
