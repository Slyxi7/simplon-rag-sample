import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag.config.logging import get_logger, conversation_id
from rag.db.session import get_db
from rag.rag.chat_service import ChatService, ConversationNotFoundError

router = APIRouter()
logger = get_logger("chat")

class ChatRequest(BaseModel):
    message: str
    conversation_id: str

class ChatResponse(BaseModel):
    content: str
    sources: list[str] = []

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Set conversation context
    conversation_id.set(request.conversation_id)
    
    # Log request (without PII)
    logger.info(
        "Chat request received",
        extra={
            "event": "chat_request",
            "conversation_id": request.conversation_id,
            "message_length": len(request.message),
        }
    )
    
    try:
        # Validate conversation_id format
        try:
            conversation_uuid = uuid.UUID(request.conversation_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid conversation_id format. Must be a valid UUID.")
        
        # Use the existing RAG pipeline
        chat_service = ChatService()
        try:
            result = await chat_service.send_message(
                conversation_id=conversation_uuid,
                content=request.message,
                db=db
            )
        except ConversationNotFoundError:
            # Create conversation first with the specific ID, then send message
            from rag.db.models.conversation import Conversation
            conversation = Conversation(id=str(conversation_uuid))
            db.add(conversation)
            await db.commit()
            
            result = await chat_service.send_message(
                conversation_id=conversation_uuid,
                content=request.message,
                db=db
            )
        
        response = ChatResponse(
            content=result.content,
            sources=result.sources
        )
        
        logger.info(
            "Chat response generated",
            extra={
                "event": "chat_response",
                "conversation_id": request.conversation_id,
                "sources_count": len(response.sources),
            }
        )
        
        return response

        
    except Exception as e:
        logger.error(
            "Chat processing failed",
            extra={
                "event": "chat_error",
                "conversation_id": request.conversation_id,
                "error_type": type(e).__name__,
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")