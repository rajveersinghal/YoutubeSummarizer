# backend/middleware/error_handler.py
from flask import jsonify, request
from werkzeug.exceptions import HTTPException
from core.exceptions import SpectraAIException
from config.logging_config import logger
import traceback

def register_error_handlers(app):
    """Register global error handlers"""
    
    @app.errorhandler(SpectraAIException)
    def handle_custom_exception(error):
        """Handle custom application exceptions"""
        logger.error(
            f"Custom exception: {error.message} | "
            f"Path: {request.path} | "
            f"Method: {request.method} | "
            f"Details: {error.details}"
        )
        
        return jsonify({
            "success": False,
            "message": error.message,
            "errors": error.details
        }), error.status_code
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle HTTP exceptions"""
        logger.warning(
            f"HTTP exception: {error.code} {error.name} | "
            f"Path: {request.path}"
        )
        
        return jsonify({
            "success": False,
            "message": error.description or "HTTP error occurred"
        }), error.code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors"""
        logger.warning(f"404 Not Found: {request.path}")
        
        return jsonify({
            "success": False,
            "message": "Endpoint not found"
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 errors"""
        logger.error(
            f"Internal server error: {str(error)} | "
            f"Path: {request.path} | "
            f"Traceback: {traceback.format_exc()}"
        )
        
        if app.debug:
            return jsonify({
                "success": False,
                "message": "Internal server error",
                "error": str(error),
                "traceback": traceback.format_exc()
            }), 500
        
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        """Handle all unexpected exceptions"""
        logger.critical(
            f"Unexpected exception: {str(error)} | "
            f"Path: {request.path} | "
            f"Method: {request.method} | "
            f"Traceback: {traceback.format_exc()}"
        )
        
        if app.debug:
            return jsonify({
                "success": False,
                "message": "An unexpected error occurred",
                "error": str(error),
                "traceback": traceback.format_exc()
            }), 500
        
        return jsonify({
            "success": False,
            "message": "An unexpected error occurred"
        }), 500
