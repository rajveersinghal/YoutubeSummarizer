# backend/core/exceptions.py
class SpectraAIException(Exception):
    """Base exception for Spectra-AI"""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class AuthenticationError(SpectraAIException):
    """Authentication failed"""
    def __init__(self, message: str = "Authentication failed", details: dict = None):
        super().__init__(message, status_code=401, details=details)

class AuthorizationError(SpectraAIException):
    """User not authorized"""
    def __init__(self, message: str = "Not authorized", details: dict = None):
        super().__init__(message, status_code=403, details=details)

class ValidationError(SpectraAIException):
    """Validation failed"""
    def __init__(self, message: str = "Validation error", details: dict = None):
        super().__init__(message, status_code=400, details=details)

class ResourceNotFoundError(SpectraAIException):
    """Resource not found"""
    def __init__(self, message: str = "Resource not found", details: dict = None):
        super().__init__(message, status_code=404, details=details)

class DatabaseError(SpectraAIException):
    """Database operation failed"""
    def __init__(self, message: str = "Database error", details: dict = None):
        super().__init__(message, status_code=500, details=details)

class ExternalServiceError(SpectraAIException):
    """External service error (AI, YouTube, etc.)"""
    def __init__(self, message: str = "External service error", details: dict = None):
        super().__init__(message, status_code=503, details=details)

class RateLimitError(SpectraAIException):
    """Rate limit exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", details: dict = None):
        super().__init__(message, status_code=429, details=details)

class FileProcessingError(SpectraAIException):
    """File processing failed"""
    def __init__(self, message: str = "File processing error", details: dict = None):
        super().__init__(message, status_code=422, details=details)
