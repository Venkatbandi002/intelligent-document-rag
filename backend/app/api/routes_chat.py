import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.database.models import get_db_connection
from backend.app.schemas.chat import (
    ChatHistoryItem,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    RetrievedPassage,
    SourceCitation,
)
from backend.app.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["Chat & RAG"])
rag_service = RAGService()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Core RAG conversational query endpoint.
    Retrieves semantic passages, optionally reranks, invokes grounded LLM, and formats citations.
    """
    try:
        response = rag_service.query(
            question=request.question,
            conversation_id=request.conversation_id or "default",
            top_k=request.top_k,
            enable_reranking=request.enable_reranking,
            document_filter=request.document_filter,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query execution error: {str(e)}"
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_history(conversation_id: str = Query("default")):
    """
    Fetches message history and citations for a conversation.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM chat_messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
        """,
        (conversation_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    items = []
    for r in rows:
        sources_raw = json.loads(r["sources_json"] or "[]")
        passages_raw = json.loads(r["retrieved_context_json"] or "[]")
        
        sources = [SourceCitation(**s) for s in sources_raw]
        passages = [RetrievedPassage(**p) for p in passages_raw]

        items.append(
            ChatHistoryItem(
                id=r["id"],
                role=r["role"],
                content=r["content"],
                sources=sources,
                retrieved_passages=passages,
                created_at=r["created_at"],
                latency_ms=r["latency_ms"],
            )
        )

    return ChatHistoryResponse(
        conversation_id=conversation_id,
        messages=items,
    )


@router.get("/conversations")
async def list_conversations():
    """Returns a list of conversation sessions with title, count, and timestamp."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            conversation_id,
            MIN(CASE WHEN role = 'user' THEN content END) as first_question,
            COUNT(*) as message_count,
            MAX(created_at) as last_activity
        FROM chat_messages
        GROUP BY conversation_id
        ORDER BY last_activity DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    conversations = []
    for r in rows:
        title = r["first_question"] or "Conversation"
        if len(title) > 36:
            title = title[:36] + "..."
        conversations.append({
            "conversation_id": r["conversation_id"],
            "title": title,
            "message_count": r["message_count"],
            "last_activity": r["last_activity"],
        })
    return {"conversations": conversations}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Deletes all messages for a specific conversation session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (conversation_id,))
    conn.commit()
    conn.close()
    return {"message": f"Conversation '{conversation_id}' deleted."}


@router.delete("/history")
async def clear_history(conversation_id: str = Query("default")):
    """Clears chat messages for a conversation session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (conversation_id,))
    conn.commit()
    conn.close()
    return {"message": f"Chat history for conversation '{conversation_id}' cleared."}

