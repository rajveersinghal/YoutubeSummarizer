# services/chat_service.py - CHAT SERVICE

from typing import List, Dict, Optional
import time
import uuid
from config.logging_config import logger
from database.database import get_db


class ChatService:
    """Service for managing chat conversations and messages"""
    
    def __init__(self):
        """Initialize chat service"""
        self.db = get_db()
    
    async def save_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str
    ) -> Dict:
        """
        Save a chat message
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            role: Message role (user/assistant)
            content: Message content
        
        Returns:
            Saved message
        """
        try:
            message_id = str(uuid.uuid4())
            timestamp = time.time()
            
            message = {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "timestamp": timestamp
            }
            
            # Save to database
            await self.db.messages.insert_one(message)
            
            # Update conversation timestamp
            await self.db.conversations.update_one(
                {"conversation_id": conversation_id, "user_id": user_id},
                {
                    "$set": {"updated_at": timestamp},
                    "$inc": {"message_count": 1},
                    "$setOnInsert": {
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "created_at": timestamp,
                        "title": "New Conversation"
                    }
                },
                upsert=True
            )
            
            logger.debug(f"Message saved: {message_id}")
            return message
        
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise
    
    async def get_conversation_history(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get conversation history
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            limit: Maximum messages to return
        
        Returns:
            List of messages
        """
        try:
            messages = await self.db.messages.find(
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id
                }
            ).sort("timestamp", 1).limit(limit).to_list(length=limit)
            
            return messages
        
        except Exception as e:
            logger.error(f"Error fetching history: {e}")
            return []
    
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get user's conversations
        
        Args:
            user_id: User ID
            limit: Number to return
            offset: Pagination offset
        
        Returns:
            List of conversations
        """
        try:
            conversations = await self.db.conversations.find(
                {"user_id": user_id}
            ).sort("updated_at", -1).skip(offset).limit(limit).to_list(length=limit)
            
            # Get preview of last message for each conversation
            for conv in conversations:
                last_message = await self.db.messages.find_one(
                    {"conversation_id": conv["conversation_id"]},
                    sort=[("timestamp", -1)]
                )
                
                conv["preview"] = last_message["content"][:100] if last_message else ""
                conv["last_message_at"] = last_message["timestamp"] if last_message else conv["updated_at"]
            
            return conversations
        
        except Exception as e:
            logger.error(f"Error fetching conversations: {e}")
            return []
    
    async def get_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> Optional[Dict]:
        """
        Get conversation with all messages
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
        
        Returns:
            Conversation with messages
        """
        try:
            conversation = await self.db.conversations.find_one({
                "conversation_id": conversation_id,
                "user_id": user_id
            })
            
            if not conversation:
                return None
            
            messages = await self.get_conversation_history(user_id, conversation_id)
            
            conversation["messages"] = messages
            return conversation
        
        except Exception as e:
            logger.error(f"Error fetching conversation: {e}")
            return None
    
    async def delete_conversation(
        self,
        user_id: str,
        conversation_id: str
    ):
        """
        Delete a conversation
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
        """
        try:
            # Delete all messages
            await self.db.messages.delete_many({
                "user_id": user_id,
                "conversation_id": conversation_id
            })
            
            # Delete conversation
            await self.db.conversations.delete_one({
                "conversation_id": conversation_id,
                "user_id": user_id
            })
            
            logger.info(f"Conversation deleted: {conversation_id}")
        
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            raise
    
    async def update_conversation_title(
        self,
        user_id: str,
        conversation_id: str,
        title: str
    ):
        """
        Update conversation title
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            title: New title
        """
        try:
            await self.db.conversations.update_one(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id
                },
                {"$set": {"title": title}}
            )
        
        except Exception as e:
            logger.error(f"Error updating conversation title: {e}")
            raise
