# models/user_chats.py - FASTAPI ASYNC VERSION
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from database.session import get_db, Collections
from config.logging_config import logger


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ChatSummary(BaseModel):
    """Summary of a single chat"""
    chatId: str
    title: str
    createdAt: datetime
    lastMessageAt: Optional[datetime] = None
    messageCount: Optional[int] = 0


class UserChatsModel(BaseModel):
    """User chats document model"""
    userId: str = Field(..., description="User ID")
    chats: List[ChatSummary] = Field(default_factory=list)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "userId": "user_123",
                "chats": [
                    {
                        "chatId": "chat_456",
                        "title": "New Chat",
                        "createdAt": "2025-12-25T17:00:00Z",
                        "lastMessageAt": "2025-12-25T17:05:00Z",
                        "messageCount": 5
                    }
                ],
                "updatedAt": "2025-12-25T17:05:00Z"
            }
        }


class AddChatRequest(BaseModel):
    """Request model for adding a chat"""
    chatId: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)


class UpdateChatRequest(BaseModel):
    """Request model for updating chat metadata"""
    title: Optional[str] = Field(None, max_length=200)
    lastMessageAt: Optional[datetime] = None
    messageCount: Optional[int] = None


# ============================================================================
# USER CHATS DATABASE OPERATIONS (Async)
# ============================================================================

async def add_user_chat(
    user_id: str,
    chat_id: str,
    title: str,
    message_count: int = 0
) -> bool:
    """
    Add chat to user's chat list
    
    Args:
        user_id: User ID
        chat_id: Chat ID
        title: Chat title
        message_count: Initial message count
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        # Check if chat already exists
        existing = await db[Collections.USER_CHATS].find_one({
            'userId': user_id,
            'chats.chatId': chat_id
        })
        
        if existing:
            logger.warning(f"⚠️  Chat {chat_id} already exists for user {user_id}")
            return False
        
        # Add chat to user's list
        result = await db[Collections.USER_CHATS].update_one(
            {'userId': user_id},
            {
                '$push': {
                    'chats': {
                        'chatId': chat_id,
                        'title': title,
                        'createdAt': datetime.utcnow(),
                        'lastMessageAt': datetime.utcnow(),
                        'messageCount': message_count
                    }
                },
                '$set': {
                    'updatedAt': datetime.utcnow()
                }
            },
            upsert=True
        )
        
        logger.info(f"✅ Added chat {chat_id} to user {user_id}'s list")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to add chat to user list: {e}")
        raise


async def get_user_chats(
    user_id: str,
    sort_by: str = "createdAt",
    ascending: bool = False
) -> List[Dict[str, Any]]:
    """
    Get all chats for a user
    
    Args:
        user_id: User ID
        sort_by: Field to sort by (createdAt/lastMessageAt/title)
        ascending: Sort order
    
    Returns:
        List of chat summaries
    """
    try:
        db = await get_db()
        
        user_doc = await db[Collections.USER_CHATS].find_one(
            {'userId': user_id},
            {'_id': 0}
        )
        
        if user_doc and 'chats' in user_doc:
            chats = user_doc['chats']
            
            # Sort chats
            reverse = not ascending
            if sort_by == "createdAt":
                chats.sort(key=lambda x: x.get('createdAt', datetime.min), reverse=reverse)
            elif sort_by == "lastMessageAt":
                chats.sort(key=lambda x: x.get('lastMessageAt', datetime.min), reverse=reverse)
            elif sort_by == "title":
                chats.sort(key=lambda x: x.get('title', '').lower(), reverse=reverse)
            
            logger.info(f"📋 Retrieved {len(chats)} chats for user {user_id}")
            return chats
        
        return []
        
    except Exception as e:
        logger.error(f"❌ Failed to get chats for user {user_id}: {e}")
        return []


async def get_user_chat(
    user_id: str,
    chat_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get a specific chat from user's list
    
    Args:
        user_id: User ID
        chat_id: Chat ID
    
    Returns:
        Chat summary or None
    """
    try:
        db = await get_db()
        
        user_doc = await db[Collections.USER_CHATS].find_one(
            {'userId': user_id},
            {'_id': 0, 'chats': 1}
        )
        
        if user_doc and 'chats' in user_doc:
            for chat in user_doc['chats']:
                if chat.get('chatId') == chat_id:
                    return chat
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to get chat {chat_id} for user {user_id}: {e}")
        return None


