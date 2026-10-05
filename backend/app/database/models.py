import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import sqlite3
from backend.app.core.config import settings
from backend.app.core.logging import logger


def init_db(db_path: Optional[str] = None):
    path = db_path or str(settings.SQLITE_DB_PATH)
    logger.info(f"Initializing SQLite database at: {path}")
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    # Documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        file_hash TEXT NOT NULL UNIQUE,
        file_size_bytes INTEGER NOT NULL,
        page_count INTEGER NOT NULL,
        chunk_count INTEGER NOT NULL DEFAULT 0,
        uploaded_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'indexed'
    )
    """)
    
    # Chunks table (for tracking metadata and quick inspections)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        document_name TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
    )
    """)
    
    # Chat message records
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        sources_json TEXT DEFAULT '[]',
        retrieved_context_json TEXT DEFAULT '[]',
        latency_ms REAL DEFAULT 0.0,
        created_at TEXT NOT NULL
    )
    """)
    
    # Evaluation runs history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evaluation_runs (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        config_json TEXT NOT NULL,
        total_queries INTEGER NOT NULL,
        hit_rate REAL NOT NULL,
        precision_at_k REAL NOT NULL,
        recall_at_k REAL NOT NULL,
        mrr REAL NOT NULL,
        avg_latency_ms REAL NOT NULL,
        created_at TEXT NOT NULL,
        report_json TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or str(settings.SQLITE_DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
