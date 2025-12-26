# routes/chat.py - FASTAPI CHAT ROUTES
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime

from models.chat import (
    create_chat,
    get_chat_by_id,
    get_user_chats,
    update_chat_title,
    delete_chat,
    get_chat_count,
    search_chats,
    ChatModel,
    CreateChatRequest,
    UpdateChatRequest
)
from models.message import (
    add_message,
    get_messages_by_chat,
    delete_messages_by_chat,
    get_message_count,
    MessageModel,
    CreateMessageRequest
)
from models.user_chats import (
    add_user_chat,
    get_user_chats as get_user_chat_list,
    remove_user_chat,
    update_user_chat
)
from models.query import save_query
from services.rag_service import answer_question_async, get_gemini_model
from core.auth import get_current_user
from core.responses import (
    success_response,
    created_response,
    not_found_response,
    no_content_response,
    error_response
)
from config.logging_config import logger

import google.generativeai as genai


router = APIRouter(prefix="/api/chats", tags=["chats"])


# ============================================================================
# CHAT MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("", status_code=201)
async def create_new_chat(
    data: CreateChatRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Create a new chat
    
    - **title**: Chat title
    - **mode**: Chat mode (chat/rag/youtube/document)
    """
    try:
        chat_id = await create_chat(
            user_id=user_id,
            title=data.title,
            mode=data.mode
        )
        
        # Add to user's chat list
        await add_user_chat(user_id, chat_id, data.title)
        
        return created_response(
            data={"chatId": chat_id, "title": data.title},
            message="Chat created successfully",
            resource_id=chat_id
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to create chat: {e}")
        return error_response(str(e), 500)


@router.get("")
async def get_chats(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    mode: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """
    Get all chats for user
    
    - **limit**: Maximum number of chats to return
    - **skip**: Number of chats to skip (pagination)
    - **mode**: Filter by chat mode
    """
    try:
        chats = await get_user_chats(user_id, limit, skip, mode)
        total = await get_chat_count(user_id)
        
        return success_response(
            data={"chats": chats, "total": total, "count": len(chats)},
            message=f"Retrieved {len(chats)} chats"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get chats: {e}")
        return error_response(str(e), 500)


@router.get("/search")
async def search_user_chats(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user)
):
    """
    Search chats by title
    
    - **q**: Search query
    - **limit**: Maximum results
    """
    try:
        chats = await search_chats(user_id, q, limit)
        
        return success_response(
            data={"chats": chats, "count": len(chats)},
            message=f"Found {len(chats)} matching chats"
        )
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        return error_response(str(e), 500)


@router.get("/{chat_id}")
async def get_chat(
    chat_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Get specific chat by ID
    
    - **chat_id**: Chat ID
    """
    try:
        chat = await get_chat_by_id(user_id, chat_id)
        
        if not chat:
            return not_found_response("Chat", chat_id)
        
        return success_response(
            data=chat,
            message="Chat retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get chat: {e}")
        return error_response(str(e), 500)


@router.patch("/{chat_id}")
async def update_chat(
    chat_id: str,
    data: UpdateChatRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Update chat details
    
    - **chat_id**: Chat ID
    - **title**: New chat title
    """
    try:
        success = await update_chat_title(user_id, chat_id, data.title)
        
        if not success:
            return not_found_response("Chat", chat_id)
        
        # Update in user's chat list
        await update_user_chat(
            user_id,
            chat_id,
            title=data.title,
            last_message_at=datetime.utcnow()
        )
        
        return success_response(message="Chat updated successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to update chat: {e}")
        return error_response(str(e), 500)


@router.delete("/{chat_id}", status_code=204)
async def remove_chat(
    chat_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Delete a chat
    
    - **chat_id**: Chat ID
    """
    try:
        # Delete chat
        deleted = await delete_chat(user_id, chat_id)
        
        if not deleted:
            return not_found_response("Chat", chat_id)
        
        # Remove from user's chat list
        await remove_user_chat(user_id, chat_id)
        
        # Delete associated messages
        await delete_messages_by_chat(user_id, chat_id)
        
        return no_content_response()
        
    except Exception as e:
        logger.error(f"❌ Failed to delete chat: {e}")
        return error_response(str(e), 500)


# ============================================================================
# CHAT MESSAGES ENDPOINTS
# ============================================================================

@router.get("/{chat_id}/messages")
async def get_chat_messages(
    chat_id: str,
    limit: int = Query(100, ge=1, le=200),
    user_id: str = Depends(get_current_user)
):
    """
    Get messages for a chat
    
    - **chat_id**: Chat ID
    - **limit**: Maximum messages to return
    """
    try:
        # Verify chat exists
        chat = await get_chat_by_id(user_id, chat_id)
        if not chat:
            return not_found_response("Chat", chat_id)
        
        messages = await get_messages_by_chat(user_id, chat_id, limit)
        total = await get_message_count(chat_id)
        
        return success_response(
            data={"messages": messages, "total": total, "count": len(messages)},
            message=f"Retrieved {len(messages)} messages"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get messages: {e}")
        return error_response(str(e), 500)


@router.post("/{chat_id}/messages", status_code=201)
async def send_message(
    chat_id: str,
    data: CreateMessageRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Send a message in chat
    
    - **chat_id**: Chat ID
    - **content**: Message content
    - **role**: Message role (user/assistant/system)
    """
    try:
        # Verify chat exists
        chat = await get_chat_by_id(user_id, chat_id)
        if not chat:
            return not_found_response("Chat", chat_id)
        
        # Add message
        message_id = await add_message(
            user_id=user_id,
            chat_id=chat_id,
            role=data.role,
            content=data.content
        )
        
        # Update user's chat list
        await update_user_chat(
            user_id,
            chat_id,
            last_message_at=datetime.utcnow(),
            increment_message_count=True
        )
        
        return created_response(
            data={"messageId": message_id, "chatId": chat_id},
            message="Message sent successfully",
            resource_id=message_id
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to send message: {e}")
        return error_response(str(e), 500)


# ============================================================================
# CHAT AI ENDPOINTS
# ============================================================================

@router.post("/{chat_id}/ask")
async def ask_question(
    chat_id: str,
    question: str,
    video_id: Optional[str] = None,
    document_id: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """
    Ask a question in chat (with optional RAG)
    
    - **chat_id**: Chat ID
    - **question**: User question
    - **video_id**: Optional video ID for RAG
    - **document_id**: Optional document ID for RAG
    """
    try:
        start_time = datetime.utcnow()
        
        # Verify chat exists
        chat = await get_chat_by_id(user_id, chat_id)
        if not chat:
            return not_found_response("Chat", chat_id)
        
        # Add user message
        await add_message(user_id, chat_id, "user", question)
        
        # Determine mode and generate response
        mode = chat.get('mode', 'chat')
        
        if video_id and mode == 'rag':
            # RAG mode with video
            result = await answer_question_async(video_id, question)
            answer = result['answer']
            context = result.get('sources', [])
        
        elif document_id and mode == 'rag':
            # RAG mode with document
            # TODO: Implement document RAG
            answer = "Document RAG not implemented yet"
            context = []
        
        else:
            # Regular chat mode with Gemini
            model = get_gemini_model()
            
            # Get conversation history
            messages = await get_messages_by_chat(user_id, chat_id, limit=10)
            
            # Build prompt with history
            conversation = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in reversed(messages[:-1])  # Exclude current question
            ])
            
            prompt = f"""You are a helpful AI assistant. Continue this conversation naturally.

Conversation history:
{conversation}

USER: {question}

ASSISTANT:"""
            
            response = model.generate_content(prompt)
            answer = response.text.strip() if hasattr(response, 'text') else "Unable to generate response"
            context = []
        
        # Add assistant message
        await add_message(user_id, chat_id, "assistant", answer)
        
        # Update chat
        await update_user_chat(
            user_id,
            chat_id,
            last_message_at=datetime.utcnow(),
            increment_message_count=True
        )
        
        # Calculate response time
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds()
        
        # Save query
        await save_query(
            user_id=user_id,
            question=question,
            answer=answer,
            chat_id=chat_id,
            video_id=video_id,
            document_id=document_id,
            context=[c.get('text', '') for c in context] if context else [],
            mode=mode,
            response_time=response_time
        )
        
        return success_response(
            data={
                "question": question,
                "answer": answer,
                "context": context,
                "responseTime": response_time
            },
            message="Question answered successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to answer question: {e}")
        return error_response(str(e), 500)


@router.post("/{chat_id}/clear")
async def clear_chat_messages(
    chat_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Clear all messages in a chat
    
    - **chat_id**: Chat ID
    """
    try:
        # Verify chat exists
        chat = await get_chat_by_id(user_id, chat_id)
        if not chat:
            return not_found_response("Chat", chat_id)
        
        # Delete messages
        count = await delete_messages_by_chat(user_id, chat_id)
        
        return success_response(
            data={"deletedCount": count},
            message=f"Cleared {count} messages"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to clear messages: {e}")
        return error_response(str(e), 500)


# ============================================================================
# CHAT STATISTICS
# ============================================================================

@router.get("/{chat_id}/stats")
async def get_chat_stats(
    chat_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Get chat statistics
    
    - **chat_id**: Chat ID
    """
    try:
        # Verify chat exists
        chat = await get_chat_by_id(user_id, chat_id)
        if not chat:
            return not_found_response("Chat", chat_id)
        
        # Get message count
        message_count = await get_message_count(chat_id)
        
        # Calculate chat age
        created_at = chat.get('createdAt', datetime.utcnow())
        age_days = (datetime.utcnow() - created_at).days
        
        stats = {
            "chatId": chat_id,
            "title": chat.get('title'),
            "mode": chat.get('mode'),
            "messageCount": message_count,
            "createdAt": chat.get('createdAt'),
            "lastMessageAt": chat.get('lastMessageAt'),
            "ageDays": age_days
        }
        
        return success_response(data=stats)
        
    except Exception as e:
        logger.error(f"❌ Failed to get chat stats: {e}")
        return error_response(str(e), 500)
