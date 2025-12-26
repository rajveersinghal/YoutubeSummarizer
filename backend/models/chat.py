# models/chat.py - CHAT MODELS (FASTAPI ASYNC VERSION)

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
import uuid
import time

from db.database import get_db
from config.logging_config import logger


# ============================================================================
# PYDANTIC MODELS (Request/Response Schemas)
# ============================================================================

class MessageModel(BaseModel):
    """Single message in chat history"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: float = Field(default_factory=time.time)
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is either user or assistant"""
        if v not in ['user', 'assistant', 'system']:
            raise ValueError("Role must be 'user', 'assistant', or 'system'")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "Hello, how are you?",
                "timestamp": 1703001600.0
            }
        }


class ChatModel(BaseModel):
    """Chat document model"""
    chat_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User ID who owns this chat")
    title: str = Field(default="New Chat", max_length=200)
    history: List[MessageModel] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    is_deleted: bool = Field(default=False)
    message_count: int = Field(default=0, ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "chat_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "user_123",
                "title": "New Chat",
                "history": [
                    {
                        "role": "user",
                        "content": "Hello",
                        "timestamp": 1703001600.0
                    },
                    {
                        "role": "assistant",
                        "content": "Hi! How can I help?",
                        "timestamp": 1703001601.0
                    }
                ],
                "created_at": 1703001600.0,
                "updated_at": 1703001601.0,
                "is_deleted": False,
                "message_count": 2
            }
        }


class CreateChatRequest(BaseModel):
    """Request model for creating a chat"""
    text: Optional[str] = Field(None, description="Initial message (optional)")
    title: Optional[str] = Field("New Chat", max_length=200)


class AddMessageRequest(BaseModel):
    """Request model for adding message to chat"""
    question: str = Field(..., min_length=1, max_length=5000)
    answer: str = Field(..., min_length=1)


class UpdateChatTitleRequest(BaseModel):
    """Request model for updating chat title"""
    title: str = Field(..., min_length=1, max_length=200)


class ChatResponse(BaseModel):
    """Chat response model"""
    chat_id: str
    user_id: str
    title: str
    message_count: int
    created_at: float
    updated_at: float


