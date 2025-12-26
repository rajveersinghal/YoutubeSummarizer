# backend/routes/chat.py - COMPLETE WITH RAG INTEGRATION

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
import time
import uuid

from middleware.auth import get_current_user
from database.database import get_db
from services.ai_service import AIService
from services.rag_service import RAGService
from config.settings import settings
from config.logging_config import logger

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Initialize services
ai_service = AIService()
rag_service = RAGService()

# ============================================================================
# MODELS
# ============================================================================

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Chat"
    context_type: Optional[str] = None
    context_id: Optional[str] = None

class SendMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class UpdateConversationRequest(BaseModel):
    title: str

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new conversation"""
    try:
        conversation_id = str(uuid.uuid4())
        
        conversation_doc = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "title": request.title,
            "created_at": time.time(),
            "updated_at": time.time(),
            "message_count": 0,
            "context_type": request.context_type,
            "context_id": request.context_id,
            "uses_rag": bool(request.context_id),  # If context exists, use RAG
        }
        
        db.conversations.insert_one(conversation_doc)
        
        logger.info(f"✅ Conversation created: {conversation_id}")
        
        return {
            "conversation_id": conversation_id,
            "title": request.title,
            "created_at": conversation_doc["created_at"],
            "uses_rag": conversation_doc["uses_rag"]
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation"
        )

@router.get("/conversations")
async def get_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all conversations for user"""
    try:
        skip = (page - 1) * page_size
        
        conversations = list(
            db.conversations
            .find({"user_id": user_id})
            .sort("updated_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        
        total = db.conversations.count_documents({"user_id": user_id})
        
        # Format conversations
        formatted_conversations = []
        for conv in conversations:
            formatted_conversations.append({
                "conversation_id": conv.get("conversation_id"),
                "title": conv.get("title"),
                "message_count": conv.get("message_count", 0),
                "context_type": conv.get("context_type"),
                "context_id": conv.get("context_id"),
                "uses_rag": conv.get("uses_rag", False),
                "created_at": conv.get("created_at"),
                "updated_at": conv.get("updated_at"),
            })
        
        return {
            "conversations": formatted_conversations,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting conversations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversations"
        )

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get a specific conversation with messages"""
    try:
        # Get conversation
        conversation = db.conversations.find_one({
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Get messages
        messages = list(
            db.messages
            .find({"conversation_id": conversation_id})
            .sort("created_at", 1)
        )
        
        # Format messages
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "message_id": msg.get("message_id"),
                "role": msg.get("role"),
                "content": msg.get("content"),
                "created_at": msg.get("created_at"),
                "sources": msg.get("sources"),  # RAG sources
            })
        
        return {
            "conversation_id": conversation.get("conversation_id"),
            "title": conversation.get("title"),
            "context_type": conversation.get("context_type"),
            "context_id": conversation.get("context_id"),
            "uses_rag": conversation.get("uses_rag", False),
            "created_at": conversation.get("created_at"),
            "updated_at": conversation.get("updated_at"),
            "messages": formatted_messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversation"
        )

@router.post("/messages")
async def send_message(
    request: SendMessageRequest,
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Send a message and get AI response with RAG
    """
    try:
        message = request.message.strip()
        conversation_id = request.conversation_id
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        # Create conversation if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            conversation_doc = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "title": message[:50] + ("..." if len(message) > 50 else ""),
                "created_at": time.time(),
                "updated_at": time.time(),
                "message_count": 0,
                "context_type": None,
                "context_id": None,
                "uses_rag": False,
            }
            db.conversations.insert_one(conversation_doc)
            logger.info(f"✅ New conversation created: {conversation_id}")
        else:
            # Verify conversation exists and belongs to user
            conversation = db.conversations.find_one({
                "conversation_id": conversation_id,
                "user_id": user_id
            })
            
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
        
        # Save user message
        user_message_id = str(uuid.uuid4())
        user_message_doc = {
            "message_id": user_message_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": "user",
            "content": message,
            "created_at": time.time(),
        }
        db.messages.insert_one(user_message_doc)
        
        # ✅ GET CONVERSATION CONTEXT FOR RAG
        conversation_data = db.conversations.find_one({"conversation_id": conversation_id})
        
        context = None
        context_type = None
        sources = []
        
        if conversation_data:
            stored_context_type = conversation_data.get("context_type")
            stored_context_id = conversation_data.get("context_id")
            uses_rag = conversation_data.get("uses_rag", False)
            
            # ✅ USE RAG IF AVAILABLE
            if uses_rag and stored_context_type and stored_context_id:
                logger.info(f"🧠 Using RAG for {stored_context_type}: {stored_context_id}")
                
                if stored_context_type == "document":
                    # Search document chunks using RAG
                    results = rag_service.search_documents(message, n_results=5)
                    
                    if results:
                        # Build context from relevant chunks
                        context_chunks = []
                        for result in results:
                            context_chunks.append(result["content"])
                            sources.append({
                                "chunk_index": result["metadata"].get("chunk_index"),
                                "title": result["metadata"].get("title"),
                                "relevance": 1 - result.get("distance", 0)
                            })
                        
                        context = "\n\n---\n\n".join(context_chunks)
                        context_type = "document"
                        
                        logger.info(f"📄 Retrieved {len(results)} relevant document chunks")
                
                elif stored_context_type in ["video", "youtube"]:
                    # Search video chunks using RAG
                    results = rag_service.search_videos(message, n_results=5)
                    
                    if results:
                        # Build context from relevant chunks
                        context_chunks = []
                        for result in results:
                            context_chunks.append(result["content"])
                            sources.append({
                                "chunk_index": result["metadata"].get("chunk_index"),
                                "title": result["metadata"].get("title"),
                                "relevance": 1 - result.get("distance", 0)
                            })
                        
                        context = "\n\n---\n\n".join(context_chunks)
                        context_type = "youtube"
                        
                        logger.info(f"🎥 Retrieved {len(results)} relevant video chunks")
            
            # ✅ FALLBACK: Load full context if RAG not available
            elif stored_context_type and stored_context_id and not uses_rag:
                logger.info(f"📋 Loading full context (no RAG)")
                
                if stored_context_type == "document":
                    doc = db.documents.find_one({"document_id": stored_context_id})
                    if doc:
                        context = doc.get("content", "")
                        context_type = "document"
                
                elif stored_context_type in ["video", "youtube"]:
                    video = db.videos.find_one({"video_id": stored_context_id})
                    if video:
                        context = video.get("transcript", "")
                        context_type = "youtube"
        
        # ✅ GET CONVERSATION HISTORY
        history_messages = list(
            db.messages
            .find({"conversation_id": conversation_id})
            .sort("created_at", 1)
            .limit(20)  # Last 20 messages
        )
        
        history = []
        for msg in history_messages[:-1]:  # Exclude current message
            history.append({
                "role": msg.get("role"),
                "content": msg.get("content")
            })
        
        # ✅ GENERATE AI RESPONSE
        logger.info(f"🤖 Generating AI response...")
        logger.info(f"   - Context: {'Yes' if context else 'No'}")
        logger.info(f"   - Context Type: {context_type}")
        logger.info(f"   - History: {len(history)} messages")
        logger.info(f"   - RAG Sources: {len(sources)}")
        
        ai_response = await ai_service.generate_response(
            message=message,
            history=history,
            context=context,
            context_type=context_type
        )
        
        # Save AI message
        ai_message_id = str(uuid.uuid4())
        ai_message_doc = {
            "message_id": ai_message_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": "assistant",
            "content": ai_response,
            "created_at": time.time(),
            "sources": sources if sources else None,  # ✅ Store RAG sources
        }
        db.messages.insert_one(ai_message_doc)
        
        # Update conversation
        db.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {"updated_at": time.time()},
                "$inc": {"message_count": 2}
            }
        )
        
        logger.info(f"✅ Messages saved to conversation: {conversation_id}")
        
        return {
            "conversation_id": conversation_id,
            "user_message": {
                "message_id": user_message_id,
                "role": "user",
                "content": message,
                "created_at": user_message_doc["created_at"]
            },
            "ai_message": {
                "message_id": ai_message_id,
                "role": "assistant",
                "content": ai_response,
                "created_at": ai_message_doc["created_at"],
                "sources": sources if sources else None
            },
            "rag_used": bool(sources),
            "context_type": context_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error sending message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )

