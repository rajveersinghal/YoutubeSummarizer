# middleware/request_logger.py - REQUEST LOGGING MIDDLEWARE

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from config.logging_config import logger
import time
import json
from typing import Callable, Awaitable


# ============================================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests and responses"""
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and log details"""
        
        # Start timing
        start_time = time.time()
        
        # Log incoming request
        await self.log_request(request)
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error and re-raise
            duration = time.time() - start_time
            logger.error(
                f"❌ Request failed: {request.method} {request.url.path} | "
                f"Error: {str(e)} | Duration: {duration:.3f}s"
            )
            raise
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        self.log_response(request, response, duration)
        
        # Add custom headers
        response.headers["X-Process-Time"] = str(duration)
        
        return response
    
    async def log_request(self, request: Request):
        """Log incoming request details"""
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get forwarded IP if behind proxy
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Get user agent
        user_agent = request.headers.get("user-agent", "unknown")
        if len(user_agent) > 100:
            user_agent = user_agent[:100] + "..."
        
        # Get user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        user_info = f" | User: {user_id}" if user_id else ""
        
        logger.info(
            f"➡️  {request.method} {request.url.path} | "
            f"IP: {client_ip}{user_info}"
        )
        
        # Log query parameters
        if request.query_params:
            logger.debug(f"Query Params: {dict(request.query_params)}")
        
        # Log request body for POST/PUT/PATCH (excluding sensitive data)
        if request.method in ["POST", "PUT", "PATCH"]:
            await self.log_request_body(request)
    
    async def log_request_body(self, request: Request):
        """Log request body (with sensitive data redacted)"""
        try:
            content_type = request.headers.get("content-type", "")
            
            if "application/json" in content_type:
                # Read body (FastAPI will still be able to read it again)
                body_bytes = await request.body()
                
                if body_bytes:
                    try:
                        data = json.loads(body_bytes)
                        
                        # Filter sensitive fields
                        sensitive_fields = {
                            'password', 'token', 'apikey', 'api_key',
                            'secret', 'authorization', 'access_token',
                            'refresh_token', 'bearer', 'sessiontoken',
                            'session_token', 'clerk_token', 'jwt'
                        }
                        
                        safe_data = self.redact_sensitive_data(data, sensitive_fields)
                        
                        logger.debug(f"Request Body: {json.dumps(safe_data, indent=2)}")
                    except json.JSONDecodeError:
                        logger.debug("Request Body: [Invalid JSON]")
            
            elif "multipart/form-data" in content_type:
                logger.debug("Request Body: [File Upload]")
            
            elif "application/x-www-form-urlencoded" in content_type:
                logger.debug("Request Body: [Form Data]")
        
        except Exception as e:
            logger.debug(f"Could not log request body: {e}")
    
    def redact_sensitive_data(self, data: any, sensitive_fields: set) -> any:
        """Recursively redact sensitive data from dict/list"""
        if isinstance(data, dict):
            return {
                k: "***REDACTED***" if k.lower() in sensitive_fields 
                else self.redact_sensitive_data(v, sensitive_fields)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self.redact_sensitive_data(item, sensitive_fields) for item in data]
        else:
            return data
    
    def log_response(self, request: Request, response: Response, duration: float):
        """Log response details"""
        
        # Choose log level and emoji based on status code
        status_code = response.status_code
        
        if status_code < 300:
            log_func = logger.info
            emoji = "✅"
        elif status_code < 400:
            log_func = logger.info
            emoji = "↩️ "
        elif status_code < 500:
            log_func = logger.warning
            emoji = "⚠️ "
        else:
            log_func = logger.error
            emoji = "❌"
        
        # Get response size
        content_length = response.headers.get("content-length", "unknown")
        
        log_func(
            f"{emoji} {request.method} {request.url.path} | "
            f"Status: {status_code} | "
            f"Duration: {duration:.3f}s | "
            f"Size: {content_length} bytes"
        )


# ============================================================================
# SIMPLE FUNCTION-BASED REQUEST LOGGER
# ============================================================================

async def request_logger_middleware(request: Request, call_next):
    """
    Simple function-based middleware for request logging
    
    This is an alternative to the class-based middleware above.
    Use this if you prefer function-based middleware.
    """
    start_time = time.time()
    
    # Get client info
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Get user ID if authenticated
    user_id = getattr(request.state, "user_id", None)
    user_info = f" | User: {user_id}" if user_id else ""
    
    # Log request
    logger.info(
        f"➡️  {request.method} {request.url.path} | "
        f"IP: {client_ip}{user_info}"
    )
    
    # Process request
    try:
        response = await call_next(request)
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"❌ {request.method} {request.url.path} | "
            f"Error: {str(e)} | Duration: {duration:.3f}s"
        )
        raise
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Choose log level based on status code
    status_code = response.status_code
    
    if status_code < 300:
        log_func = logger.info
        emoji = "✅"
    elif status_code < 400:
        log_func = logger.info
        emoji = "↩️ "
    elif status_code < 500:
        log_func = logger.warning
        emoji = "⚠️ "
    else:
        log_func = logger.error
        emoji = "❌"
    
    # Log response
    log_func(
        f"{emoji} {request.method} {request.url.path} | "
        f"Status: {status_code} | "
        f"Duration: {duration:.3f}s"
    )
    
    # Add custom header
    response.headers["X-Process-Time"] = str(duration)
    
    return response


# ============================================================================
# SIMPLE LOG FUNCTION (For manual use in routes)
# ============================================================================

async def log_request(request: Request) -> float:
    """
    Simple function to log requests manually in routes
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(request: Request):
            start_time = await log_request(request)
            # ... your code ...
            return response
    
    Returns:
        Start time for duration calculation
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    # Get forwarded IP if behind proxy
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    user_agent = request.headers.get("user-agent", "unknown")[:50]
    
    logger.info(
        f"➡️  {request.method} {request.url.path} | "
        f"IP: {client_ip} | "
        f"User-Agent: {user_agent}"
    )
    
    return start_time


def log_response(request: Request, status_code: int, start_time: float):
    """
    Log response manually
    
    Usage:
        start_time = await log_request(request)
        # ... process request ...
        log_response(request, 200, start_time)
    """
    duration = time.time() - start_time
    
    if status_code < 400:
        log_func = logger.info
        emoji = "✅"
    elif status_code < 500:
        log_func = logger.warning
        emoji = "⚠️ "
    else:
        log_func = logger.error
        emoji = "❌"
    
    log_func(
        f"{emoji} {request.method} {request.url.path} | "
        f"Status: {status_code} | "
        f"Duration: {duration:.3f}s"
    )


# ============================================================================
# REGISTER MIDDLEWARE (Class-based)
# ============================================================================

def register_request_logger(app):
    """
    Register class-based request logging middleware with FastAPI app
    
    Usage:
        from middleware.request_logger import register_request_logger
        
        app = FastAPI()
        register_request_logger(app)
    """
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("✅ Request logging middleware registered")
