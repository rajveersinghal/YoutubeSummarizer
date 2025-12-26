# core/responses.py - FASTAPI VERSION
from fastapi.responses import JSONResponse
from typing import Any, Optional, List, Dict
from pydantic import BaseModel


# ============================================================================
# PYDANTIC RESPONSE MODELS
# ============================================================================

class SuccessResponseModel(BaseModel):
    """Success response model"""
    success: bool = True
    message: str
    data: Any = None


class ErrorResponseModel(BaseModel):
    """Error response model"""
    success: bool = False
    message: str
    errors: Dict[str, Any] = {}


class PaginationModel(BaseModel):
    """Pagination metadata"""
    page: int
    pageSize: int
    totalItems: int
    totalPages: int
    hasNext: bool
    hasPrev: bool


class PaginatedResponseModel(BaseModel):
    """Paginated response model"""
    success: bool = True
    message: str
    data: Dict[str, Any]


# ============================================================================
# RESPONSE FUNCTIONS
# ============================================================================

def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200
) -> JSONResponse:
    """
    Standard success response
    
    Args:
        data: Response data (can be dict, list, string, etc.)
        message: Success message
        status_code: HTTP status code (default: 200)
    
    Returns:
        JSONResponse with success format
    
    Example:
        return success_response(
            data={"userId": "123", "name": "John"},
            message="User retrieved successfully"
        )
    """
    response = {
        "success": True,
        "message": message,
        "data": data
    }
    return JSONResponse(content=response, status_code=status_code)


def error_response(
    message: str,
    status_code: int = 400,
    errors: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Standard error response
    
    Args:
        message: Error message
        status_code: HTTP status code (default: 400)
        errors: Additional error details
    
    Returns:
        JSONResponse with error format
    
    Example:
        return error_response(
            message="Validation failed",
            status_code=400,
            errors={"email": "Invalid format"}
        )
    """
    response = {
        "success": False,
        "message": message,
        "errors": errors or {}
    }
    return JSONResponse(content=response, status_code=status_code)


def paginated_response(
    items: List[Any],
    page: int,
    page_size: int,
    total_count: int,
    message: str = "Success"
) -> JSONResponse:
    """
    Paginated response with metadata
    
    Args:
        items: List of items for current page
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_count: Total number of items
        message: Success message
    
    Returns:
        JSONResponse with pagination metadata
    
    Example:
        return paginated_response(
            items=chats,
            page=1,
            page_size=20,
            total_count=150,
            message="Chats retrieved successfully"
        )
    """
    total_pages = (total_count + page_size - 1) // page_size
    
    response = {
        "success": True,
        "message": message,
        "data": {
            "items": items,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": total_count,
                "totalPages": total_pages,
                "hasNext": page < total_pages,
                "hasPrev": page > 1
            }
        }
    }
    return JSONResponse(content=response, status_code=200)


def created_response(
    data: Any = None,
    message: str = "Created successfully",
    resource_id: Optional[str] = None
) -> JSONResponse:
    """
    Response for resource creation (201)
    
    Args:
        data: Created resource data
        message: Success message
        resource_id: ID of created resource
    
    Returns:
        JSONResponse with 201 status
    
    Example:
        return created_response(
            data={"chatId": "abc123", "title": "New Chat"},
            message="Chat created successfully",
            resource_id="abc123"
        )
    """
    response = {
        "success": True,
        "message": message,
        "data": data
    }
    
    if resource_id:
        response["resourceId"] = resource_id
    
    return JSONResponse(content=response, status_code=201)


def no_content_response() -> JSONResponse:
    """
    Empty response for successful deletion (204)
    
    Returns:
        JSONResponse with 204 status (no content)
    
    Example:
        return no_content_response()
    """
    return JSONResponse(content=None, status_code=204)


def accepted_response(
    message: str = "Request accepted",
    task_id: Optional[str] = None
) -> JSONResponse:
    """
    Response for async operations (202)
    
    Args:
        message: Acceptance message
        task_id: ID of background task
    
    Returns:
        JSONResponse with 202 status
    
    Example:
        return accepted_response(
            message="Video processing started",
            task_id="task_123"
        )
    """
    response = {
        "success": True,
        "message": message
    }
    
    if task_id:
        response["taskId"] = task_id
    
    return JSONResponse(content=response, status_code=202)


def validation_error_response(
    errors: Dict[str, str],
    message: str = "Validation failed"
) -> JSONResponse:
    """
    Response for validation errors (400)
    
    Args:
        errors: Field-level validation errors
        message: Error message
    
    Returns:
        JSONResponse with validation errors
    
    Example:
        return validation_error_response(
            errors={
                "email": "Invalid email format",
                "password": "Must be at least 8 characters"
            }
        )
    """
    return error_response(
        message=message,
        status_code=400,
        errors=errors
    )


def unauthorized_response(
    message: str = "Authentication required"
) -> JSONResponse:
    """
    Response for unauthorized access (401)
    
    Args:
        message: Error message
    
    Returns:
        JSONResponse with 401 status
    """
    return error_response(
        message=message,
        status_code=401,
        errors={"auth": "Invalid or missing authentication"}
    )


def forbidden_response(
    message: str = "Access forbidden"
) -> JSONResponse:
    """
    Response for forbidden access (403)
    
    Args:
        message: Error message
    
    Returns:
        JSONResponse with 403 status
    """
    return error_response(
        message=message,
        status_code=403,
        errors={"permission": "Insufficient permissions"}
    )


def not_found_response(
    resource: str = "Resource",
    resource_id: Optional[str] = None
) -> JSONResponse:
    """
    Response for not found resources (404)
    
    Args:
        resource: Resource type (e.g., "Chat", "User")
        resource_id: ID of resource
    
    Returns:
        JSONResponse with 404 status
    
    Example:
        return not_found_response("Chat", "abc123")
    """
    message = f"{resource} not found"
    errors = {}
    
    if resource_id:
        errors["resourceId"] = resource_id
    
    return error_response(
        message=message,
        status_code=404,
        errors=errors
    )


def rate_limit_response(
    retry_after: int = 60
) -> JSONResponse:
    """
    Response for rate limit exceeded (429)
    
    Args:
        retry_after: Seconds until rate limit resets
    
    Returns:
        JSONResponse with 429 status
    """
    return error_response(
        message="Rate limit exceeded",
        status_code=429,
        errors={
            "retryAfter": retry_after,
            "detail": f"Please try again in {retry_after} seconds"
        }
    )


def server_error_response(
    message: str = "Internal server error",
    error_detail: Optional[str] = None
) -> JSONResponse:
    """
    Response for server errors (500)
    
    Args:
        message: Error message
        error_detail: Additional error details
    
    Returns:
        JSONResponse with 500 status
    """
    errors = {}
    if error_detail:
        errors["detail"] = error_detail
    
    return error_response(
        message=message,
        status_code=500,
        errors=errors
    )


def service_unavailable_response(
    service: str = "Service"
) -> JSONResponse:
    """
    Response for unavailable external services (503)
    
    Args:
        service: Service name
    
    Returns:
        JSONResponse with 503 status
    """
    return error_response(
        message=f"{service} temporarily unavailable",
        status_code=503,
        errors={"service": service}
    )
