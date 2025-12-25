# backend/utils/decorators.py
from functools import wraps
from flask import request, g
from core.exceptions import RateLimitError, ValidationError
from config.logging_config import logger
from config.settings import settings
import time
from collections import defaultdict

# Simple in-memory rate limiter (use Redis in production)
_rate_limit_storage = defaultdict(list)

def rate_limit(max_requests: int = None):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not settings.RATE_LIMIT_ENABLED:
                return f(*args, **kwargs)
            
            limit = max_requests or settings.RATE_LIMIT_PER_MINUTE
            user_id = getattr(g, 'user_id', request.remote_addr)
            key = f"{user_id}:{request.endpoint}"
            
            now = time.time()
            minute_ago = now - 60
            
            # Clean old requests
            _rate_limit_storage[key] = [
                t for t in _rate_limit_storage[key] if t > minute_ago
            ]
            
            if len(_rate_limit_storage[key]) >= limit:
                logger.warning(f"Rate limit exceeded for {user_id} on {request.endpoint}")
                raise RateLimitError(
                    f"Rate limit exceeded. Maximum {limit} requests per minute."
                )
            
            _rate_limit_storage[key].append(now)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def validate_json(*required_fields):
    """Validate JSON request body"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                raise ValidationError("Content-Type must be application/json")
            
            data = request.get_json()
            
            if not data:
                raise ValidationError("Request body is required")
            
            missing = [field for field in required_fields if field not in data]
            
            if missing:
                raise ValidationError(
                    f"Missing required fields: {', '.join(missing)}"
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def log_execution_time(f):
    """Log function execution time"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        elapsed = time.time() - start
        
        logger.debug(f"⏱️  {f.__name__} executed in {elapsed:.3f}s")
        
        return result
    
    return decorated_function
