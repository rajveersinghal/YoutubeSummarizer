# backend/services/video_processor.py - VIDEO PROCESSING

from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
import re
from config.logging_config import logger

class VideoProcessor:
    """Process videos and extract transcripts"""
    
    def __init__(self):
        self.youtube_regex = r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s]+)'
    
    async def process_youtube(self, youtube_url: str, video_id: str) -> dict:
        """
        Process YouTube video and extract transcript
        
        Args:
            youtube_url: YouTube video URL
            video_id: Generated video ID
            
        Returns:
            dict with title, transcript, duration
        """
        try:
            # Extract video ID from URL
            match = re.search(self.youtube_regex, youtube_url)
            if not match:
                raise ValueError("Invalid YouTube URL")
            
            yt_video_id = match.group(1)
            
            logger.info(f"📹 Extracting YouTube video ID: {yt_video_id}")
            
            # Get video info
            try:
                yt = YouTube(youtube_url)
                title = yt.title
                duration = yt.length
            except Exception as e:
                logger.warning(f"⚠️ Could not get video info: {e}")
                title = "YouTube Video"
                duration = 0
            
            # Get transcript
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(yt_video_id)
                transcript = " ".join([entry['text'] for entry in transcript_list])
                logger.info(f"✅ Transcript extracted ({len(transcript)} chars)")
            except Exception as e:
                logger.warning(f"⚠️ Could not get transcript: {e}")
                transcript = ""
            
            return {
                "title": title,
                "transcript": transcript,
                "duration": duration,
                "youtube_video_id": yt_video_id
            }
            
        except Exception as e:
            logger.error(f"❌ YouTube processing error: {e}")
            raise
    
    async def process_video_file(self, file_path: str, video_id: str) -> dict:
        """
        Process uploaded video file
        
        Args:
            file_path: Path to video file
            video_id: Generated video ID
            
        Returns:
            dict with transcript, duration
        """
        try:
            # For now, return empty transcript
            # You can add whisper processing here later
            return {
                "transcript": "",
                "duration": 0
            }
            
        except Exception as e:
            logger.error(f"❌ Video file processing error: {e}")
            raise
