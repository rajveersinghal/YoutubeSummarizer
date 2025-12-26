# models/history.py - FASTAPI ASYNC VERSION
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from database.session import get_db, Collections
from config.logging_config import logger


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class HistoryModel(BaseModel):
    """History document model"""
    historyId: str = Field(..., description="Unique history ID")
    userId: str = Field(..., description="User ID")
    videoId: str = Field(..., description="YouTube video ID")
    title: str = Field(..., max_length=500, description="Video title")
    summary: str = Field(..., description="Generated summary")
    mode: str = Field(..., description="Processing mode (quick/detailed/custom)")
    thumbnail: Optional[str] = Field(None, description="Video thumbnail URL")
    duration: Optional[int] = Field(None, description="Video duration in seconds")
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "historyId": "hist_123",
                "userId": "user_123",
                "videoId": "dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "summary": "This video is about...",
                "mode": "detailed",
                "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
                "duration": 213,
                "createdAt": "2025-12-25T17:00:00Z"
            }
        }


class SaveHistoryRequest(BaseModel):
    """Request model for saving history"""
    videoId: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=500)
    summary: str = Field(..., min_length=1)
    mode: str = Field(default="quick")
    thumbnail: Optional[str] = None
    duration: Optional[int] = None


class HistoryStatsModel(BaseModel):
    """History statistics model"""
    totalVideos: int
    totalSummaries: int
    modeBreakdown: Dict[str, int]
    recentActivity: List[datetime]


# ============================================================================
# HISTORY DATABASE OPERATIONS (Async)
# ============================================================================

async def save_history(
    user_id: str,
    video_id: str,
    title: str,
    summary: str,
    mode: str = "quick",
    thumbnail: Optional[str] = None,
    duration: Optional[int] = None
) -> str:
    """
    Save video processing to history
    
    Args:
        user_id: User ID
        video_id: YouTube video ID
        title: Video title
        summary: Generated summary
        mode: Processing mode (quick/detailed/custom)
        thumbnail: Video thumbnail URL
        duration: Video duration in seconds
    
    Returns:
        history_id: ID of created history record
    """
    try:
        db = await get_db()
        
        # Generate unique history ID
        from uuid import uuid4
        history_id = f"hist_{str(uuid4())[:8]}"
        
        history_doc = {
            'historyId': history_id,
            'userId': user_id,
            'videoId': video_id,
            'title': title,
            'summary': summary,
            'mode': mode,
            'thumbnail': thumbnail,
            'duration': duration,
            'createdAt': datetime.utcnow()
        }
        
        await db[Collections.HISTORY].insert_one(history_doc)
        
        logger.info(f"💾 Saved history record {history_id} for user {user_id}")
        return history_id
        
    except Exception as e:
        logger.error(f"❌ Failed to save history: {e}")
        raise


async def get_all_history(
    user_id: str,
    limit: int = 50,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """
    Get all history for a user
    
    Args:
        user_id: User ID
        limit: Maximum number of records to return
        skip: Number of records to skip (pagination)
    
    Returns:
        List of history documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.HISTORY].find(
            {'userId': user_id},
            {'_id': 0}
        ).sort('createdAt', -1).skip(skip).limit(limit)
        
        history = await cursor.to_list(length=limit)
        
        logger.info(f"📜 Retrieved {len(history)} history records for user {user_id}")
        return history
        
    except Exception as e:
        logger.error(f"❌ Failed to get history for user {user_id}: {e}")
        return []


async def get_history_by_video(
    user_id: str,
    video_id: str
) -> List[Dict[str, Any]]:
    """
    Get history for a specific video
    
    Args:
        user_id: User ID
        video_id: YouTube video ID
    
    Returns:
        List of history documents for the video
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.HISTORY].find(
            {
                'userId': user_id,
                'videoId': video_id
            },
            {'_id': 0}
        ).sort('createdAt', -1)
        
        history = await cursor.to_list(length=None)
        
        logger.info(f"📜 Retrieved {len(history)} history records for video {video_id}")
        return history
        
    except Exception as e:
        logger.error(f"❌ Failed to get history for video {video_id}: {e}")
        return []


async def get_history_by_id(
    user_id: str,
    history_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get a specific history record by ID
    
    Args:
        user_id: User ID (for authorization)
        history_id: History record ID
    
    Returns:
        History document or None
    """
    try:
        db = await get_db()
        
        history = await db[Collections.HISTORY].find_one(
            {
                'historyId': history_id,
                'userId': user_id
            },
            {'_id': 0}
        )
        
        return history
        
    except Exception as e:
        logger.error(f"❌ Failed to get history {history_id}: {e}")
        return None


async def delete_history(
    user_id: str,
    history_id: str
) -> bool:
    """
    Delete a specific history record
    
    Args:
        user_id: User ID (for authorization)
        history_id: History record ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.HISTORY].delete_one({
            'historyId': history_id,
            'userId': user_id
        })
        
        if result.deleted_count > 0:
            logger.info(f"🗑️  Deleted history record {history_id}")
            return True
        
        logger.warning(f"⚠️  History record {history_id} not found")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to delete history {history_id}: {e}")
        raise


