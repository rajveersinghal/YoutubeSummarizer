# services/history_service.py - HISTORY & ACTIVITY TRACKING SERVICE

from typing import List, Dict, Optional
import time
from datetime import datetime, timedelta
from config.logging_config import logger
from database.database import get_db


class HistoryService:
    """Service for tracking user activities and history"""
    
    def __init__(self):
        """Initialize history service"""
        self.db = get_db()
    
    async def log_activity(
        self,
        user_id: str,
        activity_type: str,
        action: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        metadata: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict:
        """
        Log user activity
        
        Args:
            user_id: User ID
            activity_type: Type of activity (chat, document, search, etc.)
            action: Action performed (view, create, update, delete, etc.)
            resource_id: ID of resource affected
            resource_type: Type of resource
            metadata: Additional metadata
            ip_address: User's IP address
            user_agent: User agent string
        
        Returns:
            Activity record
        """
        try:
            import uuid
            
            activity_id = str(uuid.uuid4())
            timestamp = time.time()
            
            activity = {
                "activity_id": activity_id,
                "user_id": user_id,
                "activity_type": activity_type,
                "action": action,
                "resource_id": resource_id,
                "resource_type": resource_type,
                "metadata": metadata or {},
                "timestamp": timestamp,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
            
            await self.db.activities.insert_one(activity)
            
            logger.debug(f"Activity logged: {activity_type}/{action}")
            return activity
        
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            raise
    
    async def get_user_activities(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        activity_type: Optional[str] = None,
        start_date: Optional[float] = None,
        end_date: Optional[float] = None
    ) -> List[Dict]:
        """
        Get user activities
        
        Args:
            user_id: User ID
            limit: Number to return
            offset: Pagination offset
            activity_type: Filter by type
            start_date: Filter by start timestamp
            end_date: Filter by end timestamp
        
        Returns:
            List of activities
        """
        try:
            query = {"user_id": user_id}
            
            if activity_type:
                query["activity_type"] = activity_type
            
            if start_date or end_date:
                query["timestamp"] = {}
                if start_date:
                    query["timestamp"]["$gte"] = start_date
                if end_date:
                    query["timestamp"]["$lte"] = end_date
            
            activities = await self.db.activities.find(query).sort(
                "timestamp", -1
            ).skip(offset).limit(limit).to_list(length=limit)
            
            return activities
        
        except Exception as e:
            logger.error(f"Error fetching activities: {e}")
            return []
    
    async def count_user_activities(
        self,
        user_id: str,
        activity_type: Optional[str] = None,
        start_date: Optional[float] = None,
        end_date: Optional[float] = None
    ) -> int:
        """
        Count user activities
        
        Args:
            user_id: User ID
            activity_type: Filter by type
            start_date: Filter by start timestamp
            end_date: Filter by end timestamp
        
        Returns:
            Activity count
        """
        try:
            query = {"user_id": user_id}
            
            if activity_type:
                query["activity_type"] = activity_type
            
            if start_date or end_date:
                query["timestamp"] = {}
                if start_date:
                    query["timestamp"]["$gte"] = start_date
                if end_date:
                    query["timestamp"]["$lte"] = end_date
            
            count = await self.db.activities.count_documents(query)
            return count
        
        except Exception as e:
            logger.error(f"Error counting activities: {e}")
            return 0
    
    async def get_activity(
        self,
        activity_id: str,
        user_id: str
    ) -> Optional[Dict]:
        """
        Get specific activity
        
        Args:
            activity_id: Activity ID
            user_id: User ID
        
        Returns:
            Activity or None
        """
        try:
            activity = await self.db.activities.find_one({
                "activity_id": activity_id,
                "user_id": user_id
            })
            
            return activity
        
        except Exception as e:
            logger.error(f"Error fetching activity: {e}")
            return None
    
    async def delete_user_activities(
        self,
        user_id: str,
        older_than: Optional[float] = None
    ) -> int:
        """
        Delete user activities
        
        Args:
            user_id: User ID
            older_than: Delete only activities older than this timestamp
        
        Returns:
            Number of deleted activities
        """
        try:
            query = {"user_id": user_id}
            
            if older_than:
                query["timestamp"] = {"$lt": older_than}
            
            result = await self.db.activities.delete_many(query)
            
            return result.deleted_count
        
        except Exception as e:
            logger.error(f"Error deleting activities: {e}")
            raise
    
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get user conversations
        
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
            
            # Add preview
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
    
    async def count_user_conversations(self, user_id: str) -> int:
        """
        Count user conversations
        
        Args:
            user_id: User ID
        
        Returns:
            Conversation count
        """
        try:
            count = await self.db.conversations.count_documents({"user_id": user_id})
            return count
        
        except Exception as e:
            logger.error(f"Error counting conversations: {e}")
            return 0
    
    async def get_conversation_details(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[Dict]:
        """
        Get conversation with messages
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
        
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
            
            messages = await self.db.messages.find(
                {"conversation_id": conversation_id}
            ).sort("timestamp", 1).to_list(length=None)
            
            conversation["messages"] = messages
            return conversation
        
        except Exception as e:
            logger.error(f"Error fetching conversation: {e}")
            return None
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ):
        """
        Delete conversation
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
        """
        try:
            await self.db.messages.delete_many({
                "conversation_id": conversation_id,
                "user_id": user_id
            })
            
            await self.db.conversations.delete_one({
                "conversation_id": conversation_id,
                "user_id": user_id
            })
        
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            raise
    
    async def delete_all_conversations(self, user_id: str) -> int:
        """
        Delete all user conversations
        
        Args:
            user_id: User ID
        
        Returns:
            Number of conversations deleted
        """
        try:
            # Delete all messages
            await self.db.messages.delete_many({"user_id": user_id})
            
            # Delete all conversations
            result = await self.db.conversations.delete_many({"user_id": user_id})
            
            return result.deleted_count
        
        except Exception as e:
            logger.error(f"Error deleting conversations: {e}")
            raise
    
    async def get_document_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get document history
        
        Args:
            user_id: User ID
            limit: Number to return
            offset: Pagination offset
        
        Returns:
            Document activities
        """
        try:
            activities = await self.db.activities.find({
                "user_id": user_id,
                "activity_type": "document"
            }).sort("timestamp", -1).skip(offset).limit(limit).to_list(length=limit)
            
            return activities
        
        except Exception as e:
            logger.error(f"Error fetching document history: {e}")
            return []
    
    async def get_user_stats(self, user_id: str) -> Dict:
        """
        Get user statistics
        
        Args:
            user_id: User ID
        
        Returns:
            Statistics dictionary
        """
        try:
            now = time.time()
            today_start = now - (now % 86400)
            week_start = now - (7 * 86400)
            month_start = now - (30 * 86400)
            
            # Count various entities
            total_chats = await self.db.conversations.count_documents({"user_id": user_id})
            total_documents = await self.db.documents.count_documents({"user_id": user_id})
            total_activities = await self.db.activities.count_documents({"user_id": user_id})
            
            activities_today = await self.db.activities.count_documents({
                "user_id": user_id,
                "timestamp": {"$gte": today_start}
            })
            
            activities_this_week = await self.db.activities.count_documents({
                "user_id": user_id,
                "timestamp": {"$gte": week_start}
            })
            
            activities_this_month = await self.db.activities.count_documents({
                "user_id": user_id,
                "timestamp": {"$gte": month_start}
            })
            
            return {
                "total_chats": total_chats,
                "total_documents": total_documents,
                "total_activities": total_activities,
                "activities_today": activities_today,
                "activities_this_week": activities_this_week,
                "activities_this_month": activities_this_month,
                "most_active_day": None,  # TODO: Implement
                "most_used_feature": None  # TODO: Implement
            }
        
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            return {}
    
    async def get_activity_timeline(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Get activity timeline
        
        Args:
            user_id: User ID
            days: Number of days
        
        Returns:
            Timeline data
        """
        try:
            # TODO: Implement proper timeline aggregation
            # For now, return empty list
            return []
        
        except Exception as e:
            logger.error(f"Error fetching timeline: {e}")
            return []
    
    async def get_search_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get search history
        
        Args:
            user_id: User ID
            limit: Number to return
        
        Returns:
            Search history
        """
        try:
            searches = await self.db.activities.find({
                "user_id": user_id,
                "activity_type": "search"
            }).sort("timestamp", -1).limit(limit).to_list(length=limit)
            
            return searches
        
        except Exception as e:
            logger.error(f"Error fetching search history: {e}")
            return []
    
    async def clear_search_history(self, user_id: str) -> int:
        """
        Clear search history
        
        Args:
            user_id: User ID
        
        Returns:
            Number of searches deleted
        """
        try:
            result = await self.db.activities.delete_many({
                "user_id": user_id,
                "activity_type": "search"
            })
            
            return result.deleted_count
        
        except Exception as e:
            logger.error(f"Error clearing search history: {e}")
            raise