@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update conversation title"""
    try:
        result = db.conversations.update_one(
            {
                "conversation_id": conversation_id,
                "user_id": user_id
            },
            {
                "$set": {
                    "title": request.title,
                    "updated_at": time.time()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        logger.info(f"✅ Conversation updated: {conversation_id}")
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "title": request.title
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete conversation and all its messages"""
    try:
        # Delete conversation
        result = db.conversations.delete_one({
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Delete all messages
        db.messages.delete_many({"conversation_id": conversation_id})
        
        logger.info(f"✅ Conversation deleted: {conversation_id}")
        
        return {
            "success": True,
            "message": "Conversation deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )

@router.post("/search")
async def search_content(
    query: str = Query(..., min_length=1),
    search_type: str = Query("all", regex="^(all|documents|videos)$"),
    n_results: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user),
):
    """
    Search across documents and videos using RAG
    """
    try:
        logger.info(f"🔍 Searching for: '{query}' (type: {search_type})")
        
        results = {}
        
        if search_type in ["all", "documents"]:
            doc_results = rag_service.search_documents(query, n_results)
            results["documents"] = doc_results
        
        if search_type in ["all", "videos"]:
            video_results = rag_service.search_videos(query, n_results)
            results["videos"] = video_results
        
        total_results = sum(len(v) for v in results.values())
        
        logger.info(f"✅ Found {total_results} results")
        
        return {
            "query": query,
            "search_type": search_type,
            "results": results,
            "total": total_results
        }
        
    except Exception as e:
        logger.error(f"❌ Search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )

__all__ = ["router"]
