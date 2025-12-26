# services/youtube_captions.py - FASTAPI ASYNC VERSION
import asyncio
import json
import re
from typing import Optional, Dict, Any, List
import yt_dlp
import requests

from config.logging_config import logger


# ============================================================================
# SUBTITLE PARSERS
# ============================================================================

def parse_json3_subtitles(json3_content: str) -> Optional[str]:
    """
    Parse YouTube's JSON3 subtitle format
    JSON3 format: {"wireMagic": "pb3", "events": [...]}
    
    Args:
        json3_content: JSON3 format subtitle content
    
    Returns:
        Plain text transcript or None
    """
    try:
        data = json.loads(json3_content)
        
        if 'events' not in data:
            return None
        
        text_parts = []
        
        for event in data['events']:
            if 'segs' in event:
                # Extract text segments
                for seg in event['segs']:
                    if 'utf8' in seg:
                        text_parts.append(seg['utf8'])
        
        # Combine all text
        full_text = ' '.join(text_parts)
        
        # Clean up whitespace
        full_text = re.sub(r'\s+', ' ', full_text)
        full_text = re.sub(r'\n+', ' ', full_text)
        
        return full_text.strip()
        
    except Exception as e:
        logger.error(f"❌ Failed to parse JSON3 subtitles: {e}")
        return None


def parse_srv3_subtitles(srv3_content: str) -> Optional[str]:
    """
    Parse YouTube's SRV3 subtitle format (also JSON-based)
    
    Args:
        srv3_content: SRV3 format subtitle content
    
    Returns:
        Plain text transcript or None
    """
    try:
        # SRV3 is similar to JSON3
        return parse_json3_subtitles(srv3_content)
        
    except Exception as e:
        logger.error(f"❌ Failed to parse SRV3 subtitles: {e}")
        return None


