# core/middlewares.py - FASTAPI MIDDLEWARE
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import json

from config.settings import settings
from config.logging_config import logger


# ============================================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests and responses"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and log details"""
        
        start_time = time.time()
        
        # Get client details
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")[:50]
        
        # Log incoming request
        logger.info(
            f"➡️  {request.method} {request.url.path} | "
            f"IP: {client_ip} | Agent: {user_agent}"
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"❌ Request failed: {str(e)}")
            raise
        
        # Calculate duration
        duration = (time.time() - start_time) * 1000  # Convert to ms
        
        # Log response
        status_code = response.status_code
        emoji = "✅" if status_code < 400 else "❌"
        
        logger.info(
            f"{emoji} {request.method} {request.url.path} | "
            f"Status: {status_code} | Duration: {duration:.2f}ms"
        )
        
        # Add custom headers
        response.headers["X-Process-Time"] = f"{duration:.2f}ms"
        
        return response


# ============================================================================
# RATE LIMITING MIDDLEWARE
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting"""
    
    def __init__(self, app, rate_limit: int = 60):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.requests = {}  # {ip: [(timestamp, count)]}
        self.window = 60  # 60 seconds window
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Check rate limit before processing request"""
        
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get current timestamp
        current_time = time.time()
        
        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                (ts, count) for ts, count in self.requests[client_ip]
                if current_time - ts < self.window
            ]
        
        # Count requests in current window
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        request_count = sum(count for _, count in self.requests[client_ip])
        
        # Check rate limit
        if request_count >= self.rate_limit:
            logger.warning(
                f"⚠️  Rate limit exceeded for {client_ip} | "
                f"Requests: {request_count}/{self.rate_limit}"
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "message": "Rate limit exceeded",
                    "errors": {
                        "limit": self.rate_limit,
                        "window": f"{self.window} seconds",
                        "retry_after": self.window
                    }
                },
                headers={"Retry-After": str(self.window)}
            )
        
        # Add current request
        self.requests[client_ip].append((current_time, 1))
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(self.rate_limit - request_count - 1)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window))
        
        return response


# ============================================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Add security headers"""
        
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # API headers
        response.headers["X-API-Version"] = settings.APP_VERSION
        response.headers["X-Powered-By"] = settings.APP_NAME
        
        return response


# ============================================================================
# ERROR HANDLING MIDDLEWARE
# ============================================================================

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch and format all exceptions"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Handle exceptions"""
        
        try:
            return await call_next(request)
        
        except Exception as e:
            logger.error(
                f"❌ Unhandled exception: {type(e).__name__} | "
                f"Message: {str(e)} | "
                f"Path: {request.url.path}"
            )
            
            # Return generic error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "message": "Internal server error",
                    "errors": {
                        "type": type(e).__name__,
                        "detail": str(e) if settings.DEBUG else "An error occurred"
                    }
                }
            )


# ============================================================================
# REQUEST TIMEOUT MIDDLEWARE
# ============================================================================

class TimeoutMiddleware(BaseHTTPMiddleware):
    """Timeout long-running requests"""
    
    def __init__(self, app, timeout: int = 30):
        super().__init__(app)
        self.timeout = timeout
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Add timeout to requests"""
        
        import asyncio
        
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.error(
                f"⏱️  Request timeout: {request.method} {request.url.path} | "
                f"Timeout: {self.timeout}s"
            )
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "success": False,
                    "message": "Request timeout",
                    "errors": {
                        "timeout": f"{self.timeout} seconds"
                    }
                }
            )


# ============================================================================
# CLERK AUTH MIDDLEWARE (Optional)
# ============================================================================

class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Validate Clerk JWT tokens"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Validate authentication"""
        
        # Skip auth for public routes
        public_routes = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/health"
        ]
        
        if request.url.path in public_routes:
            return await call_next(request)
        
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            logger.warning(f"⚠️  No authorization header: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "message": "Authentication required",
                    "errors": {"detail": "No authorization header"}
                }
            )
        
        # Validate token (implement your Clerk validation logic)
        try:
            # TODO: Add Clerk token validation
            # token = auth_header.replace("Bearer ", "")
            # user_id = verify_clerk_token(token)
            # request.state.user_id = user_id
            
            return await call_next(request)
        
        except Exception as e:
            logger.error(f"❌ Auth validation failed: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "message": "Authentication failed",
                    "errors": {"detail": str(e)}
                }
            )


# ============================================================================
# CORS MIDDLEWARE (Configured in main.py)
# ============================================================================

def setup_cors(app):
    """Setup CORS middleware"""
    from fastapi.middleware.cors import CORSMiddleware
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
    )
