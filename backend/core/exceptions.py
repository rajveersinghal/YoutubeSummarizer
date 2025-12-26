# core/exceptions.py - CUSTOM EXCEPTIONS
from typing import Any, Dict, Optional


class SpectraAIException(Exception):
    """Base exception for all custom exceptions"""
    
    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(SpectraAIException):
    """Validation error"""
    
    def __init__(self, message: str = "Validation failed", details: Optional[Dict] = None):
        super().__init__(message, status_code=400, details=details)


class AuthenticationError(SpectraAIException):
    """Authentication error"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict] = None):
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(SpectraAIException):
    """Authorization error"""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict] = None):
        super().__init__(message, status_code=403, details=details)


class NotFoundError(SpectraAIException):
    """Resource not found error"""
    
    def __init__(self, resource: str = "Resource", resource_id: str = None, details: Optional[Dict] = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"
        
        super().__init__(message, status_code=404, details=details)


class RateLimitError(SpectraAIException):
    """Rate limit exceeded error"""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict] = None):
        super().__init__(message, status_code=429, details=details)


class ServiceUnavailableError(SpectraAIException):
    """Service unavailable error"""
    
    def __init__(self, message: str = "Service temporarily unavailable", details: Optional[Dict] = None):
        super().__init__(message, status_code=503, details=details)


class DatabaseError(SpectraAIException):
    """Database operation error"""
    
    def __init__(self, message: str = "Database error", details: Optional[Dict] = None):
        super().__init__(message, status_code=500, details=details)


class AIServiceError(SpectraAIException):
    """AI service error"""
    
    def __init__(self, message: str = "AI service error", details: Optional[Dict] = None):
        super().__init__(message, status_code=500, details=details)
