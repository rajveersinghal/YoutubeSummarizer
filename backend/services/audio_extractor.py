# services/audio_extractor.py - FASTAPI ASYNC VERSION
import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import yt_dlp

from config.settings import settings
from config.logging_config import logger


# ============================================================================
# AUDIO DIRECTORY SETUP
# ============================================================================

BASE_DIR = settings.BASE_DIR
AUDIO_DIR = settings.AUDIO_DIR
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# YOUTUBE AUDIO EXTRACTOR
# ============================================================================

class YouTubeAudioExtractor:
    """Extract audio from YouTube videos"""
    
    def __init__(self):
        self.audio_dir = AUDIO_DIR
        self.max_retries = 3
    
    def _get_ydl_opts(self, video_id: str, quality: str = "192") -> Dict[str, Any]:
        """
        Get yt-dlp options
        
        Args:
            video_id: YouTube video ID
            quality: Audio quality (128, 192, 256, 320)
        
        Returns:
            Dictionary of yt-dlp options
        """
        out_tmpl = str(self.audio_dir / f"{video_id}.%(ext)s")
        
        return {
            "format": "bestaudio/best",
            "outtmpl": out_tmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_flat": False,
            "socket_timeout": 30,
            "retries": self.max_retries,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                }
            ],
            "postprocessor_args": [
                "-ar", "16000"  # Resample to 16kHz for Whisper
            ],
            # Add cookies for age-restricted videos
            "cookiefile": None,
            # Add user agent
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        }
    
    def extract_audio_sync(
        self,
        video_id: str,
        quality: str = "192"
    ) -> str:
        """
        Download audio for a YouTube video (synchronous)
        
        Args:
            video_id: YouTube video ID
            quality: Audio quality (128, 192, 256, 320)
        
        Returns:
            Path to downloaded audio file
        
        Raises:
            RuntimeError: If download fails
        """
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            audio_path = self.audio_dir / f"{video_id}.mp3"
            
            # Check if audio already exists
            if audio_path.exists():
                logger.info(f"🎵 Audio already exists: {audio_path}")
                return str(audio_path)
            
            logger.info(f"📥 Downloading audio from YouTube: {video_id}")
            
            ydl_opts = self._get_ydl_opts(video_id, quality)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    raise RuntimeError(f"Failed to extract video info for {video_id}")
            
            # Verify audio file exists
            if not audio_path.exists():
                raise RuntimeError(f"Audio file not found at {audio_path}")
            
            file_size = audio_path.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"✅ Audio downloaded successfully: {audio_path} ({file_size:.2f} MB)")
            
            return str(audio_path)
            
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"❌ YouTube download error for {video_id}: {e}")
            raise RuntimeError(f"Failed to download audio: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Audio extraction failed for {video_id}: {e}")
            raise RuntimeError(f"Audio extraction error: {str(e)}")
    
    async def extract_audio(
        self,
        video_id: str,
        quality: str = "192"
    ) -> str:
        """
        Download audio for a YouTube video (async)
        
        Args:
            video_id: YouTube video ID
            quality: Audio quality (128, 192, 256, 320)
        
        Returns:
            Path to downloaded audio file
        """
        try:
            # Run blocking operation in thread pool
            loop = asyncio.get_event_loop()
            audio_path = await loop.run_in_executor(
                None,
                self.extract_audio_sync,
                video_id,
                quality
            )
            return audio_path
            
        except Exception as e:
            logger.error(f"❌ Async audio extraction failed: {e}")
            raise
    
    def get_video_info(self, video_id: str) -> Dict[str, Any]:
        """
        Get video information without downloading
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Dictionary with video metadata
        """
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": False
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    "videoId": video_id,
                    "title": info.get("title"),
                    "description": info.get("description"),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                    "channelName": info.get("uploader") or info.get("channel"),
                    "channelId": info.get("channel_id"),
                    "viewCount": info.get("view_count"),
                    "uploadDate": info.get("upload_date"),
                    "categories": info.get("categories", []),
                    "tags": info.get("tags", [])
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get video info for {video_id}: {e}")
            raise RuntimeError(f"Failed to get video info: {str(e)}")
    
    async def get_video_info_async(self, video_id: str) -> Dict[str, Any]:
        """
        Get video information asynchronously
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Dictionary with video metadata
        """
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                self.get_video_info,
                video_id
            )
            return info
            
        except Exception as e:
            logger.error(f"❌ Async video info fetch failed: {e}")
            raise
    
    def delete_audio(self, video_id: str) -> bool:
        """
        Delete downloaded audio file
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            True if deleted, False otherwise
        """
        try:
            audio_path = self.audio_dir / f"{video_id}.mp3"
            
            if audio_path.exists():
                audio_path.unlink()
                logger.info(f"🗑️  Deleted audio file: {audio_path}")
                return True
            
            logger.warning(f"⚠️  Audio file not found: {audio_path}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to delete audio: {e}")
            return False
    
    async def delete_audio_async(self, video_id: str) -> bool:
        """
        Delete audio file asynchronously
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            True if deleted, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            deleted = await loop.run_in_executor(
                None,
                self.delete_audio,
                video_id
            )
            return deleted
            
        except Exception as e:
            logger.error(f"❌ Async audio deletion failed: {e}")
            return False
    
    def audio_exists(self, video_id: str) -> bool:
        """
        Check if audio file exists
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            True if exists, False otherwise
        """
        audio_path = self.audio_dir / f"{video_id}.mp3"
        return audio_path.exists()
    
    def get_audio_path(self, video_id: str) -> Optional[str]:
        """
        Get path to audio file if it exists
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Path to audio file or None
        """
        audio_path = self.audio_dir / f"{video_id}.mp3"
        return str(audio_path) if audio_path.exists() else None
    
    def cleanup_old_audio(self, days: int = 7) -> int:
        """
        Delete audio files older than specified days
        
        Args:
            days: Number of days
        
        Returns:
            Number of files deleted
        """
        try:
            import time
            
            current_time = time.time()
            max_age = days * 24 * 60 * 60  # Convert to seconds
            deleted_count = 0
            
            for audio_file in self.audio_dir.glob("*.mp3"):
                file_age = current_time - audio_file.stat().st_mtime
                
                if file_age > max_age:
                    audio_file.unlink()
                    deleted_count += 1
                    logger.info(f"🗑️  Deleted old audio: {audio_file.name}")
            
            logger.info(f"🧹 Cleaned up {deleted_count} old audio files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return 0
    
    async def cleanup_old_audio_async(self, days: int = 7) -> int:
        """
        Delete old audio files asynchronously
        
        Args:
            days: Number of days
        
        Returns:
            Number of files deleted
        """
        try:
            loop = asyncio.get_event_loop()
            count = await loop.run_in_executor(
                None,
                self.cleanup_old_audio,
                days
            )
            return count
            
        except Exception as e:
            logger.error(f"❌ Async cleanup failed: {e}")
            return 0


# ============================================================================
# GLOBAL EXTRACTOR INSTANCE
# ============================================================================

audio_extractor = YouTubeAudioExtractor()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def extract_youtube_audio(video_id: str, quality: str = "192") -> str:
    """
    Download audio for a YouTube video (sync wrapper)
    
    Args:
        video_id: YouTube video ID
        quality: Audio quality
    
    Returns:
        Path to downloaded audio file
    """
    return audio_extractor.extract_audio_sync(video_id, quality)


async def extract_youtube_audio_async(video_id: str, quality: str = "192") -> str:
    """
    Download audio for a YouTube video (async wrapper)
    
    Args:
        video_id: YouTube video ID
        quality: Audio quality
    
    Returns:
        Path to downloaded audio file
    """
    return await audio_extractor.extract_audio(video_id, quality)


def get_youtube_video_info(video_id: str) -> Dict[str, Any]:
    """
    Get YouTube video information (sync wrapper)
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Dictionary with video metadata
    """
    return audio_extractor.get_video_info(video_id)


async def get_youtube_video_info_async(video_id: str) -> Dict[str, Any]:
    """
    Get YouTube video information (async wrapper)
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Dictionary with video metadata
    """
    return await audio_extractor.get_video_info_async(video_id)


def delete_youtube_audio(video_id: str) -> bool:
    """
    Delete downloaded audio (sync wrapper)
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        True if deleted, False otherwise
    """
    return audio_extractor.delete_audio(video_id)


async def delete_youtube_audio_async(video_id: str) -> bool:
    """
    Delete downloaded audio (async wrapper)
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        True if deleted, False otherwise
    """
    return await audio_extractor.delete_audio_async(video_id)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_video_id_from_url(url: str) -> Optional[str]:
    """
    Extract video ID from YouTube URL
    
    Args:
        url: YouTube URL
    
    Returns:
        Video ID or None
    """
    import re
    
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def validate_youtube_url(url: str) -> bool:
    """
    Validate if URL is a valid YouTube URL
    
    Args:
        url: URL to validate
    
    Returns:
        True if valid, False otherwise
    """
    return extract_video_id_from_url(url) is not None


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to HH:MM:SS
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted duration string
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"
