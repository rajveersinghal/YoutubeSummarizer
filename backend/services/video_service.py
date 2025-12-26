# services/video_service.py - VIDEO SERVICE

from typing import List, Dict, Optional
import time
import asyncio
from config.logging_config import logger
from database.database import get_db


class VideoService:
    """Service for managing video metadata and processing"""
    
    def __init__(self):
        """Initialize video service"""
        self.db = get_db()
    
    async def create_video(
        self,
        video_id: str,
        user_id: str,
        title: str,
        description: Optional[str],
        file_name: str,
        file_size: int,
        format: str,
        video_url: str
    ) -> Dict:
        """
        Create video record
        
        Args:
            video_id: Unique video ID
            user_id: User ID
            title: Video title
            description: Optional description
            file_name: Original file name
            file_size: File size in bytes
            format: Video format (mp4, avi, etc.)
            video_url: Storage URL
        
        Returns:
            Created video
        """
        try:
            timestamp = time.time()
            
            video = {
                "video_id": video_id,
                "user_id": user_id,
                "title": title,
                "description": description,
                "file_name": file_name,
                "file_size": file_size,
                "format": format,
                "video_url": video_url,
                "stream_url": f"/api/videos/{video_id}/stream",
                "status": "processing",
                "duration": None,
                "resolution": None,
                "thumbnail_url": None,
                "created_at": timestamp,
                "updated_at": timestamp
            }
            
            await self.db.videos.insert_one(video)
            
            logger.info(f"Video created: {video_id}")
            return video
        
        except Exception as e:
            logger.error(f"Error creating video: {e}")
            raise
    
    async def get_video(
        self,
        video_id: str,
        user_id: str
    ) -> Optional[Dict]:
        """
        Get video by ID
        
        Args:
            video_id: Video ID
            user_id: User ID
        
        Returns:
            Video or None
        """
        try:
            video = await self.db.videos.find_one({
                "video_id": video_id,
                "user_id": user_id
            })
            
            return video
        
        except Exception as e:
            logger.error(f"Error fetching video: {e}")
            return None
    
    async def get_user_videos(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict]:
        """
        Get user's videos
        
        Args:
            user_id: User ID
            limit: Number to return
            offset: Pagination offset
            status: Filter by status
            search: Search query
        
        Returns:
            List of videos
        """
        try:
            query = {"user_id": user_id}
            
            if status:
                query["status"] = status
            
            if search:
                query["$or"] = [
                    {"title": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]
            
            videos = await self.db.videos.find(query).sort(
                "created_at", -1
            ).skip(offset).limit(limit).to_list(length=limit)
            
            return videos
        
        except Exception as e:
            logger.error(f"Error fetching videos: {e}")
            return []
    
    async def count_user_videos(
        self,
        user_id: str,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> int:
        """
        Count user's videos
        
        Args:
            user_id: User ID
            status: Filter by status
            search: Search query
        
        Returns:
            Video count
        """
        try:
            query = {"user_id": user_id}
            
            if status:
                query["status"] = status
            
            if search:
                query["$or"] = [
                    {"title": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]
            
            count = await self.db.videos.count_documents(query)
            return count
        
        except Exception as e:
            logger.error(f"Error counting videos: {e}")
            return 0
    
    async def update_video(
        self,
        video_id: str,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Update video metadata
        
        Args:
            video_id: Video ID
            user_id: User ID
            title: New title
            description: New description
        
        Returns:
            Updated video
        """
        try:
            update_fields = {"updated_at": time.time()}
            
            if title is not None:
                update_fields["title"] = title
            
            if description is not None:
                update_fields["description"] = description
            
            result = await self.db.videos.find_one_and_update(
                {"video_id": video_id, "user_id": user_id},
                {"$set": update_fields},
                return_document=True
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error updating video: {e}")
            return None
    
    async def update_video_status(
        self,
        video_id: str,
        status: str,
        duration: Optional[float] = None,
        resolution: Optional[str] = None,
        thumbnail_url: Optional[str] = None
    ):
        """
        Update video processing status
        
        Args:
            video_id: Video ID
            status: New status
            duration: Video duration in seconds
            resolution: Video resolution (e.g., "1920x1080")
            thumbnail_url: Thumbnail URL
        """
        try:
            update_fields = {
                "status": status,
                "updated_at": time.time()
            }
            
            if duration is not None:
                update_fields["duration"] = duration
            
            if resolution is not None:
                update_fields["resolution"] = resolution
            
            if thumbnail_url is not None:
                update_fields["thumbnail_url"] = thumbnail_url
            
            await self.db.videos.update_one(
                {"video_id": video_id},
                {"$set": update_fields}
            )
        
        except Exception as e:
            logger.error(f"Error updating video status: {e}")
            raise
    
    async def delete_video(
        self,
        video_id: str,
        user_id: str
    ):
        """
        Delete video
        
        Args:
            video_id: Video ID
            user_id: User ID
        """
        try:
            await self.db.videos.delete_one({
                "video_id": video_id,
                "user_id": user_id
            })
            
            logger.info(f"Video deleted: {video_id}")
        
        except Exception as e:
            logger.error(f"Error deleting video: {e}")
            raise
    
    async def process_video_async(
        self,
        video_id: str,
        file_path: str
    ):
        """
        Process video asynchronously (extract metadata, generate thumbnail)
        
        Args:
            video_id: Video ID
            file_path: Video file path
        """
        try:
            # TODO: Implement video processing
            # - Extract duration, resolution using ffmpeg
            # - Generate thumbnail
            # - Update video status
            
            # For now, just mark as ready after a delay
            await asyncio.sleep(2)  # Simulate processing
            
            await self.update_video_status(
                video_id=video_id,
                status="ready",
                duration=120.0,  # Placeholder
                resolution="1920x1080"  # Placeholder
            )
            
            logger.info(f"Video processed: {video_id}")
        
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            await self.update_video_status(video_id=video_id, status="failed")
    
    async def get_processing_status(
        self,
        video_id: str,
        user_id: str
    ) -> Optional[Dict]:
        """
        Get video processing status
        
        Args:
            video_id: Video ID
            user_id: User ID
        
        Returns:
            Status information
        """
        try:
            video = await self.get_video(video_id, user_id)
            
            if not video:
                return None
            
            return {
                "video_id": video_id,
                "status": video["status"],
                "progress": 100 if video["status"] == "ready" else 50,
                "message": "Processing complete" if video["status"] == "ready" else "Processing..."
            }
        
        except Exception as e:
            logger.error(f"Error getting video status: {e}")
            return None
