# services/audio_extractor.py
import os
import yt_dlp
from config.settings import settings
from config.logging_config import logger

def extract_youtube_audio(video_id: str) -> str:
    try:
        audio_path = settings.AUDIO_DIR / f"{video_id}.mp3"
        
        if audio_path.exists():
            logger.info(f"Audio already exists: {audio_path}")
            return str(audio_path)
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio',  # Faster format
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',  # Lower quality = faster (was 192)
            }],
            'outtmpl': str(settings.AUDIO_DIR / f'{video_id}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'no_playlist': True,  # Prevent playlist download
            'concurrent_fragment_downloads': 4,  # Parallel downloads [web:48]
            'ffmpeg_location': r'C:\ffmpeg\bin',
        }
        
        logger.info(f"⏬ Downloading audio for {video_id}...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        logger.info(f"✅ Audio extracted: {audio_path}")
        return str(audio_path)
        
    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")
        raise
