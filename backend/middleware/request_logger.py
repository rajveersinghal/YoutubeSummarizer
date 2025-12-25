# backend/middleware/request_logger.py
from flask import request, g
from config.logging_config import logger
import time
import json

def register_request_logger(app):
    """Register request logging middleware"""
    
    @app.before_request
    def log_request_info():
        """Log incoming request details"""
        g.start_time = time.time()
        
        logger.info(
            f"➡️  {request.method} {request.path} | "
            f"IP: {request.remote_addr} | "
            f"User-Agent: {request.user_agent.string[:50]}"
        )
        
        if request.is_json and request.method in ['POST', 'PUT', 'PATCH']:
            try:
                # Don't log sensitive data
                safe_data = {k: v for k, v in request.get_json().items() 
                            if k not in ['password', 'token', 'apiKey']}
                logger.debug(f"Request Body: {json.dumps(safe_data)}")
            except:
                pass
    
    @app.after_request
    def log_response_info(response):
        """Log response details"""
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            
            log_func = logger.info if response.status_code < 400 else logger.warning
            
            log_func(
                f"⬅️  {request.method} {request.path} | "
                f"Status: {response.status_code} | "
                f"Duration: {elapsed:.3f}s"
            )
        
        return response
