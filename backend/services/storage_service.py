# services/storage_service.py - FILE STORAGE SERVICE

import os
import aiofiles
from pathlib import Path
from typing import Optional
import shutil
from config.settings import settings
from config.logging_config import logger


class StorageService:
    """Service for managing file storage (local or cloud)"""
    
    def __init__(self):
        """Initialize storage service"""
        self.storage_path = Path(settings.STORAGE_PATH or "storage")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Storage service initialized: {self.storage_path}")
    
    def _get_user_path(self, user_id: str) -> Path:
        """Get user's storage directory"""
        user_path = self.storage_path / user_id
        user_path.mkdir(parents=True, exist_ok=True)
        return user_path
    
    async def save_file(
        self,
        user_id: str,
        file_content: bytes,
        filename: str
    ) -> str:
        """
        Save file to storage
        
        Args:
            user_id: User ID
            file_content: File content bytes
            filename: Filename
        
        Returns:
            File URL/path
        """
        try:
            user_path = self._get_user_path(user_id)
            file_path = user_path / filename
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            # Return relative path
            file_url = f"{user_id}/{filename}"
            logger.debug(f"File saved: {file_url}")
            
            return file_url
        
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise
    
    async def save_video(
        self,
        user_id: str,
        file_content: bytes,
        filename: str
    ) -> str:
        """
        Save video file
        
        Args:
            user_id: User ID
            file_content: Video content bytes
            filename: Filename
        
        Returns:
            Video URL/path
        """
        try:
            # Create videos subdirectory
            user_path = self._get_user_path(user_id)
            videos_path = user_path / "videos"
            videos_path.mkdir(exist_ok=True)
            
            file_path = videos_path / filename
            
            # Save video
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            video_url = f"{user_id}/videos/{filename}"
            logger.debug(f"Video saved: {video_url}")
            
            return video_url
        
        except Exception as e:
            logger.error(f"Error saving video: {e}")
            raise
    
    async def get_file(
        self,
        user_id: str,
        file_url: str
    ) -> Optional[bytes]:
        """
        Get file content
        
        Args:
            user_id: User ID
            file_url: File URL/path
        
        Returns:
            File content bytes
        """
        try:
            file_path = self.storage_path / file_url
            
            if not file_path.exists():
                logger.warning(f"File not found: {file_url}")
                return None
            
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            return content
        
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return None
    
    async def get_video(
        self,
        user_id: str,
        video_url: str
    ) -> Optional[bytes]:
        """
        Get video content
        
        Args:
            user_id: User ID
            video_url: Video URL/path
        
        Returns:
            Video content bytes
        """
        return await self.get_file(user_id, video_url)
    
    async def get_video_path(self, video_url: str) -> str:
        """
        Get absolute video file path
        
        Args:
            video_url: Video URL/path
        
        Returns:
            Absolute file path
        """
        file_path = self.storage_path / video_url
        return str(file_path.absolute())
    
    async def delete_file(
        self,
        user_id: str,
        file_url: str
    ):
        """
        Delete file
        
        Args:
            user_id: User ID
            file_url: File URL/path
        """
        try:
            file_path = self.storage_path / file_url
            
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"File deleted: {file_url}")
        
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise
    
    async def delete_video(
        self,
        user_id: str,
        video_url: str
    ):
        """
        Delete video
        
        Args:
            user_id: User ID
            video_url: Video URL/path
        """
        await self.delete_file(user_id, video_url)
    
    async def get_file_size(self, file_url: str) -> int:
        """
        Get file size
        
        Args:
            file_url: File URL/path
        
        Returns:
            File size in bytes
        """
        try:
            file_path = self.storage_path / file_url
            
            if file_path.exists():
                return file_path.stat().st_size
            
            return 0
        
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return 0
    
    async def cleanup_user_storage(self, user_id: str):
        """
        Delete all files for a user
        
        Args:
            user_id: User ID
        """
        try:
            user_path = self._get_user_path(user_id)
            
            if user_path.exists():
                shutil.rmtree(user_path)
                logger.info(f"User storage cleaned: {user_id}")
        
        except Exception as e:
            logger.error(f"Error cleaning user storage: {e}")
            raise