async def delete_all_history(user_id: str) -> int:
    """
    Delete all history for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Number of records deleted
    """
    try:
        db = await get_db()
        
        result = await db[Collections.HISTORY].delete_many({
            'userId': user_id
        })
        
        logger.info(f"🗑️  Deleted {result.deleted_count} history records for user {user_id}")
        return result.deleted_count
        
    except Exception as e:
        logger.error(f"❌ Failed to delete all history for user {user_id}: {e}")
        raise


async def get_history_count(user_id: str) -> int:
    """
    Get total number of history records for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Number of history records
    """
    try:
        db = await get_db()
        
        count = await db[Collections.HISTORY].count_documents({
            'userId': user_id
        })
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to get history count for user {user_id}: {e}")
        return 0


async def search_history(
    user_id: str,
    query: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search history by title or summary
    
    Args:
        user_id: User ID
        query: Search query
        limit: Maximum number of results
    
    Returns:
        List of matching history records
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.HISTORY].find(
            {
                'userId': user_id,
                '$or': [
                    {'title': {'$regex': query, '$options': 'i'}},
                    {'summary': {'$regex': query, '$options': 'i'}}
                ]
            },
            {'_id': 0}
        ).sort('createdAt', -1).limit(limit)
        
        history = await cursor.to_list(length=limit)
        
        logger.info(f"🔍 Found {len(history)} history records matching '{query}'")
        return history
        
    except Exception as e:
        logger.error(f"❌ Failed to search history: {e}")
        return []


async def get_history_by_mode(
    user_id: str,
    mode: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get history filtered by processing mode
    
    Args:
        user_id: User ID
        mode: Processing mode (quick/detailed/custom)
        limit: Maximum number of results
    
    Returns:
        List of history records
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.HISTORY].find(
            {
                'userId': user_id,
                'mode': mode
            },
            {'_id': 0}
        ).sort('createdAt', -1).limit(limit)
        
        history = await cursor.to_list(length=limit)
        
        return history
        
    except Exception as e:
        logger.error(f"❌ Failed to get history by mode {mode}: {e}")
        return []


async def get_history_stats(user_id: str) -> Dict[str, Any]:
    """
    Get history statistics for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Dictionary with statistics
    """
    try:
        db = await get_db()
        
        # Total count
        total = await db[Collections.HISTORY].count_documents({
            'userId': user_id
        })
        
        # Unique videos
        unique_videos = len(await db[Collections.HISTORY].distinct(
            'videoId',
            {'userId': user_id}
        ))
        
        # Mode breakdown
        pipeline = [
            {'$match': {'userId': user_id}},
            {
                '$group': {
                    '_id': '$mode',
                    'count': {'$sum': 1}
                }
            }
        ]
        
        mode_breakdown_cursor = db[Collections.HISTORY].aggregate(pipeline)
        mode_breakdown_list = await mode_breakdown_cursor.to_list(length=None)
        
        mode_breakdown = {
            item['_id']: item['count']
            for item in mode_breakdown_list
        }
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_cursor = db[Collections.HISTORY].find(
            {
                'userId': user_id,
                'createdAt': {'$gte': week_ago}
            },
            {'createdAt': 1, '_id': 0}
        ).sort('createdAt', -1)
        
        recent_list = await recent_cursor.to_list(length=None)
        recent_activity = [item['createdAt'] for item in recent_list]
        
        return {
            'totalVideos': unique_videos,
            'totalSummaries': total,
            'modeBreakdown': mode_breakdown,
            'recentActivity': recent_activity,
            'recentCount': len(recent_activity)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get history stats for user {user_id}: {e}")
        return {
            'totalVideos': 0,
            'totalSummaries': 0,
            'modeBreakdown': {},
            'recentActivity': [],
            'recentCount': 0
        }


async def check_video_exists_in_history(
    user_id: str,
    video_id: str
) -> bool:
    """
    Check if a video exists in user's history
    
    Args:
        user_id: User ID
        video_id: YouTube video ID
    
    Returns:
        True if video exists, False otherwise
    """
    try:
        db = await get_db()
        
        count = await db[Collections.HISTORY].count_documents({
            'userId': user_id,
            'videoId': video_id
        })
        
        return count > 0
        
    except Exception as e:
        logger.error(f"❌ Failed to check video in history: {e}")
        return False
