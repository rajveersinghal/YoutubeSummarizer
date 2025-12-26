# middleware/error_handler.py - ERROR HANDLING MIDDLEWARE

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
import time
from typing import Union

from core.exceptions import (
    SpectraAIException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError
)
from config.logging_config import logger
from config.settings import settings


# ============================================================================
# ERROR HANDLER MIDDLEWARE
# ============================================================================

async def error_handler_middleware(request: Request, call_next):
    """
    Global error handler middleware
    Catches all unhandled exceptions and returns proper JSON responses
    """
    start_time = time.time()
    
    try:
        response = await call_next(request)
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        
        # Log error with context
        logger.error(
            f"❌ Unhandled error in middleware | "
            f"Path: {request.url.path} | "
            f"Method: {request.method} | "
            f"Error: {str(e)} | "
            f"Process time: {process_time:.3f}s"
        )
        logger.error(traceback.format_exc())
        
        # Return error response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Internal Server Error",
                "message": str(e) if settings.DEBUG else "An unexpected error occurred",
                "path": request.url.path,
                "timestamp": time.time()
            }
        )


# ============================================================================
# CUSTOM EXCEPTION HANDLERS
# ============================================================================

async def custom_exception_handler(request: Request, exc: SpectraAIException):
    """Handle custom application exceptions"""
    logger.error(
        f"Custom exception: {exc.message} | "
        f"Status: {exc.status_code} | "
        f"Path: {request.url.path} | "
        f"Method: {request.method} | "
        f"Details: {exc.details}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "timestamp": time.time()
        }
    )


async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors"""
    logger.warning(
        f"Validation error: {exc.message} | "
        f"Path: {request.url.path} | "
        f"Details: {exc.details}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": "ValidationError",
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "timestamp": time.time()
        }
    )


async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors"""
    logger.warning(
        f"Authentication error: {exc.message} | "
        f"Path: {request.url.path} | "
        f"IP: {request.client.host if request.client else 'unknown'}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "success": False,
            "error": "AuthenticationError",
            "message": exc.message,
            "path": request.url.path,
            "timestamp": time.time()
        },
        headers={"WWW-Authenticate": "Bearer"}
    )


async def authorization_error_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors"""
    user_id = getattr(request.state, 'user_id', 'unknown')
    
    logger.warning(
        f"Authorization error: {exc.message} | "
        f"Path: {request.url.path} | "
        f"User: {user_id}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "success": False,
            "error": "AuthorizationError",
            "message": exc.message,
            "path": request.url.path,
            "timestamp": time.time()
        }
    )


async def not_found_error_handler(request: Request, exc: NotFoundError):
    """Handle not found errors"""
    logger.info(
        f"Not found: {exc.message} | "
        f"Path: {request.url.path}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "success": False,
            "error": "NotFoundError",
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "timestamp": time.time()
        }
    )


async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    """Handle rate limit errors"""
    logger.warning(
        f"Rate limit exceeded: {exc.message} | "
        f"Path: {request.url.path} | "
        f"IP: {request.client.host if request.client else 'unknown'}"
    )
    
    retry_after = exc.details.get("retryAfter", 60) if exc.details else 60
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "error": "RateLimitError",
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "timestamp": time.time()
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(exc.details.get("limit", "unknown")) if exc.details else "unknown",
            "X-RateLimit-Remaining": "0"
        }
    )


async def service_unavailable_error_handler(request: Request, exc: ServiceUnavailableError):
    """Handle service unavailable errors"""
    logger.error(
        f"Service unavailable: {exc.message} | "
        f"Path: {request.url.path} | "
        f"Details: {exc.details}"
    )
    
    retry_after = exc.details.get("retryAfter", 300) if exc.details else 300
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "success": False,
            "error": "ServiceUnavailableError",
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "timestamp": time.time()
        },
        headers={
            "Retry-After": str(retry_after)
        }
    )


# ============================================================================
# HTTP & VALIDATION EXCEPTION HANDLERS
# ============================================================================

async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]):
    """Handle FastAPI HTTP exceptions"""
    logger.warning(
        f"HTTP exception: {exc.status_code} | "
        f"Path: {request.url.path} | "
        f"Detail: {exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": f"HTTP{exc.status_code}",
            "message": exc.detail if exc.detail else "HTTP error occurred",
            "path": request.url.path,
            "timestamp": time.time()
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors (422)"""
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    logger.warning(
        f"Validation error: {request.url.path} | "
        f"Method: {request.method} | "
        f"Errors: {len(errors)}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "ValidationError",
            "message": "Request validation failed",
            "errors": errors,
            "path": request.url.path,
            "timestamp": time.time()
        }
    )


