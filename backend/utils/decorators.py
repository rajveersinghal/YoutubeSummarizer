# utils/decorators.py - FASTAPI VERSION
import time
import asyncio
from functools import wraps
from typing import Callable, Optional, List
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from config.logging_config import logger
from config.settings import settings


# ============================================================================
# RATE LIMITER STORAGE
# ============================================================================

# Simple in-memory rate limiter (use Redis in production)
_rate_limit_storage = defaultdict(list)
_rate_limit_lock = asyncio.Lock()


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """Rate limiting utility"""
    
    def __init__(
        self,
        max_requests: int = None,
        window_seconds: int = 60
    ):
        self.max_requests = max_requests or settings.RATE_LIMIT_PER_MINUTE
        self.window_seconds = window_seconds
        self.storage = _rate_limit_storage
    
    async def check_rate_limit(self, key: str) -> bool:
        """
        Check if request is within rate limit
        
        Args:
            key: Rate limit key (usually user_id:endpoint)
        
        Returns:
            True if within limit, False otherwise
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True
        
        async with _rate_limit_lock:
            now = time.time()
            window_start = now - self.window_seconds
            
            # Clean old requests
            self.storage[key] = [
                t for t in self.storage[key] if t > window_start
            ]
            
            # Check limit
            if len(self.storage[key]) >= self.max_requests:
                logger.warning(f"⚠️  Rate limit exceeded for key: {key}")
                return False
            
            # Add current request
            self.storage[key].append(now)
            return True
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests for key"""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        self.storage[key] = [
            t for t in self.storage[key] if t > window_start
        ]
        
        current_count = len(self.storage[key])
        return max(0, self.max_requests - current_count)
    
    def get_reset_time(self, key: str) -> Optional[float]:
        """Get time until rate limit resets"""
        if not self.storage[key]:
            return None
        
        oldest = min(self.storage[key])
        reset_time = oldest + self.window_seconds
        return reset_time


# Global rate limiter
rate_limiter = RateLimiter()


def rate_limit(max_requests: int = None, window_seconds: int = 60):
    """
    Rate limiting decorator for FastAPI routes
    
    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds
    
    Usage:
        @router.get("/api/endpoint")
        @rate_limit(max_requests=10, window_seconds=60)
        async def my_endpoint():
            ...
    """
    limiter = RateLimiter(max_requests, window_seconds)
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request = kwargs.get('request')
            if not request:
                # Try to find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                logger.warning("⚠️  Rate limiter: No request object found")
                return await func(*args, **kwargs)
            
            # Get user identifier
            user_id = getattr(request.state, 'user_id', None) or request.client.host
            endpoint = request.url.path
            key = f"{user_id}:{endpoint}"
            
            # Check rate limit
            if not await limiter.check_rate_limit(key):
                remaining = limiter.get_remaining(key)
                reset_time = limiter.get_reset_time(key)
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {limiter.max_requests} requests per {limiter.window_seconds} seconds",
                        "remaining": remaining,
                        "resetAt": reset_time
                    }
                )
            
            # Add rate limit headers to response
            response = await func(*args, **kwargs)
            
            if hasattr(response, 'headers'):
                remaining = limiter.get_remaining(key)
                response.headers['X-RateLimit-Limit'] = str(limiter.max_requests)
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Reset'] = str(int(limiter.get_reset_time(key) or 0))
            
            return response
        
        return wrapper
    return decorator


# ============================================================================
# VALIDATION DECORATORS
# ============================================================================

def validate_request(*required_fields: str):
    """
    Validate request body contains required fields
    
    Args:
        required_fields: List of required field names
    
    Usage:
        @router.post("/api/endpoint")
        @validate_request("email", "password")
        async def my_endpoint(data: dict):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to find request data
            data = None
            
            # Check kwargs for common data parameter names
            for key in ['data', 'body', 'payload', 'request_data']:
                if key in kwargs:
                    data = kwargs[key]
                    break
            
            # Check if data is a Pydantic model
            if data and hasattr(data, '__dict__'):
                data = data.__dict__
            
            if not data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request body is required"
                )
            
            # Check required fields
            missing = [field for field in required_fields if field not in data]
            
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Validation failed",
                        "message": f"Missing required fields: {', '.join(missing)}",
                        "missing_fields": missing
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_query_params(*required_params: str):
    """
    Validate query parameters
    
    Args:
        required_params: List of required parameter names
    
    Usage:
        @router.get("/api/endpoint")
        @validate_query_params("page", "limit")
        async def my_endpoint(request: Request):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                return await func(*args, **kwargs)
            
            query_params = dict(request.query_params)
            missing = [param for param in required_params if param not in query_params]
            
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Validation failed",
                        "message": f"Missing required query parameters: {', '.join(missing)}",
                        "missing_params": missing
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# EXECUTION TIME LOGGING
# ============================================================================

def log_execution_time(func: Callable):
    """
    Log function execution time
    
    Usage:
        @router.get("/api/endpoint")
        @log_execution_time
        async def my_endpoint():
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed = time.time() - start_time
            logger.info(f"⏱️  {func.__name__} executed in {elapsed:.3f}s")
    
    return wrapper


def log_execution_time_sync(func: Callable):
    """
    Log function execution time (sync version)
    
    Usage:
        @log_execution_time_sync
        def my_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.time() - start_time
            logger.info(f"⏱️  {func.__name__} executed in {elapsed:.3f}s")
    
    return wrapper


# ============================================================================
# RETRY DECORATOR
# ============================================================================

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch
    
    Usage:
        @retry(max_attempts=3, delay=1.0, backoff=2.0)
        async def my_function():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"⚠️  Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}"
                        )
                        logger.info(f"⏳ Retrying in {current_delay:.1f}s...")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"❌ All {max_attempts} attempts failed for {func.__name__}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_sync(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator for synchronous functions
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"⚠️  Attempt {attempt + 1}/{max_attempts} failed: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


# ============================================================================
# CACHE DECORATOR
# ============================================================================

_cache_storage = {}
_cache_lock = asyncio.Lock()


def cache(ttl: int = 300):
    """
    Simple cache decorator
    
    Args:
        ttl: Time to live in seconds
    
    Usage:
        @cache(ttl=300)
        async def expensive_function(param: str):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            async with _cache_lock:
                # Check cache
                if cache_key in _cache_storage:
                    cached_value, cached_time = _cache_storage[cache_key]
                    
                    if time.time() - cached_time < ttl:
                        logger.debug(f"💾 Cache hit for {func.__name__}")
                        return cached_value
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                _cache_storage[cache_key] = (result, time.time())
                logger.debug(f"💾 Cached result for {func.__name__}")
                
                return result
        
        return wrapper
    return decorator


def clear_cache():
    """Clear all cached data"""
    _cache_storage.clear()
    logger.info("🧹 Cache cleared")


# ============================================================================
# PERMISSION DECORATORS
# ============================================================================

def require_admin(func: Callable):
    """
    Require admin role
    
    Usage:
        @router.get("/api/admin/endpoint")
        @require_admin
        async def admin_endpoint(user_id: str = Depends(get_current_user)):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check if user_id is in kwargs
        user_id = kwargs.get('user_id')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Check if user is admin (you'll need to implement this)
        from models.user import get_user_by_id
        
        user = await get_user_by_id(user_id)
        
        if not user or user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return await func(*args, **kwargs)
    
    return wrapper
