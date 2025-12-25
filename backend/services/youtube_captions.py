# services/youtube_captions.py (FIXED WITH JSON3 PARSER)
import yt_dlp
import json
import re
from config.logging_config import logger

def parse_json3_subtitles(json3_content: str) -> str:
    """
    Parse YouTube's JSON3 subtitle format
    JSON3 format: {"wireMagic": "pb3", "events": [...]}
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
        logger.error(f"Failed to parse JSON3 subtitles: {e}")
        return None

def clean_vtt_text(vtt_content: str) -> str:
    """Clean VTT subtitle format to plain text"""
    # Remove WEBVTT header
    text = re.sub(r'WEBVTT.*?\n\n', '', vtt_content, flags=re.DOTALL)
    
    # Remove timestamp lines
    text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}.*?\n', '', text)
    
    # Remove cue identifiers
    text = re.sub(r'^\d+\n', '', text, flags=re.MULTILINE)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean whitespace
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def get_youtube_captions(video_id: str) -> str:
    """
    Get captions using yt-dlp (supports VTT, JSON3, and other formats)
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        str: Transcript text or None if not available
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
            
            # Priority 1: Manual subtitles
            if 'subtitles' in info and info['subtitles']:
                for lang in ['en', 'en-US', 'en-GB', 'en-IN', 'en-CA']:
                    if lang in info['subtitles']:
                        # Get subtitle info
                        sub_info = info['subtitles'][lang][0]
                        subtitle_url = sub_info['url']
                        subtitle_ext = sub_info.get('ext', 'vtt')
                        subtitle_type = 'manual'
                        logger.info(f"✅ Found manual captions ({lang}, {subtitle_ext})")
                        break
            
            # Priority 2: Auto-generated captions
            if not subtitle_url and 'automatic_captions' in info and info['automatic_captions']:
                for lang in ['en', 'en-US', 'en-GB']:
                    if lang in info['automatic_captions']:
                        sub_info = info['automatic_captions'][lang][0]
                        subtitle_url = sub_info['url']
                        subtitle_ext = sub_info.get('ext', 'vtt')
                        subtitle_type = 'auto-generated'
                        logger.info(f"✅ Found auto-generated captions ({lang}, {subtitle_ext})")
                        break
            
            if subtitle_url:
                # Download subtitle file
                import requests
                response = requests.get(subtitle_url, timeout=10)
                response.raise_for_status()
                
                content = response.text
                
                # Parse based on format
                if subtitle_ext == 'json3' or content.strip().startswith('{'):
                    # JSON3 format (YouTube's format)
                    transcript = parse_json3_subtitles(content)
                elif subtitle_ext == 'srv3':
                    # SRV3 format (also JSON-based)
                    transcript = parse_json3_subtitles(content)
                else:
                    # VTT or SRT format
                    transcript = clean_vtt_text(content)
                
                if transcript:
                    logger.info(f"✅ Captions retrieved ({subtitle_type})! {len(transcript)} chars ⚡ INSTANT!")
                    return transcript
                else:
                    logger.warning(f"⚠️  Failed to parse {subtitle_ext} format")
                    return None
            
            logger.info(f"⚠️  No captions available for {video_id}")
            return None
    
    except Exception as e:
        logger.info(f"⚠️  Caption fetch failed for {video_id}: {str(e)[:100]}")
        return None
