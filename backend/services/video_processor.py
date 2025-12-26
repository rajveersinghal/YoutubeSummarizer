# backend/services/video_processor.py - WITH WHISPER TRANSCRIPTION

import whisper
import os
import tempfile
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi
import re
from config.logging_config import logger
from config.settings import settings

class VideoProcessor:
    """Process videos and extract transcripts using Whisper"""
    
    def __init__(self):
        self.youtube_regex = r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s]+)'
        self.whisper_model = None
    
    def _load_whisper(self):
        """Lazy load Whisper model"""
        if self.whisper_model is None:
            try:
                logger.info(f"🎤 Loading Whisper model: {settings.WHISPER_MODEL_SIZE}")
                self.whisper_model = whisper.load_model(settings.WHISPER_MODEL_SIZE)
                logger.info("✅ Whisper model loaded")
            except Exception as e:
                logger.error(f"❌ Failed to load Whisper: {e}")
                raise
        return self.whisper_model
    
    async def process_youtube(self, youtube_url: str, video_id: str) -> dict:
        """
        Process YouTube video - try transcript API first, then Whisper
        
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
            
            logger.info(f"📹 Processing YouTube video: {yt_video_id}")
            
            title = f"YouTube Video ({yt_video_id})"
            duration = 0
            transcript = ""
            
            # Try YouTube Transcript API first (faster)
            try:
                logger.info("🔍 Trying YouTube Transcript API...")
                transcript_list = YouTubeTranscriptApi.get_transcript(yt_video_id)
                transcript = " ".join([entry['text'] for entry in transcript_list])
                logger.info(f"✅ Transcript extracted via API ({len(transcript)} chars)")
            except Exception as e:
                logger.warning(f"⚠️ Transcript API failed: {e}")
                logger.info("🎤 Falling back to Whisper transcription...")
                
                # TODO: Download YouTube video and transcribe with Whisper
                # This requires yt-dlp package
                # For now, raise error
                raise ValueError("No transcript available. Whisper fallback not yet implemented for YouTube.")
            
            if not transcript:
                raise ValueError("No transcript could be extracted")
            
            return {
                "title": title,
                "transcript": transcript,
                "duration": duration,
                "youtube_video_id": yt_video_id,
                "method": "api"
            }
            
        except Exception as e:
            logger.error(f"❌ YouTube processing error: {e}")
            raise
    
    async def process_video_file(self, file_path: str, video_id: str) -> dict:
        """
        Process uploaded video file using Whisper
        
        Args:
            file_path: Path to video file
            video_id: Generated video ID
            
        Returns:
            dict with transcript, duration
        """
        try:
            logger.info(f"🎤 Transcribing video file: {file_path}")
            
            # Load Whisper model
            model = self._load_whisper()
            
            # Transcribe
            result = model.transcribe(file_path)
            
            transcript = result["text"]
            duration = result.get("duration", 0)
            
            logger.info(f"✅ Video transcribed ({len(transcript)} chars, {duration}s)")
            
            return {
                "transcript": transcript,
                "duration": duration,
                "method": "whisper"
            }
            
        except Exception as e:
            logger.error(f"❌ Video transcription error: {e}")
            raise
