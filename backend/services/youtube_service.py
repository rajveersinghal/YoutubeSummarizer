# services/youtube_service.py - YOUTUBE VIDEO PROCESSING SERVICE

import re
from typing import Optional, Dict, List
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from config.logging_config import logger

class YouTubeService:
    """Service for processing YouTube videos and extracting transcripts"""
    
    def __init__(self):
        """Initialize YouTube service"""
        self.youtube_api = None
        
        # Try to initialize YouTube Data API if available
        try:
            from googleapiclient.discovery import build
            from config.settings import settings
            
            if hasattr(settings, 'YOUTUBE_API_KEY') and settings.YOUTUBE_API_KEY:
                self.youtube_api = build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)
                logger.info("✅ YouTube Data API initialized")
            else:
                logger.warning("⚠️ YouTube API key not found, metadata features will be limited")
        except ImportError:
            logger.warning("⚠️ google-api-python-client not installed, metadata features disabled")
        except Exception as e:
            logger.error(f"❌ Error initializing YouTube API: {e}")

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats
        
        Supported formats:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID
        - https://m.youtube.com/watch?v=VIDEO_ID
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video ID or None if invalid
        """
        try:
            # Remove whitespace
            url = url.strip()
            
            # Patterns for different YouTube URL formats
            patterns = [
                r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([^&\n?#]+)',
                r'youtube\.com\/watch\?.*?v=([^&\n?#]+)',
                r'youtube\.com\/shorts\/([^&\n?#]+)',
                r'youtube-nocookie\.com\/embed\/([^&\n?#]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    video_id = match.group(1)
                    logger.info(f"✅ Extracted video ID: {video_id}")
                    return video_id
            
            # If no pattern matches, check if it's already just the video ID
            if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
                logger.info(f"✅ Direct video ID provided: {url}")
                return url
            
            logger.warning(f"⚠️ Could not extract video ID from: {url}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting video ID: {e}")
            return None

    def get_transcript(self, video_id: str, languages: List[str] = None) -> Optional[str]:
        """
        Get transcript/captions for a YouTube video
        
        Args:
            video_id: YouTube video ID
            languages: List of language codes to try (default: ['en', 'en-US', 'en-GB'])
            
        Returns:
            Transcript text or None if not available
        """
        try:
            if languages is None:
                languages = ['en', 'en-US', 'en-GB', 'en-IN']
            
            logger.info(f"📝 Fetching transcript for video: {video_id}")
            
            # Try to get transcript in preferred languages
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(
                    video_id,
                    languages=languages
                )
                
                # Combine all text entries
                transcript = " ".join([entry['text'] for entry in transcript_list])
                
                # Clean up transcript
                transcript = self._clean_transcript(transcript)
                
                logger.info(f"✅ Transcript fetched: {len(transcript)} characters")
                return transcript
                
            except NoTranscriptFound:
                logger.warning(f"⚠️ No transcript in preferred languages, trying all available...")
                
                # Try to get any available transcript
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                # Get first available transcript
                for transcript_info in transcript_list:
                    try:
                        transcript_data = transcript_info.fetch()
                        transcript = " ".join([entry['text'] for entry in transcript_data])
                        transcript = self._clean_transcript(transcript)
                        
                        logger.info(f"✅ Transcript fetched in {transcript_info.language}: {len(transcript)} characters")
                        return transcript
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to fetch transcript in {transcript_info.language}: {e}")
                        continue
                
                logger.error("❌ No transcripts available for this video")
                return None
                
        except TranscriptsDisabled:
            logger.error(f"❌ Transcripts are disabled for video: {video_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching transcript: {e}")
            return None

    def _clean_transcript(self, transcript: str) -> str:
        """
        Clean and format transcript text
        
        Args:
            transcript: Raw transcript text
            
        Returns:
            Cleaned transcript
        """
        try:
            # Remove excessive whitespace
            transcript = re.sub(r'\s+', ' ', transcript)
            
            # Remove common YouTube caption artifacts
            transcript = re.sub(r'\[.*?\]', '', transcript)  # Remove [Music], [Applause], etc.
            transcript = re.sub(r'\(.*?\)', '', transcript)  # Remove (unintelligible), etc.
            
            # Fix spacing around punctuation
            transcript = re.sub(r'\s+([.,!?;:])', r'\1', transcript)
            transcript = re.sub(r'([.,!?;:])\s*', r'\1 ', transcript)
            
            # Trim
            transcript = transcript.strip()
            
            return transcript
            
        except Exception as e:
            logger.error(f"❌ Error cleaning transcript: {e}")
            return transcript

    def get_video_info(self, video_id: str) -> Optional[Dict]:
        """
        Get video metadata from YouTube Data API
        
        Requires YOUTUBE_API_KEY in settings
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with video metadata or None
        """
        try:
            if not self.youtube_api:
                logger.warning("⚠️ YouTube API not available, cannot fetch metadata")
                return None
            
            logger.info(f"📊 Fetching metadata for video: {video_id}")
            
            request = self.youtube_api.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                logger.warning(f"⚠️ No metadata found for video: {video_id}")
                return None
            
            item = response['items'][0]
            snippet = item.get('snippet', {})
            content_details = item.get('contentDetails', {})
            statistics = item.get('statistics', {})
            
            video_info = {
                "title": snippet.get('title', 'Unknown Title'),
                "description": snippet.get('description', ''),
                "channel": snippet.get('channelTitle', 'Unknown Channel'),
                "channel_id": snippet.get('channelId', ''),
                "published_at": snippet.get('publishedAt', ''),
                "duration": content_details.get('duration', ''),
                "view_count": int(statistics.get('viewCount', 0)),
                "like_count": int(statistics.get('likeCount', 0)),
                "comment_count": int(statistics.get('commentCount', 0)),
                "thumbnail_url": self._get_best_thumbnail(snippet.get('thumbnails', {})),
                "tags": snippet.get('tags', []),
                "category_id": snippet.get('categoryId', ''),
            }
            
            logger.info(f"✅ Metadata fetched: {video_info['title']}")
            return video_info
            
        except Exception as e:
            logger.error(f"❌ Error fetching video info: {e}")
            return None

    def _get_best_thumbnail(self, thumbnails: Dict) -> str:
        """
        Get the highest quality thumbnail URL
        
        Args:
            thumbnails: Thumbnails dictionary from YouTube API
            
        Returns:
            Best thumbnail URL
        """
        try:
            # Priority: maxres > high > medium > default
            for quality in ['maxres', 'high', 'medium', 'default']:
                if quality in thumbnails:
                    return thumbnails[quality]['url']
            
            return ''
            
        except Exception as e:
            logger.error(f"❌ Error getting thumbnail: {e}")
            return ''

    def format_duration(self, duration: str) -> str:
        """
        Convert ISO 8601 duration to readable format
        
        Args:
            duration: ISO 8601 duration string (e.g., 'PT1H23M45S')
            
        Returns:
            Formatted duration (e.g., '1:23:45')
        """
        try:
            # Parse ISO 8601 duration
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
            if not match:
                return duration
            
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            
            # Format
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
                
        except Exception as e:
            logger.error(f"❌ Error formatting duration: {e}")
            return duration

    def validate_video_id(self, video_id: str) -> bool:
        """
        Validate if a video ID is valid format
        
        Args:
            video_id: Video ID to validate
            
        Returns:
            True if valid format
        """
        try:
            # YouTube video IDs are 11 characters: letters, numbers, underscore, hyphen
            return bool(re.match(r'^[a-zA-Z0-9_-]{11}$', video_id))
            
        except Exception as e:
            logger.error(f"❌ Error validating video ID: {e}")
            return False

    def get_video_url(self, video_id: str) -> str:
        """
        Generate standard YouTube URL from video ID
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Full YouTube URL
        """
        return f"https://www.youtube.com/watch?v={video_id}"

    def get_embed_url(self, video_id: str) -> str:
        """
        Generate YouTube embed URL from video ID
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            YouTube embed URL
        """
        return f"https://www.youtube.com/embed/{video_id}"

    def get_thumbnail_url(self, video_id: str, quality: str = 'hqdefault') -> str:
        """
        Generate thumbnail URL from video ID
        
        Args:
            video_id: YouTube video ID
            quality: Thumbnail quality (default, mqdefault, hqdefault, sddefault, maxresdefault)
            
        Returns:
            Thumbnail URL
        """
        return f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ["YouTubeService"]
