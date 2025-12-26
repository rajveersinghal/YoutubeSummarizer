# utils/validators.py - FASTAPI VERSION
import re
from typing import Optional, Set, Tuple, Any
from pathlib import Path

from fastapi import UploadFile, HTTPException, status
from pydantic import BaseModel, validator, EmailStr

from config.settings import settings
from config.logging_config import logger


# ============================================================================
# VALIDATION EXCEPTIONS
# ============================================================================

class ValidationError(HTTPException):
    """Custom validation error"""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


# ============================================================================
# URL VALIDATORS
# ============================================================================

def validate_youtube_url(url: str) -> str:
    """
    Validate and extract YouTube video ID
    
    Args:
        url: YouTube URL or video ID
    
    Returns:
        Video ID (11 characters)
    
    Raises:
        ValidationError: If URL is invalid
    """
    if not url:
        raise ValidationError("YouTube URL is required")
    
    url = url.strip()
    
    # Pattern matching for various YouTube URL formats
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([A-Za-z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([A-Za-z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([A-Za-z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([A-Za-z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([A-Za-z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:m\.)?youtube\.com\/watch\?v=([A-Za-z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            logger.debug(f"✅ Extracted video ID: {video_id}")
            return video_id
    
    # Check if it's already a video ID
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', url):
        logger.debug(f"✅ Valid video ID: {url}")
        return url
    
    raise ValidationError(
        "Invalid YouTube URL format. Supported formats: "
        "youtube.com/watch?v=..., youtu.be/..., youtube.com/shorts/..."
    )


def validate_url(url: str, schemes: Optional[Set[str]] = None) -> bool:
    """
    Validate general URL format
    
    Args:
        url: URL to validate
        schemes: Allowed schemes (default: http, https)
    
    Returns:
        True if valid
    
    Raises:
        ValidationError: If URL is invalid
    """
    if not url:
        raise ValidationError("URL is required")
    
    schemes = schemes or {'http', 'https'}
    
    # Basic URL pattern
    pattern = r'^(https?):\/\/([\w\-]+(\.[\w\-]+)+)(\/[\w\-._~:/?#[\]@!$&\'()*+,;=]*)?$'
    
    if not re.match(pattern, url, re.IGNORECASE):
        raise ValidationError("Invalid URL format")
    
    # Check scheme
    scheme = url.split('://')[0].lower()
    if scheme not in schemes:
        raise ValidationError(f"URL scheme must be one of: {', '.join(schemes)}")
    
    return True


# ============================================================================
# FILE VALIDATORS
# ============================================================================

async def validate_file_upload(
    file: UploadFile,
    allowed_extensions: Optional[Set[str]] = None,
    max_size: Optional[int] = None,
    min_size: Optional[int] = None
) -> bool:
    """
    Validate uploaded file
    
    Args:
        file: Uploaded file
        allowed_extensions: Set of allowed extensions (e.g., {'.pdf', '.txt'})
        max_size: Maximum file size in bytes
        min_size: Minimum file size in bytes
    
    Returns:
        True if valid
    
    Raises:
        ValidationError: If file is invalid
    """
    if not file or not file.filename:
        raise ValidationError("No file provided")
    
    # Check filename
    if not file.filename.strip():
        raise ValidationError("Invalid filename")
    
    # Check extension
    file_ext = Path(file.filename).suffix.lower()
    allowed = allowed_extensions or settings.ALLOWED_EXTENSIONS
    
    if file_ext not in allowed:
        raise ValidationError(
            f"File type '{file_ext}' not allowed. Allowed types: {', '.join(allowed)}"
        )
    
    # Check file size
    contents = await file.read()
    file_size = len(contents)
    
    # Reset file pointer
    await file.seek(0)
    
    # Check maximum size
    max_allowed = max_size or settings.UPLOAD_MAX_SIZE
    if file_size > max_allowed:
        max_mb = max_allowed / (1024 * 1024)
        raise ValidationError(f"File too large. Maximum size: {max_mb:.1f}MB")
    
    # Check minimum size
    if min_size and file_size < min_size:
        min_kb = min_size / 1024
        raise ValidationError(f"File too small. Minimum size: {min_kb:.1f}KB")
    
    # Check if file is empty
    if file_size == 0:
        raise ValidationError("File is empty")
    
    logger.debug(f"✅ File validation passed: {file.filename} ({file_size} bytes)")
    return True


def validate_file_extension(filename: str, allowed_extensions: Set[str]) -> bool:
    """
    Validate file extension
    
    Args:
        filename: Filename to validate
        allowed_extensions: Set of allowed extensions
    
    Returns:
        True if valid
    
    Raises:
        ValidationError: If extension is invalid
    """
    if not filename:
        raise ValidationError("Filename is required")
    
    file_ext = Path(filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise ValidationError(
            f"File extension '{file_ext}' not allowed. "
            f"Allowed: {', '.join(allowed_extensions)}"
        )
    
    return True


# ============================================================================
# PAGINATION VALIDATORS
# ============================================================================

def validate_pagination(
    page: int = 1,
    page_size: int = 20,
    max_page_size: Optional[int] = None
) -> Tuple[int, int, int]:
    """
    Validate pagination parameters
    
    Args:
        page: Page number (1-indexed)
        page_size: Items per page
        max_page_size: Maximum allowed page size
    
    Returns:
        Tuple of (page, page_size, skip)
    
    Raises:
        ValidationError: If parameters are invalid
    """
    try:
        page = int(page)
        page_size = int(page_size)
    except (TypeError, ValueError):
        raise ValidationError("Page and page_size must be integers")
    
    if page < 1:
        raise ValidationError("Page must be >= 1")
    
    max_size = max_page_size or settings.MAX_PAGE_SIZE
    
    if page_size < 1:
        raise ValidationError("Page size must be >= 1")
    
    if page_size > max_size:
        raise ValidationError(f"Page size must be <= {max_size}")
    
    # Calculate skip
    skip = (page - 1) * page_size
    
    return page, page_size, skip


def validate_limit_skip(
    limit: int = 20,
    skip: int = 0,
    max_limit: Optional[int] = None
) -> Tuple[int, int]:
    """
    Validate limit/skip parameters
    
    Args:
        limit: Maximum items to return
        skip: Number of items to skip
        max_limit: Maximum allowed limit
    
    Returns:
        Tuple of (limit, skip)
    
    Raises:
        ValidationError: If parameters are invalid
    """
    try:
        limit = int(limit)
        skip = int(skip)
    except (TypeError, ValueError):
        raise ValidationError("Limit and skip must be integers")
    
    if limit < 1:
        raise ValidationError("Limit must be >= 1")
    
    if skip < 0:
        raise ValidationError("Skip must be >= 0")
    
    max_allowed = max_limit or settings.MAX_PAGE_SIZE
    
    if limit > max_allowed:
        raise ValidationError(f"Limit must be <= {max_allowed}")
    
    return limit, skip


# ============================================================================
# STRING VALIDATORS
# ============================================================================

def validate_string(
    value: str,
    field_name: str = "Field",
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    allow_empty: bool = False
) -> str:
    """
    Validate string value
    
    Args:
        value: String to validate
        field_name: Name of field (for error messages)
        min_length: Minimum length
        max_length: Maximum length
        pattern: Regex pattern to match
        allow_empty: Allow empty strings
    
    Returns:
        Validated string
    
    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        raise ValidationError(f"{field_name} is required")
    
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    
    value = value.strip()
    
    if not allow_empty and not value:
        raise ValidationError(f"{field_name} cannot be empty")
    
    if min_length and len(value) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters")
    
    if max_length and len(value) > max_length:
        raise ValidationError(f"{field_name} must be at most {max_length} characters")
    
    if pattern and not re.match(pattern, value):
        raise ValidationError(f"{field_name} format is invalid")
    
    return value


def validate_email(email: str) -> str:
    """
    Validate email address
    
    Args:
        email: Email to validate
    
    Returns:
        Validated email
    
    Raises:
        ValidationError: If email is invalid
    """
    if not email:
        raise ValidationError("Email is required")
    
    email = email.strip().lower()
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        raise ValidationError("Invalid email format")
    
    return email


def validate_username(username: str) -> str:
    """
    Validate username
    
    Args:
        username: Username to validate
    
    Returns:
        Validated username
    
    Raises:
        ValidationError: If username is invalid
    """
    username = validate_string(
        username,
        field_name="Username",
        min_length=3,
        max_length=50
    )
    
    # Username pattern: alphanumeric, underscores, hyphens
    pattern = r'^[a-zA-Z0-9_-]+$'
    
    if not re.match(pattern, username):
        raise ValidationError(
            "Username can only contain letters, numbers, underscores, and hyphens"
        )
    
    return username


# ============================================================================
# ID VALIDATORS
# ============================================================================

def validate_id(
    id_value: str,
    field_name: str = "ID",
    pattern: Optional[str] = None
) -> str:
    """
    Validate ID format
    
    Args:
        id_value: ID to validate
        field_name: Name of ID field
        pattern: Optional regex pattern
    
    Returns:
        Validated ID
    
    Raises:
        ValidationError: If ID is invalid
    """
    if not id_value:
        raise ValidationError(f"{field_name} is required")
    
    id_value = id_value.strip()
    
    if not id_value:
        raise ValidationError(f"{field_name} cannot be empty")
    
    # Default pattern: alphanumeric, underscores, hyphens
    default_pattern = r'^[a-zA-Z0-9_-]+$'
    
    if pattern and not re.match(pattern, id_value):
        raise ValidationError(f"Invalid {field_name} format")
    elif not pattern and not re.match(default_pattern, id_value):
        raise ValidationError(f"Invalid {field_name} format")
    
    return id_value


def validate_video_id(video_id: str) -> str:
    """
    Validate YouTube video ID format
    
    Args:
        video_id: Video ID to validate
    
    Returns:
        Validated video ID
    
    Raises:
        ValidationError: If video ID is invalid
    """
    if not video_id:
        raise ValidationError("Video ID is required")
    
    video_id = video_id.strip()
    
    # YouTube video IDs are exactly 11 characters
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        raise ValidationError("Invalid video ID format (must be 11 characters)")
    
    return video_id


# ============================================================================
# NUMERIC VALIDATORS
# ============================================================================

def validate_number(
    value: Any,
    field_name: str = "Value",
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    allow_none: bool = False
) -> Optional[float]:
    """
    Validate numeric value
    
    Args:
        value: Value to validate
        field_name: Name of field
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        allow_none: Allow None values
    
    Returns:
        Validated number
    
    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if allow_none:
            return None
        raise ValidationError(f"{field_name} is required")
    
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a number")
    
    if min_value is not None and value < min_value:
        raise ValidationError(f"{field_name} must be >= {min_value}")
    
    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} must be <= {max_value}")
    
    return value


def validate_integer(
    value: Any,
    field_name: str = "Value",
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    allow_none: bool = False
) -> Optional[int]:
    """
    Validate integer value
    
    Args:
        value: Value to validate
        field_name: Name of field
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        allow_none: Allow None values
    
    Returns:
        Validated integer
    
    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if allow_none:
            return None
        raise ValidationError(f"{field_name} is required")
    
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be an integer")
    
    if min_value is not None and value < min_value:
        raise ValidationError(f"{field_name} must be >= {min_value}")
    
    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} must be <= {max_value}")
    
    return value


# ============================================================================
# DATE/TIME VALIDATORS
# ============================================================================

def validate_date_range(
    start_date: Any,
    end_date: Any,
    allow_same: bool = True
) -> Tuple[Any, Any]:
    """
    Validate date range
    
    Args:
        start_date: Start date
        end_date: End date
        allow_same: Allow start and end to be the same
    
    Returns:
        Tuple of (start_date, end_date)
    
    Raises:
        ValidationError: If date range is invalid
    """
    if start_date is None or end_date is None:
        raise ValidationError("Both start and end dates are required")
    
    if allow_same:
        if end_date < start_date:
            raise ValidationError("End date must be >= start date")
    else:
        if end_date <= start_date:
            raise ValidationError("End date must be > start date")
    
    return start_date, end_date


# ============================================================================
# COMPOSITE VALIDATORS
# ============================================================================

def validate_search_query(
    query: str,
    min_length: int = 1,
    max_length: int = 200
) -> str:
    """
    Validate search query
    
    Args:
        query: Search query
        min_length: Minimum length
        max_length: Maximum length
    
    Returns:
        Validated query
    
    Raises:
        ValidationError: If query is invalid
    """
    return validate_string(
        query,
        field_name="Search query",
        min_length=min_length,
        max_length=max_length
    )


def validate_chat_message(message: str, max_length: int = 5000) -> str:
    """
    Validate chat message
    
    Args:
        message: Message content
        max_length: Maximum length
    
    Returns:
        Validated message
    
    Raises:
        ValidationError: If message is invalid
    """
    return validate_string(
        message,
        field_name="Message",
        min_length=1,
        max_length=max_length
    )
