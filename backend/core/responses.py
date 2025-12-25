# backend/core/responses.py
from flask import jsonify
from typing import Any, Optional

def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200
):
    """Standard success response"""
    response = {
        "success": True,
        "message": message,
        "data": data
    }
    return jsonify(response), status_code

def error_response(
    message: str,
    status_code: int = 400,
    errors: Optional[dict] = None
):
    """Standard error response"""
    response = {
        "success": False,
        "message": message,
        "errors": errors or {}
    }
    return jsonify(response), status_code

def paginated_response(
    items: list,
    page: int,
    page_size: int,
    total_count: int,
    message: str = "Success"
):
    """Paginated response"""
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
    return jsonify(response), 200