async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle all unexpected exceptions (500)"""
    error_traceback = traceback.format_exc()
    error_id = f"ERR-{int(time.time())}"
    
    client_host = request.client.host if request.client else 'unknown'
    
    logger.critical(
        f"Unexpected exception [{error_id}]: {str(exc)} | "
        f"Path: {request.url.path} | "
        f"Method: {request.method} | "
        f"IP: {client_host}"
    )
    logger.critical(f"Traceback [{error_id}]:\n{error_traceback}")
    
    # In debug mode, return full error details
    if settings.DEBUG:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "InternalServerError",
                "message": "Internal server error",
                "errorId": error_id,
                "exception": str(exc),
                "type": exc.__class__.__name__,
                "traceback": error_traceback.split("\n"),
                "path": request.url.path,
                "timestamp": time.time()
            }
        )
    
    # In production, hide error details
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please try again later.",
            "errorId": error_id,
            "path": request.url.path,
            "timestamp": time.time()
        }
    )


async def not_found_handler(request: Request, exc: StarletteHTTPException):
    """Handle 404 errors"""
    logger.info(f"404 Not Found: {request.url.path} | Method: {request.method}")
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "success": False,
            "error": "NotFound",
            "message": f"The requested endpoint was not found: {request.url.path}",
            "path": request.url.path,
            "method": request.method,
            "timestamp": time.time()
        }
    )


# ============================================================================
# REGISTER ALL ERROR HANDLERS
# ============================================================================

def register_error_handlers(app):
    """
    Register all error handlers with FastAPI app
    
    Usage:
        from middleware.error_handler import register_error_handlers
        
        app = FastAPI()
        register_error_handlers(app)
    """
    
    # Custom application exceptions
    app.add_exception_handler(SpectraAIException, custom_exception_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(AuthenticationError, authentication_error_handler)
    app.add_exception_handler(AuthorizationError, authorization_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(RateLimitError, rate_limit_error_handler)
    app.add_exception_handler(ServiceUnavailableError, service_unavailable_error_handler)
    
    # HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Validation errors (422)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, internal_server_error_handler)
    
    logger.info("✅ Error handlers registered")


# ============================================================================
# ERROR RESPONSE HELPERS
# ============================================================================

def create_error_response(
    message: str,
    status_code: int = 500,
    error_type: str = "Error",
    details: dict = None,
    path: str = None
) -> JSONResponse:
    """
    Create standardized error response
    
    Args:
        message: Error message
        status_code: HTTP status code
        error_type: Error type name
        details: Additional error details
        path: Request path
    
    Returns:
        JSONResponse with error details
    """
    content = {
        "success": False,
        "error": error_type,
        "message": message,
        "timestamp": time.time()
    }
    
    if details:
        content["details"] = details
    
    if path:
        content["path"] = path
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )


def create_validation_error_response(
    message: str,
    errors: list,
    path: str = None
) -> JSONResponse:
    """
    Create validation error response
    
    Args:
        message: Main error message
        errors: List of validation errors
        path: Request path
    
    Returns:
        JSONResponse with validation errors
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "ValidationError",
            "message": message,
            "errors": errors,
            "path": path,
            "timestamp": time.time()
        }
    )
