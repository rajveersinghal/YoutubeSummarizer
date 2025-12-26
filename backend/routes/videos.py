# backend/routes/videos.py - COMPLETE VIDEO ROUTES

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import time
import uuid
import os
from pathlib import Path

from middleware.auth import get_current_user
from database.database import get_db
from config.settings import settings
from config.logging_config import logger
from services.video_processor import VideoProcessor

router = APIRouter(prefix="/api/videos", tags=["Videos"])
video_processor = VideoProcessor()

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class YouTubeUploadRequest(BaseModel):
    youtube_url: str
    title: Optional[str] = None

class VideoResponse(BaseModel):
    video_id: str
    title: str
    transcript: Optional[str] = None
    duration: Optional[float] = None
    status: str

# ============================================================================
# UPLOAD YOUTUBE VIDEO
# ============================================================================

@router.post("/youtube", response_model=VideoResponse)
async def upload_youtube_video(
    request: YouTubeUploadRequest,
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Upload and process a YouTube video
    """
    try:
        youtube_url = request.youtube_url
        title = request.title
        
        logger.info(f"🎥 Processing YouTube video: {youtube_url}")
        
        # Validate YouTube URL
        if not any(domain in youtube_url for domain in ['youtube.com', 'youtu.be']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid YouTube URL"
            )
        
        # Generate video ID
        video_id = str(uuid.uuid4())
        
        # Process YouTube video (get transcript)
        try:
            video_data = await video_processor.process_youtube(youtube_url, video_id)
            
            # Get title if not provided
            if not title:
                title = video_data.get('title', 'YouTube Video')
            
            transcript = video_data.get('transcript', '')
            duration = video_data.get('duration', 0)
            
            if not transcript:
                raise ValueError("No transcript available for this video")
            
        except Exception as e:
            logger.error(f"❌ YouTube processing error: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to process YouTube video: {str(e)}"
            )
        
        # Save to database
        video_doc = {
            "video_id": video_id,
            "user_id": user_id,
            "title": title,
            "youtube_url": youtube_url,
            "transcript": transcript,
            "duration": duration,
            "status": "completed",
            "source": "youtube",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        
        db.videos.insert_one(video_doc)
        
        # ✅ NEW: Create conversation with video context
        conversation_id = str(uuid.uuid4())
        conversation_doc = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "title": f"📹 {title}",
            "created_at": time.time(),
            "updated_at": time.time(),
            "message_count": 0,
            "context_type": "youtube",
            "context_id": video_id,
        }
        
        db.conversations.insert_one(conversation_doc)
        
        logger.info(f"✅ YouTube video processed: {video_id}")
        logger.info(f"✅ Conversation created: {conversation_id}")
        
        return {
            "video_id": video_id,
            "conversation_id": conversation_id,  # ✅ Return this
            "title": title,
            "transcript": transcript,
            "duration": duration,
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ YouTube upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process YouTube video: {str(e)}"
        )

# ============================================================================
# UPLOAD VIDEO FILE
# ============================================================================

@router.post("/upload")
async def upload_video_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Upload a video file
    """
    try:
        logger.info(f"📹 Uploading video file: {file.filename}")
        
        # Validate file type
        allowed_types = ['video/mp4', 'video/avi', 'video/mov', 'video/mkv']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only video files are allowed."
            )
        
        # Validate file size (100MB max)
        max_size = 100 * 1024 * 1024  # 100MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds 100MB limit"
            )
        
        # Generate video ID
        video_id = str(uuid.uuid4())
        
        # Save file
        video_dir = Path(settings.STORAGE_PATH) / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)
        
        file_extension = Path(file.filename).suffix
        file_path = video_dir / f"{video_id}{file_extension}"
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Process video (extract transcript if possible)
        transcript = ""
        duration = 0
        
        try:
            video_data = await video_processor.process_video_file(str(file_path), video_id)
            transcript = video_data.get('transcript', '')
            duration = video_data.get('duration', 0)
        except Exception as e:
            logger.warning(f"⚠️ Could not extract transcript: {e}")
        
        # Save to database
        video_doc = {
            "video_id": video_id,
            "user_id": user_id,
            "title": title,
            "description": description,
            "file_path": str(file_path),
            "file_name": file.filename,
            "file_size": len(file_content),
            "transcript": transcript,
            "duration": duration,
            "status": "completed",
            "source": "upload",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        
        db.videos.insert_one(video_doc)
        
        logger.info(f"✅ Video uploaded: {video_id}")
        
        return {
            "success": True,
            "video_id": video_id,
            "title": title,
            "transcript": transcript,
            "duration": duration,
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Video upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload video: {str(e)}"
        )

# ============================================================================
# GET ALL VIDEOS
# ============================================================================

@router.get("/")
async def get_all_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get all videos for current user
    """
    try:
        skip = (page - 1) * page_size
        
        videos = list(
            db.videos
            .find({"user_id": user_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        
        total = db.videos.count_documents({"user_id": user_id})
        
        # Format videos
        formatted_videos = []
        for video in videos:
            formatted_videos.append({
                "video_id": video.get("video_id"),
                "title": video.get("title"),
                "duration": video.get("duration"),
                "status": video.get("status"),
                "source": video.get("source"),
                "created_at": video.get("created_at"),
            })
        
        return {
            "success": True,
            "videos": formatted_videos,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting videos: {e}", exc_info=True)
        return {
            "success": True,
            "videos": [],
            "total": 0,
            "page": page,
            "page_size": page_size
        }

# ============================================================================
# GET VIDEO BY ID
# ============================================================================

@router.get("/{video_id}")
async def get_video_by_id(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get a specific video
    """
    try:
        video = db.videos.find_one({
            "video_id": video_id,
            "user_id": user_id
        })
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        return {
            "success": True,
            "video": {
                "video_id": video.get("video_id"),
                "title": video.get("title"),
                "description": video.get("description"),
                "transcript": video.get("transcript"),
                "duration": video.get("duration"),
                "status": video.get("status"),
                "source": video.get("source"),
                "created_at": video.get("created_at"),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting video: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get video"
        )

# ============================================================================
# DELETE VIDEO
# ============================================================================

@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Delete a video
    """
    try:
        result = db.videos.delete_one({
            "video_id": video_id,
            "user_id": user_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        logger.info(f"✅ Video deleted: {video_id}")
        
        return {
            "success": True,
            "message": "Video deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting video: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete video"
        )

__all__ = ["router"]