class ChatListResponse(BaseModel):
    """Chat list response"""
    chats: List[ChatResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ============================================================================
# CHAT DATABASE OPERATIONS (Async)
# ============================================================================

async def create_chat(
    user_id: str,
    text: Optional[str] = None,
    title: str = "New Chat"
) -> str:
    """
    Create new chat
    
    Args:
        user_id: User ID who owns the chat
        text: Optional initial message
        title: Chat title
    
    Returns:
        chat_id: ID of created chat
    """
    try:
        db = get_db()
        chat_id = str(uuid.uuid4())
        timestamp = time.time()
        
        chat_doc = {
            'chat_id': chat_id,
            'user_id': user_id,
            'title': title,
            'history': [],
            'created_at': timestamp,
            'updated_at': timestamp,
            'is_deleted': False,
            'message_count': 0
        }
        
        # Add initial message if provided
        if text:
            chat_doc['history'].append({
                'role': 'user',
                'content': text,
                'timestamp': timestamp
            })
            chat_doc['message_count'] = 1
        
        await db.chats.insert_one(chat_doc)
        
        logger.info(f"✅ Chat created: {chat_id} for user {user_id}")
        return chat_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create chat: {e}")
        raise


async def get_chat(chat_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get chat by ID
    
    Args:
        chat_id: Chat ID
        user_id: User ID (for authorization)
    
    Returns:
        Chat document or None if not found
    """
    try:
        db = get_db()
        
        chat = await db.chats.find_one({
            'chat_id': chat_id,
            'user_id': user_id,
            'is_deleted': False
        })
        
        if chat:
            # Remove MongoDB _id from response
            chat.pop('_id', None)
        
        return chat
        
    except Exception as e:
        logger.error(f"❌ Failed to get chat {chat_id}: {e}")
        raise


async def get_all_chats(
    user_id: str,
    limit: int = 100,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """
    Get all chats for a user
    
    Args:
        user_id: User ID
        limit: Maximum number of chats to return
        skip: Number of chats to skip (pagination)
    
    Returns:
        List of chat documents
    """
    try:
        db = get_db()
        
        cursor = db.chats.find({
            'user_id': user_id,
            'is_deleted': False
        }).sort('updated_at', -1).skip(skip).limit(limit)
        
        chats = await cursor.to_list(length=limit)
        
        # Remove MongoDB _id from all chats
        for chat in chats:
            chat.pop('_id', None)
        
        return chats
        
    except Exception as e:
        logger.error(f"❌ Failed to get chats for user {user_id}: {e}")
        raise


async def add_to_chat(
    chat_id: str,
    user_id: str,
    question: str,
    answer: str
) -> bool:
    """
    Add user question and AI response to chat
    
    Args:
        chat_id: Chat ID
        user_id: User ID (for authorization)
        question: User's question
        answer: AI's answer
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = get_db()
        timestamp = time.time()
        
        result = await db.chats.update_one(
            {
                'chat_id': chat_id,
                'user_id': user_id,
                'is_deleted': False
            },
            {
                '$push': {
                    'history': {
                        '$each': [
                            {
                                'role': 'user',
                                'content': question,
                                'timestamp': timestamp
                            },
                            {
                                'role': 'assistant',
                                'content': answer,
                                'timestamp': timestamp
                            }
                        ]
                    }
                },
                '$set': {
                    'updated_at': timestamp
                },
                '$inc': {
                    'message_count': 2
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Message added to chat {chat_id}")
            return True
        
        logger.warning(f"⚠️  Chat {chat_id} not found or not modified")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to add message to chat {chat_id}: {e}")
        raise


async def update_chat_title(
    chat_id: str,
    user_id: str,
    title: str
) -> bool:
    """
    Update chat title
    
    Args:
        chat_id: Chat ID
        user_id: User ID (for authorization)
        title: New chat title
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = get_db()
        
        result = await db.chats.update_one(
            {
                'chat_id': chat_id,
                'user_id': user_id,
                'is_deleted': False
            },
            {
                '$set': {
                    'title': title,
                    'updated_at': time.time()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Chat title updated: {chat_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to update chat title {chat_id}: {e}")
        raise


async def delete_chat(chat_id: str, user_id: str) -> bool:
    """
    Soft delete chat (mark as deleted)
    
    Args:
        chat_id: Chat ID
        user_id: User ID (for authorization)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = get_db()
        
        result = await db.chats.update_one(
            {
                'chat_id': chat_id,
                'user_id': user_id,
                'is_deleted': False
            },
            {
                '$set': {
                    'is_deleted': True,
                    'deleted_at': time.time()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Chat deleted: {chat_id}")
            return True
        
        logger.warning(f"⚠️  Chat {chat_id} not found")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to delete chat {chat_id}: {e}")
        raise


async def hard_delete_chat(chat_id: str, user_id: str) -> bool:
    """
    Permanently delete chat from database
    
    Args:
        chat_id: Chat ID
        user_id: User ID (for authorization)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = get_db()
        
        result = await db.chats.delete_one({
            'chat_id': chat_id,
            'user_id': user_id
        })
        
        if result.deleted_count > 0:
            logger.info(f"✅ Chat permanently deleted: {chat_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to hard delete chat {chat_id}: {e}")
        raise


async def get_chat_count(user_id: str) -> int:
    """
    Get total number of chats for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Number of chats
    """
    try:
        db = get_db()
        
        count = await db.chats.count_documents({
            'user_id': user_id,
            'is_deleted': False
        })
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to get chat count for user {user_id}: {e}")
        raise


async def search_chats(
    user_id: str,
    query: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search chats by title or content
    
    Args:
        user_id: User ID
        query: Search query
        limit: Maximum number of results
    
    Returns:
        List of matching chats
    """
    try:
        db = get_db()
        
        cursor = db.chats.find({
            'user_id': user_id,
            'is_deleted': False,
            '$or': [
                {'title': {'$regex': query, '$options': 'i'}},
                {'history.content': {'$regex': query, '$options': 'i'}}
            ]
        }).sort('updated_at', -1).limit(limit)
        
        chats = await cursor.to_list(length=limit)
        
        # Remove MongoDB _id
        for chat in chats:
            chat.pop('_id', None)
        
        return chats
        
    except Exception as e:
        logger.error(f"❌ Failed to search chats: {e}")
        raise


async def clear_chat_history(chat_id: str, user_id: str) -> bool:
    """
    Clear all messages from a chat (keep chat, remove history)
    
    Args:
        chat_id: Chat ID
        user_id: User ID (for authorization)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = get_db()
        
        result = await db.chats.update_one(
            {
                'chat_id': chat_id,
                'user_id': user_id,
                'is_deleted': False
            },
            {
                '$set': {
                    'history': [],
                    'message_count': 0,
                    'updated_at': time.time()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Chat history cleared: {chat_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to clear chat history {chat_id}: {e}")
        raise


# ============================================================================
# EXPORT ALL
# ============================================================================

__all__ = [
    "MessageModel",
    "ChatModel",
    "CreateChatRequest",
    "AddMessageRequest",
    "UpdateChatTitleRequest",
    "ChatResponse",
    "ChatListResponse",
    "create_chat",
    "get_chat",
    "get_all_chats",
    "add_to_chat",
    "update_chat_title",
    "delete_chat",
    "hard_delete_chat",
    "get_chat_count",
    "search_chats",
    "clear_chat_history",
]