async def update_user_chat(
    user_id: str,
    chat_id: str,
    title: Optional[str] = None,
    last_message_at: Optional[datetime] = None,
    increment_message_count: bool = False
) -> bool:
    """
    Update chat metadata in user's list
    
    Args:
        user_id: User ID
        chat_id: Chat ID
        title: New title (optional)
        last_message_at: Last message timestamp (optional)
        increment_message_count: Whether to increment message count
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        update_fields = {}
        
        if title:
            update_fields['chats.$.title'] = title
        
        if last_message_at:
            update_fields['chats.$.lastMessageAt'] = last_message_at
        
        update_fields['updatedAt'] = datetime.utcnow()
        
        update_doc = {'$set': update_fields}
        
        # Increment message count if requested
        if increment_message_count:
            update_doc['$inc'] = {'chats.$.messageCount': 1}
        
        result = await db[Collections.USER_CHATS].update_one(
            {
                'userId': user_id,
                'chats.chatId': chat_id
            },
            update_doc
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Updated chat {chat_id} for user {user_id}")
            return True
        
        logger.warning(f"⚠️  Chat {chat_id} not found for user {user_id}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to update chat {chat_id}: {e}")
        raise


async def remove_user_chat(
    user_id: str,
    chat_id: str
) -> bool:
    """
    Remove chat from user's list
    
    Args:
        user_id: User ID
        chat_id: Chat ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.USER_CHATS].update_one(
            {'userId': user_id},
            {
                '$pull': {'chats': {'chatId': chat_id}},
                '$set': {'updatedAt': datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"🗑️  Removed chat {chat_id} from user {user_id}'s list")
            return True
        
        logger.warning(f"⚠️  Chat {chat_id} not found for user {user_id}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to remove chat {chat_id}: {e}")
        raise


async def delete_all_user_chats(user_id: str) -> bool:
    """
    Delete all chats for a user
    
    Args:
        user_id: User ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.USER_CHATS].delete_one({
            'userId': user_id
        })
        
        if result.deleted_count > 0:
            logger.info(f"🗑️  Deleted all chats for user {user_id}")
            return True
        
        logger.warning(f"⚠️  No chats found for user {user_id}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to delete all chats for user {user_id}: {e}")
        raise


async def clear_user_chats(user_id: str) -> bool:
    """
    Clear all chats from user's list (keep document, empty array)
    
    Args:
        user_id: User ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.USER_CHATS].update_one(
            {'userId': user_id},
            {
                '$set': {
                    'chats': [],
                    'updatedAt': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"🧹 Cleared all chats for user {user_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to clear chats for user {user_id}: {e}")
        raise


async def get_user_chat_count(user_id: str) -> int:
    """
    Get total number of chats for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Number of chats
    """
    try:
        db = await get_db()
        
        user_doc = await db[Collections.USER_CHATS].find_one(
            {'userId': user_id},
            {'chats': 1, '_id': 0}
        )
        
        if user_doc and 'chats' in user_doc:
            return len(user_doc['chats'])
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Failed to get chat count for user {user_id}: {e}")
        return 0


async def search_user_chats(
    user_id: str,
    query: str
) -> List[Dict[str, Any]]:
    """
    Search user's chats by title
    
    Args:
        user_id: User ID
        query: Search query
    
    Returns:
        List of matching chats
    """
    try:
        chats = await get_user_chats(user_id)
        
        # Filter chats by title
        matching_chats = [
            chat for chat in chats
            if query.lower() in chat.get('title', '').lower()
        ]
        
        logger.info(f"🔍 Found {len(matching_chats)} chats matching '{query}'")
        return matching_chats
        
    except Exception as e:
        logger.error(f"❌ Failed to search chats for user {user_id}: {e}")
        return []


async def get_recent_chats(
    user_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get most recently active chats
    
    Args:
        user_id: User ID
        limit: Number of chats to return
    
    Returns:
        List of recent chats
    """
    try:
        chats = await get_user_chats(user_id, sort_by="lastMessageAt", ascending=False)
        return chats[:limit]
        
    except Exception as e:
        logger.error(f"❌ Failed to get recent chats for user {user_id}: {e}")
        return []


async def bulk_update_chat_timestamps(
    user_id: str,
    chat_updates: List[Dict[str, Any]]
) -> int:
    """
    Bulk update chat timestamps
    
    Args:
        user_id: User ID
        chat_updates: List of dicts with chatId and lastMessageAt
    
    Returns:
        Number of chats updated
    
    Example:
        await bulk_update_chat_timestamps(
            "user_123",
            [
                {"chatId": "chat_1", "lastMessageAt": datetime.utcnow()},
                {"chatId": "chat_2", "lastMessageAt": datetime.utcnow()}
            ]
        )
    """
    try:
        db = await get_db()
        
        updated_count = 0
        
        for update in chat_updates:
            chat_id = update.get('chatId')
            last_message_at = update.get('lastMessageAt')
            
            if chat_id and last_message_at:
                result = await db[Collections.USER_CHATS].update_one(
                    {
                        'userId': user_id,
                        'chats.chatId': chat_id
                    },
                    {
                        '$set': {
                            'chats.$.lastMessageAt': last_message_at,
                            'updatedAt': datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    updated_count += 1
        
        logger.info(f"✅ Bulk updated {updated_count} chat timestamps")
        return updated_count
        
    except Exception as e:
        logger.error(f"❌ Failed to bulk update chat timestamps: {e}")
        raise
