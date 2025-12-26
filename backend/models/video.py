# models/video.py - FASTAPI ASYNC VERSION
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, HttpUrl
import uuid

from database.session import get_db, Collections
from config.logging_config import logger


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class VideoModel(BaseModel):
    """Video document model"""
    videoId: str = Field(..., description="YouTube video ID")
    userId: str = Field(..., description="User ID who processed the video")
    url: str = Field(..., description="YouTube video URL")
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    thumbnail: Optional[str] = Field(None, description="Video thumbnail URL")
    duration: Optional[int] = Field(None, description="Video duration in seconds")
    channelName: Optional[str] = None
    transcript: str = Field(..., description="Full transcript text")
    audioPath: Optional[str] = Field(None, description="Path to downloaded audio file")
    source: str = Field(default="whisper_transcription", description="Transcript source")
    chunkCount: Optional[int] = Field(0, description="Number of chunks created")
    embeddingStatus: str = Field(default="pending", description="Embedding status")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    processedAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "videoId": "dQw4w9WgXcQ",
                "userId": "user_123",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "description": "Music video by Rick Astley",
                "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
                "duration": 213,
                "channelName": "Rick Astley",
                "transcript": "We're no strangers to love...",
                "audioPath": "/data/audio/dQw4w9WgXcQ.mp3",
                "source": "whisper_transcription",
                "chunkCount": 10,
                "embeddingStatus": "completed",
                "createdAt": "2025-12-25T17:00:00Z"
            }
        }


class SaveVideoRequest(BaseModel):
    """Request model for saving a video"""
    videoId: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    channelName: Optional[str] = None
    transcript: str = Field(..., min_length=1)
    audioPath: Optional[str] = None
    source: str = Field(default="whisper_transcription")


class UpdateVideoRequest(BaseModel):
    """Request model for updating a video"""
    title: Optional[str] = None
    description: Optional[str] = None
    chunkCount: Optional[int] = None
    embeddingStatus: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VideoStatsModel(BaseModel):
    """Video statistics model"""
    totalVideos: int
    totalTranscriptLength: int
    avgDuration: float
    sourceBreakdown: Dict[str, int]


# ============================================================================
# VIDEO DATABASE OPERATIONS (Async)
# ============================================================================

async def save_video(
    user_id: str,
    video_id: str,
    url: str,
    transcript: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    thumbnail: Optional[str] = None,
    duration: Optional[int] = None,
    channel_name: Optional[str] = None,
    audio_path: Optional[str] = None,
    source: str = "whisper_transcription"
) -> str:
    """
    Save video to MongoDB
    
    Args:
        user_id: User ID
        video_id: YouTube video ID
        url: YouTube URL
        transcript: Full transcript
        title: Video title
        description: Video description
        thumbnail: Thumbnail URL
        duration: Duration in seconds
        channel_name: Channel name
        audio_path: Path to audio file (optional)
        source: How transcript was obtained (youtube_captions/whisper_transcription)
    
    Returns:
        video_id: YouTube video ID
    """
    try:
        db = await get_db()
        
        # Check if video already exists
        existing = await db[Collections.YOUTUBE_VIDEOS].find_one({
            'userId': user_id,
            'videoId': video_id
        })
        
        if existing:
            logger.warning(f"⚠️  Video {video_id} already exists for user {user_id}")
            return video_id
        
        video_doc = {
            'videoId': video_id,
            'userId': user_id,
            'url': url,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'channelName': channel_name,
            'transcript': transcript,
            'audioPath': audio_path,
            'source': source,
            'chunkCount': 0,
            'embeddingStatus': 'pending',
            'metadata': {},
            'createdAt': datetime.utcnow(),
            'processedAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }
        
        await db[Collections.YOUTUBE_VIDEOS].insert_one(video_doc)
        
        logger.info(f"💾 Video saved to MongoDB: {video_id} (source: {source})")
        return video_id
        
    except Exception as e:
        logger.error(f"❌ Failed to save video: {e}")
        raise


async def get_video_by_id(
    user_id: str,
    video_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get video by ID for specific user
    
    Args:
        user_id: User ID
        video_id: YouTube video ID
    
    Returns:
        Video document or None
    """
    try:
        db = await get_db()
        
        video = await db[Collections.YOUTUBE_VIDEOS].find_one(
            {
                'userId': user_id,
                'videoId': video_id
            },
            {'_id': 0}
        )
        
        if video:
            logger.info(f"📖 Retrieved video from MongoDB: {video_id}")
        
        return video
        
    except Exception as e:
        logger.error(f"❌ Failed to get video: {e}")
        return None


async def get_video_by_id_any_user(video_id: str) -> Optional[Dict[str, Any]]:
    """
    Get video by ID from any user (for admin purposes)
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Video document or None
    """
    try:
        db = await get_db()
        
        video = await db[Collections.YOUTUBE_VIDEOS].find_one(
            {'videoId': video_id},
            {'_id': 0}
        )
        
        return video
        
    except Exception as e:
        logger.error(f"❌ Failed to get video: {e}")
        return None


async def get_user_videos(
    user_id: str,
    limit: int = 50,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """
    Get all videos for user
    
    Args:
        user_id: User ID
        limit: Maximum number of videos
        skip: Number to skip (pagination)
    
    Returns:
        List of video documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.YOUTUBE_VIDEOS].find(
            {'userId': user_id},
            {'_id': 0, 'transcript': 0}  # Exclude transcript to reduce size
        ).sort('createdAt', -1).skip(skip).limit(limit)
        
        videos = await cursor.to_list(length=limit)
        
        logger.info(f"📋 Retrieved {len(videos)} videos for user {user_id}")
        return videos
        
    except Exception as e:
        logger.error(f"❌ Failed to get user videos: {e}")
        return []


async def get_user_video_count(user_id: str) -> int:
    """
    Get total number of videos for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Number of videos
    """
    try:
        db = await get_db()
        
        count = await db[Collections.YOUTUBE_VIDEOS].count_documents({
            'userId': user_id
        })
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to get video count: {e}")
        return 0


async def update_video(
    user_id: str,
    video_id: str,
    updates: Dict[str, Any]
) -> bool:
    """
    Update video document
    
    Args:
        user_id: User ID
        video_id: YouTube video ID
        updates: Dictionary of fields to update
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        # Add updatedAt timestamp
        updates['updatedAt'] = datetime.utcnow()
        
        result = await db[Collections.YOUTUBE_VIDEOS].update_one(
            {
                'userId': user_id,
                'videoId': video_id
            },
            {'$set': updates}
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Updated video {video_id}")
            return True
        
        logger.warning(f"⚠️  Video {video_id} not found or not modified")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to update video: {e}")
        raise


async def update_video_chunk_count(
    user_id: str,
    video_id: str,
    chunk_count: int
) -> bool:
    """
    Update video chunk count
    
    Args:
        user_id: User ID
        video_id: YouTube video ID
        chunk_count: Number of chunks
    
    Returns:
        True if successful, False otherwise
    """
    try:
        return await update_video(user_id, video_id, {'chunkCount': chunk_count})
        
    except Exception as e:
        logger.error(f"❌ Failed to update chunk count: {e}")
        raise


async def update_video_embedding_status(
    user_id: str,
    video_id: str,
    status: str
) -> bool:
    """
    Update video embedding status
    
    Args:
        user_id: User ID
        video_id: YouTube video ID
        status: Status (pending/processing/completed/failed)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        return await update_video(user_id, video_id, {'embeddingStatus': status})
        
    except Exception as e:
        logger.error(f"❌ Failed to update embedding status: {e}")
        raise


async def delete_video(
    user_id: str,
    video_id: str
) -> bool:
    """
    Delete video
    
    Args:
        user_id: User ID
        video_id: YouTube video ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.YOUTUBE_VIDEOS].delete_one({
            'userId': user_id,
            'videoId': video_id
        })
        
        if result.deleted_count > 0:
            logger.info(f"🗑️  Deleted video {video_id}")
            return True
        
        logger.warning(f"⚠️  Video {video_id} not found")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to delete video: {e}")
        raise


async def search_videos(
    user_id: str,
    query: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search videos by title or description
    
    Args:
        user_id: User ID
        query: Search query
        limit: Maximum number of results
    
    Returns:
        List of matching video documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.YOUTUBE_VIDEOS].find(
            {
                'userId': user_id,
                '$or': [
                    {'title': {'$regex': query, '$options': 'i'}},
                    {'description': {'$regex': query, '$options': 'i'}},
                    {'channelName': {'$regex': query, '$options': 'i'}}
                ]
            },
            {'_id': 0, 'transcript': 0}
        ).sort('createdAt', -1).limit(limit)
        
        videos = await cursor.to_list(length=limit)
        
        logger.info(f"🔍 Found {len(videos)} videos matching '{query}'")
        return videos
        
    except Exception as e:
        logger.error(f"❌ Failed to search videos: {e}")
        return []


async def get_videos_by_source(
    user_id: str,
    source: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get videos filtered by transcript source
    
    Args:
        user_id: User ID
        source: Transcript source (youtube_captions/whisper_transcription)
        limit: Maximum number of videos
    
    Returns:
        List of video documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.YOUTUBE_VIDEOS].find(
            {
                'userId': user_id,
                'source': source
            },
            {'_id': 0, 'transcript': 0}
        ).sort('createdAt', -1).limit(limit)
        
        videos = await cursor.to_list(length=limit)
        
        return videos
        
    except Exception as e:
        logger.error(f"❌ Failed to get videos by source: {e}")
        return []


async def get_video_stats(user_id: str) -> Dict[str, Any]:
    """
    Get video statistics for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Dictionary with statistics
    """
    try:
        db = await get_db()
        
        # Total count
        total = await db[Collections.YOUTUBE_VIDEOS].count_documents({
            'userId': user_id
        })
        
        # Source breakdown
        pipeline = [
            {'$match': {'userId': user_id}},
            {
                '$group': {
                    '_id': '$source',
                    'count': {'$sum': 1}
                }
            }
        ]
        
        source_breakdown_cursor = db[Collections.YOUTUBE_VIDEOS].aggregate(pipeline)
        source_breakdown_list = await source_breakdown_cursor.to_list(length=None)
        
        source_breakdown = {
            item['_id']: item['count']
            for item in source_breakdown_list
        }
        
        # Average duration and total transcript length
        stats_pipeline = [
            {'$match': {'userId': user_id}},
            {
                '$group': {
                    '_id': None,
                    'avgDuration': {'$avg': '$duration'},
                    'totalTranscriptLength': {'$sum': {'$strLenCP': '$transcript'}}
                }
            }
        ]
        
        stats_cursor = db[Collections.YOUTUBE_VIDEOS].aggregate(stats_pipeline)
        stats_result = await stats_cursor.to_list(1)
        
        avg_duration = 0
        total_transcript_length = 0
        
        if stats_result:
            avg_duration = stats_result[0].get('avgDuration', 0) or 0
            total_transcript_length = stats_result[0].get('totalTranscriptLength', 0) or 0
        
        return {
            'totalVideos': total,
            'totalTranscriptLength': total_transcript_length,
            'avgDuration': round(avg_duration, 2),
            'sourceBreakdown': source_breakdown
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get video stats: {e}")
        return {
            'totalVideos': 0,
            'totalTranscriptLength': 0,
            'avgDuration': 0,
            'sourceBreakdown': {}
        }


async def get_recent_videos(
    user_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get most recently processed videos
    
    Args:
        user_id: User ID
        limit: Number of videos
    
    Returns:
        List of recent video documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.YOUTUBE_VIDEOS].find(
            {'userId': user_id},
            {'_id': 0, 'transcript': 0}
        ).sort('processedAt', -1).limit(limit)
        
        videos = await cursor.to_list(length=limit)
        
        return videos
        
    except Exception as e:
        logger.error(f"❌ Failed to get recent videos: {e}")
        return []


async def check_video_exists(
    user_id: str,
    video_id: str
) -> bool:
    """
    Check if video exists in database
    
    Args:
        user_id: User ID
        video_id: YouTube video ID
    
    Returns:
        True if exists, False otherwise
    """
    try:
        db = await get_db()
        
        count = await db[Collections.YOUTUBE_VIDEOS].count_documents({
            'userId': user_id,
            'videoId': video_id
        })
        
        return count > 0
        
    except Exception as e:
        logger.error(f"❌ Failed to check video existence: {e}")
        return False