def clean_vtt_text(vtt_content: str) -> str:
    """
    Clean VTT subtitle format to plain text
    
    Args:
        vtt_content: VTT format subtitle content
    
    Returns:
        Plain text transcript
    """
    try:
        # Remove WEBVTT header
        text = re.sub(r'WEBVTT.*?\n\n', '', vtt_content, flags=re.DOTALL)
        
        # Remove timestamp lines
        text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}.*?\n', '', text)
        
        # Remove cue identifiers
        text = re.sub(r'^\d+\n', '', text, flags=re.MULTILINE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove position/styling tags
        text = re.sub(r'\{[^}]+\}', '', text)
        
        # Clean whitespace
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
        
    except Exception as e:
        logger.error(f"❌ Failed to clean VTT text: {e}")
        return vtt_content


def clean_srt_text(srt_content: str) -> str:
    """
    Clean SRT subtitle format to plain text
    
    Args:
        srt_content: SRT format subtitle content
    
    Returns:
        Plain text transcript
    """
    try:
        # Remove subtitle numbers
        text = re.sub(r'^\d+\n', '', srt_content, flags=re.MULTILINE)
        
        # Remove timestamps
        text = re.sub(r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\n', '', text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean whitespace
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
        
    except Exception as e:
        logger.error(f"❌ Failed to clean SRT text: {e}")
        return srt_content


# ============================================================================
# YOUTUBE CAPTIONS SERVICE
# ============================================================================

class YouTubeCaptionsService:
    """Service for fetching YouTube captions"""
    
    def __init__(self):
        self.preferred_languages = ['en', 'en-US', 'en-GB', 'en-IN', 'en-CA']
    
    def get_captions_sync(
        self,
        video_id: str,
        prefer_manual: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get captions using yt-dlp (synchronous)
        
        Args:
            video_id: YouTube video ID
            prefer_manual: Prefer manual captions over auto-generated
        
        Returns:
            Dictionary with transcript and metadata, or None
        """
        try:
            logger.info(f"📝 Fetching captions with yt-dlp: {video_id}")
            
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                subtitle_url = None
                subtitle_ext = None
                subtitle_type = None
                subtitle_lang = None
                
                # Priority 1: Manual subtitles (if preferred)
                if prefer_manual and 'subtitles' in info and info['subtitles']:
                    for lang in self.preferred_languages:
                        if lang in info['subtitles']:
                            sub_info = info['subtitles'][lang][0]
                            subtitle_url = sub_info['url']
                            subtitle_ext = sub_info.get('ext', 'vtt')
                            subtitle_type = 'manual'
                            subtitle_lang = lang
                            logger.info(f"✅ Found manual captions ({lang}, {subtitle_ext})")
                            break
                
                # Priority 2: Auto-generated captions
                if not subtitle_url and 'automatic_captions' in info and info['automatic_captions']:
                    for lang in self.preferred_languages:
                        if lang in info['automatic_captions']:
                            sub_info = info['automatic_captions'][lang][0]
                            subtitle_url = sub_info['url']
                            subtitle_ext = sub_info.get('ext', 'vtt')
                            subtitle_type = 'auto-generated'
                            subtitle_lang = lang
                            logger.info(f"✅ Found auto-generated captions ({lang}, {subtitle_ext})")
                            break
                
                # Priority 3: Manual subtitles (if auto-generated not found)
                if not subtitle_url and not prefer_manual and 'subtitles' in info and info['subtitles']:
                    for lang in self.preferred_languages:
                        if lang in info['subtitles']:
                            sub_info = info['subtitles'][lang][0]
                            subtitle_url = sub_info['url']
                            subtitle_ext = sub_info.get('ext', 'vtt')
                            subtitle_type = 'manual'
                            subtitle_lang = lang
                            logger.info(f"✅ Found manual captions ({lang}, {subtitle_ext})")
                            break
                
                if subtitle_url:
                    # Download subtitle file
                    response = requests.get(subtitle_url, timeout=10)
                    response.raise_for_status()
                    
                    content = response.text
                    
                    # Parse based on format
                    transcript = None
                    
                    if subtitle_ext == 'json3' or (content.strip().startswith('{') and 'events' in content):
                        # JSON3 format
                        transcript = parse_json3_subtitles(content)
                    elif subtitle_ext == 'srv3':
                        # SRV3 format
                        transcript = parse_srv3_subtitles(content)
                    elif subtitle_ext == 'srt' or 'SubRip' in content[:100]:
                        # SRT format
                        transcript = clean_srt_text(content)
                    else:
                        # VTT format (default)
                        transcript = clean_vtt_text(content)
                    
                    if transcript:
                        logger.info(f"✅ Captions retrieved ({subtitle_type})! {len(transcript)} chars ⚡ INSTANT!")
                        
                        return {
                            'transcript': transcript,
                            'type': subtitle_type,
                            'language': subtitle_lang,
                            'format': subtitle_ext,
                            'length': len(transcript)
                        }
                    else:
                        logger.warning(f"⚠️  Failed to parse {subtitle_ext} format")
                        return None
                
                logger.info(f"⚠️  No captions available for {video_id}")
                return None
        
        except Exception as e:
            logger.info(f"⚠️  Caption fetch failed for {video_id}: {str(e)[:100]}")
            return None
    
    async def get_captions(
        self,
        video_id: str,
        prefer_manual: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get captions using yt-dlp (async)
        
        Args:
            video_id: YouTube video ID
            prefer_manual: Prefer manual captions over auto-generated
        
        Returns:
            Dictionary with transcript and metadata, or None
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.get_captions_sync,
                video_id,
                prefer_manual
            )
            return result
            
        except Exception as e:
            logger.error(f"❌ Async caption fetch failed: {e}")
            return None
    
    def get_available_captions_sync(self, video_id: str) -> Dict[str, List[str]]:
        """
        Get list of available caption languages (synchronous)
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Dictionary with manual and auto-generated caption languages
        """
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            ydl_opts = {
                'skip_download': True,
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                manual_langs = list(info.get('subtitles', {}).keys())
                auto_langs = list(info.get('automatic_captions', {}).keys())
                
                return {
                    'manual': manual_langs,
                    'auto_generated': auto_langs
                }
        
        except Exception as e:
            logger.error(f"❌ Failed to get available captions: {e}")
            return {'manual': [], 'auto_generated': []}
    
    async def get_available_captions(self, video_id: str) -> Dict[str, List[str]]:
        """
        Get list of available caption languages (async)
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Dictionary with manual and auto-generated caption languages
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.get_available_captions_sync,
                video_id
            )
            return result
            
        except Exception as e:
            logger.error(f"❌ Async get available captions failed: {e}")
            return {'manual': [], 'auto_generated': []}


# ============================================================================
# GLOBAL SERVICE INSTANCE
# ============================================================================

youtube_captions_service = YouTubeCaptionsService()


# ============================================================================
# CONVENIENCE FUNCTIONS (Backward Compatibility)
# ============================================================================

def get_youtube_captions(video_id: str) -> Optional[str]:
    """
    Get captions using yt-dlp (backward compatibility)
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Transcript text or None
    """
    result = youtube_captions_service.get_captions_sync(video_id)
    return result['transcript'] if result else None


async def get_youtube_captions_async(
    video_id: str,
    prefer_manual: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Get captions with metadata (async wrapper)
    
    Args:
        video_id: YouTube video ID
        prefer_manual: Prefer manual captions
    
    Returns:
        Dictionary with transcript and metadata, or None
    """
    return await youtube_captions_service.get_captions(video_id, prefer_manual)


async def get_available_captions_async(video_id: str) -> Dict[str, List[str]]:
    """
    Get available caption languages (async wrapper)
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Dictionary with caption languages
    """
    return await youtube_captions_service.get_available_captions(video_id)
