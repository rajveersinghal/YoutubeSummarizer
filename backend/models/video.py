# models/video.py
from datetime import datetime
from database.connection import db_connection  # ✅ Changed from get_db
from config.logging_config import logger

def save_video(user_id: str, video_id: str, url: str, transcript: str, audio_path: str = None, source: str = "whisper_transcription") -> str:
    """
    Save video to MongoDB
    
    Args:
        user_id: User ID
        video_id: YouTube video ID
        url: YouTube URL
        transcript: Full transcript
        audio_path: Path to audio file (optional)
        source: How transcript was obtained (youtube_captions or whisper_transcription)
    
    Returns:
        str: MongoDB document ID
    """
    try:
        db = db_connection.db  # ✅ Changed
        
        video_doc = {
            'userId': user_id,
            'videoId': video_id,
            'url': url,
            'transcript': transcript,
            'audioPath': audio_path,
            'source': source,
            'createdAt': datetime.utcnow(),
            'processedAt': datetime.utcnow()
        }
        
        result = db.videos.insert_one(video_doc)
        
        logger.info(f"💾 Video saved to MongoDB: {video_id} (source: {source})")
        return str(result.inserted_id)
        
    except Exception as e:
        logger.error(f"Failed to save video: {e}")
        raise

def get_video_by_id(user_id: str, video_id: str):
    """Get video by ID for specific user"""
    try:
        db = db_connection.db  # ✅ Changed
        video = db.videos.find_one({
            'userId': user_id,
            'videoId': video_id
        })
        
        if video:
            logger.info(f"📖 Retrieved video from MongoDB: {video_id}")
        
        return video
        
    except Exception as e:
        logger.error(f"Failed to get video: {e}")
        return None

def get_user_videos(user_id: str, limit: int = 50):
    """Get all videos for user"""
    try:
        db = db_connection.db  # ✅ Changed
        videos = list(db.videos.find(
            {'userId': user_id}
        ).sort('createdAt', -1).limit(limit))
        
        return videos
        
    except Exception as e:
        logger.error(f"Failed to get user videos: {e}")
        return []

def update_video(user_id: str, video_id: str, updates: dict):
    """Update video document"""
    try:
        db = db_connection.db  # ✅ Changed
        result = db.videos.update_one(
            {'userId': user_id, 'videoId': video_id},
            {'$set': updates}
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"Failed to update video: {e}")
        return False

def delete_video(user_id: str, video_id: str):
    """Delete video"""
    try:
        db = db_connection.db  # ✅ Changed
        result = db.videos.delete_one({
            'userId': user_id,
            'videoId': video_id
        })
        
        return result.deleted_count > 0
        
    except Exception as e:
        logger.error(f"Failed to delete video: {e}")
        return False
