import httpx
import uuid
from app.logging import get_logger
from app.config import API_TIMEOUT_SECONDS
 
logger = get_logger("api_client")



def _timeout() -> httpx.Timeout:
    """Generous read timeout (chat endpoint runs the LLM agent graph), short
    connect/write timeouts because those should be fast on a local network."""
    return httpx.Timeout(
        connect=10.0,
        read=API_TIMEOUT_SECONDS,
        write=30.0,
        pool=30.0,
    )


def create_conversation(base_url: str) -> str:
    """Generate a conversation ID locally since the API doesn't have a conversations endpoint."""
    conversation_id = str(uuid.uuid4())
    
    logger.info(
        "Generated conversation ID locally",
        extra={
            "event": "conversation_created",
            "conversation_id": conversation_id
        }
    )
    
    return conversation_id


def send_message(base_url: str, conversation_id: str, content: str) -> dict:
    """Send a user message and return the assistant response."""
    
    logger.info(
        "Sending message via API",
        extra={
            "event": "api_message_send",
            "conversation_id": conversation_id,
            "message_length": len(content)
        }
    )
    
    try:
        with httpx.Client(timeout=_timeout()) as client:
            response = client.post(
                f"{base_url}/api/v1/chat",
                json={"message": content, "conversation_id": conversation_id},
                headers={"X-Conversation-ID": conversation_id},
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(
                "API response received",
                extra={
                    "event": "api_response_received",
                    "conversation_id": conversation_id,
                    "sources_count": len(data.get("sources", [])),
                    "response_length": len(data.get("content", "")),
                    "request_id": response.headers.get("X-Request-ID", "")
                }
            )
            
            return {
                "content": data.get("content", ""),
                "sources": data.get("sources", []),
            }
            
    except httpx.HTTPStatusError as e:
        logger.error(
            "API message send failed",
            extra={
                "event": "api_message_error",
                "conversation_id": conversation_id,
                "status_code": e.response.status_code,
                "request_id": e.response.headers.get("X-Request-ID", "")
            },
            exc_info=True
        )
        raise
    except (httpx.ConnectError, httpx.ReadTimeout) as e:
        logger.error(
            "API connection timeout",
            extra={
                "event": "api_timeout",
                "conversation_id": conversation_id,
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise