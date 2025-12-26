# backend/routes/chat.py - COMPLETE WITH ACTIVITY LOGGING

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional
import time
import uuid

from middleware.auth import get_current_user
from database.database import get_db
from services.ai_service import AIService
from config.logging_config import logger

router = APIRouter(prefix="/api/chat", tags=["Chat"])
ai_service = AIService()

# ============================================================================
# ACTIVITY LOGGER HELPER
# ============================================================================

def log_activity(
    user_id: str,
    activity_type: str,
    action: str,
    resource_type: str = None,
    resource_id: str = None,
    message: str = None,
    metadata: dict = None
):
    """Log user activity to database"""
    try:
        db = get_db()
        
        activity = {
            "user_id": user_id,
            "activity_type": activity_type,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "message": message or f"{action} {resource_type}",
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        
        db.activities.insert_one(activity)
        logger.debug(f"📝 Activity logged: {activity_type}/{action}")
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to log activity: {e}")

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    message_id: str

class UpdateConversationRequest(BaseModel):
    title: str

# ============================================================================
# GET ALL CONVERSATIONS (LIST)
# ============================================================================

@router.get("/conversations")
async def get_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get all conversations for current user"""
    try:
        user_id = current_user.get("user_id")
        db = get_db()
        
        logger.info(f"📥 Fetching conversations for user: {user_id}")
        
        # Calculate skip
        skip = (page - 1) * page_size
        
        # Get conversations
        conversations = list(
            db.conversations
            .find({"user_id": user_id})
            .sort("updated_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        
        # Convert ObjectId to string and format response
        formatted_conversations = []
        for conv in conversations:
            formatted_conversations.append({
                "conversation_id": conv.get("conversation_id"),
                "title": conv.get("title", "New Chat"),
                "created_at": conv.get("created_at"),
                "updated_at": conv.get("updated_at"),
                "message_count": conv.get("message_count", 0),
            })
        
        # Get total count
        total = db.conversations.count_documents({"user_id": user_id})
        
        logger.info(f"✅ Fetched {len(formatted_conversations)} conversations (total: {total})")
        
        # Log activity
        log_activity(
            user_id=user_id,
            activity_type="chat",
            action="viewed",
            resource_type="conversations",
            message="Viewed conversation list"
        )
        
        return {
            "success": True,
            "conversations": formatted_conversations,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching conversations: {e}", exc_info=True)
        # Return empty instead of error
        return {
            "success": True,
            "conversations": [],
            "total": 0,
            "page": page,
            "page_size": page_size
        }

# ============================================================================
# GET SINGLE CONVERSATION BY ID
# ============================================================================

@router.get("/conversations/{conversation_id}")
async def get_conversation_by_id(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific conversation with messages"""
    try:
        user_id = current_user.get("user_id")
        db = get_db()
        
        logger.info(f"📥 Fetching conversation: {conversation_id}")
        
        # Get conversation
        conversation = db.conversations.find_one({
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        
        if not conversation:
            logger.warning(f"⚠️ Conversation not found: {conversation_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Get messages
        messages = list(
            db.messages
            .find({"conversation_id": conversation_id})
            .sort("timestamp", 1)
        )
        
        # Format messages
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "message_id": msg.get("message_id"),
                "role": msg.get("role"),
                "content": msg.get("content"),
                "timestamp": msg.get("timestamp"),
            })
        
        # Format conversation
        formatted_conversation = {
            "conversation_id": conversation.get("conversation_id"),
            "title": conversation.get("title", "New Chat"),
            "created_at": conversation.get("created_at"),
            "updated_at": conversation.get("updated_at"),
            "message_count": conversation.get("message_count", 0),
        }
        
        logger.info(f"✅ Fetched conversation with {len(formatted_messages)} messages")
        
        # Log activity
        log_activity(
            user_id=user_id,
            activity_type="chat",
            action="viewed",
            resource_type="conversation",
            resource_id=conversation_id,
            message=f"Viewed conversation: {conversation.get('title', 'Untitled')}"
        )
        
        return {
            "success": True,
            "conversation": formatted_conversation,
            "messages": formatted_messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch conversation"
        )

# ============================================================================
# DELETE CONVERSATION
# ============================================================================

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a conversation and its messages"""
    try:
        user_id = current_user.get("user_id")
        db = get_db()
        
        logger.info(f"🗑️ Deleting conversation: {conversation_id}")
        
        # Get conversation title before deleting
        conversation = db.conversations.find_one({
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        conversation_title = conversation.get("title", "Untitled")
        
        # Delete conversation
        result = db.conversations.delete_one({
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        
        # Delete all messages
        messages_result = db.messages.delete_many({"conversation_id": conversation_id})
        
        logger.info(f"✅ Deleted conversation and {messages_result.deleted_count} messages")
        
        # Log activity
        log_activity(
            user_id=user_id,
            activity_type="chat",
            action="deleted",
            resource_type="conversation",
            resource_id=conversation_id,
            message=f"Deleted conversation: {conversation_title}",
            metadata={"messages_deleted": messages_result.deleted_count}
        )
        
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

# ============================================================================
# CLEAR CONVERSATION HISTORY (DELETE MESSAGES)
# ============================================================================

@router.delete("/conversations/{conversation_id}/messages")
async def clear_conversation_history(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Clear all messages in a conversation"""
    try:
        user_id = current_user.get("user_id")
        db = get_db()
        
        logger.info(f"🗑️ Clearing messages for conversation: {conversation_id}")
        
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
        
        # Delete all messages
        result = db.messages.delete_many({"conversation_id": conversation_id})
        
        # Update conversation
        db.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {
                    "message_count": 0,
                    "updated_at": time.time()
                }
            }
        )
        
        logger.info(f"✅ Cleared {result.deleted_count} messages")
        
        # Log activity
        log_activity(
            user_id=user_id,
            activity_type="chat",
            action="cleared",
            resource_type="conversation",
            resource_id=conversation_id,
            message=f"Cleared conversation history",
            metadata={"messages_deleted": result.deleted_count}
        )
        
        return {
            "success": True,
            "message": f"Cleared {result.deleted_count} messages"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error clearing history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear history"
        )

# ============================================================================
# SEND CHAT MESSAGE (MAIN CHAT ENDPOINT)
# ============================================================================


@router.post("/", response_model=ChatResponse)
async def chat(
    chat_request: ChatMessage,
    current_user: dict = Depends(get_current_user)
):
    """Send a chat message and get AI response"""
    try:
        user_id = current_user.get("user_id")
        message = chat_request.message
        conversation_id = chat_request.conversation_id
        
        logger.info(f"💬 Processing chat message for user: {user_id}")
        
        db = get_db()
        
        # Get or create conversation
        if conversation_id:
            conversation = db.conversations.find_one({
                "conversation_id": conversation_id,
                "user_id": user_id
            })
            
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
            
            logger.info(f"📂 Using existing conversation: {conversation_id}")
        else:
            # Create new conversation
            conversation_id = str(uuid.uuid4())
            conversation_doc = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "title": message[:50] + "..." if len(message) > 50 else message,
                "created_at": time.time(),
                "updated_at": time.time(),
                "message_count": 0,
                "context_type": None,  # document, video, youtube
                "context_id": None,    # document_id or video_id
            }
            
            db.conversations.insert_one(conversation_doc)
            logger.info(f"✅ New conversation created: {conversation_id}")
            
            # Log activity
            log_activity(
                user_id=user_id,
                activity_type="chat",
                action="created",
                resource_type="conversation",
                resource_id=conversation_id,
                message=f"Created new conversation",
                metadata={"title": conversation_doc["title"]}
            )
        
        # Get conversation history
        history_messages = list(
            db.messages
            .find({"conversation_id": conversation_id})
            .sort("timestamp", 1)
            .limit(20)
        )
        
        # Format history for AI
        history = []
        for msg in history_messages:
            history.append({
                "role": msg.get("role"),
                "content": msg.get("content")
            })
        
        # ✅ NEW: Check for context (document or video)
        context = None
        context_type = None
        conversation = db.conversations.find_one({"conversation_id": conversation_id})
        
        if conversation:
            context_type = conversation.get("context_type")
            context_id = conversation.get("context_id")
            
            if context_type == "document" and context_id:
                # Get document content
                document = db.documents.find_one({"document_id": context_id})
                if document:
                    context = document.get("content", "")
                    logger.info(f"📄 Using document context ({len(context)} chars)")
            
            elif context_type in ["video", "youtube"] and context_id:
                # Get video transcript
                video = db.videos.find_one({"video_id": context_id})
                if video:
                    context = video.get("transcript", "")
                    logger.info(f"🎥 Using video context ({len(context)} chars)")
        
        logger.info(f"🤖 Generating AI response (history: {len(history)} messages)")
        
        # Generate AI response WITH CONTEXT
        ai_response = await ai_service.generate_response(
            message=message,
            history=history,
            context=context,
            context_type=context_type
        )
        
        logger.info(f"✅ AI response generated ({len(ai_response)} chars)")
        
        # Save user message
        user_message_id = str(uuid.uuid4())
        user_message_doc = {
            "message_id": user_message_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": "user",
            "content": message,
            "timestamp": time.time()
        }
        
        db.messages.insert_one(user_message_doc)
        
        # Save AI response
        ai_message_id = str(uuid.uuid4())
        ai_message_doc = {
            "message_id": ai_message_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": "assistant",
            "content": ai_response,
            "timestamp": time.time()
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
        
        # Log activity
        log_activity(
            user_id=user_id,
            activity_type="chat",
            action="sent_message",
            resource_type="conversation",
            resource_id=conversation_id,
            message="Sent chat message",
            metadata={"message_preview": message[:50]}
        )
        
        return ChatResponse(
            response=ai_response,
            conversation_id=conversation_id,
            message_id=ai_message_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )

# ============================================================================
# UPDATE CONVERSATION TITLE
# ============================================================================

@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update conversation title"""
    try:
        user_id = current_user.get("user_id")
        title = request.title
        db = get_db()
        
        logger.info(f"✏️ Updating conversation title: {conversation_id}")
        
        result = db.conversations.update_one(
            {
                "conversation_id": conversation_id,
                "user_id": user_id
            },
            {
                "$set": {
                    "title": title,
                    "updated_at": time.time()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        logger.info(f"✅ Conversation title updated")
        
        # Log activity
        log_activity(
            user_id=user_id,
            activity_type="chat",
            action="updated",
            resource_type="conversation",
            resource_id=conversation_id,
            message=f"Updated conversation title",
            metadata={"new_title": title}
        )
        
        return {
            "success": True,
            "message": "Conversation updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation"
        )

__all__ = ["router"]
