# backend/utils/validators.py
import re
from core.exceptions import ValidationError

def validate_youtube_url(url: str) -> str:
    """Validate and extract YouTube video ID"""
    if not url:
        raise ValidationError("YouTube URL is required")
    
    url = url.strip()
    
    # Pattern matching
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([A-Za-z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([A-Za-z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([A-Za-z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([A-Za-z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Check if it's already a video ID
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', url):
        return url
    
    raise ValidationError("Invalid YouTube URL format")

def validate_file_upload(file, allowed_extensions: set = None, max_size: int = None):
    """Validate uploaded file"""
    from backend.config.settings import settings
    
    if not file or not file.filename:
        raise ValidationError("No file provided")
    
    # Check extension
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    allowed = allowed_extensions or settings.ALLOWED_EXTENSIONS
    
    if ext not in allowed:
        raise ValidationError(
            f"File type not allowed. Allowed types: {', '.join(allowed)}"
        )
    
    # Check size (if possible)
    if max_size and hasattr(file, 'content_length') and file.content_length:
        if file.content_length > (max_size or settings.UPLOAD_MAX_SIZE):
            max_mb = (max_size or settings.UPLOAD_MAX_SIZE) / (1024 * 1024)
            raise ValidationError(f"File too large. Maximum size: {max_mb}MB")
    
    return True

def validate_pagination(page: int = 1, page_size: int = 20) -> tuple:
    """Validate pagination parameters"""
    from backend.config.settings import settings
    
    try:
        page = int(page)
        page_size = int(page_size)
    except (TypeError, ValueError):
        raise ValidationError("Page and page_size must be integers")
    
    if page < 1:
        raise ValidationError("Page must be >= 1")
    
    if page_size < 1 or page_size > settings.MAX_PAGE_SIZE:
        raise ValidationError(f"Page size must be between 1 and {settings.MAX_PAGE_SIZE}")
    
    return page, page_size
