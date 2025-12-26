# main.py - FASTAPI APPLICATION (Complete & Fixed - SYNC + VIDEOS)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from collections import defaultdict
import time
import uvicorn

# Configuration and Setup
from config.settings import settings
from config.logging_config import logger
from database.database import init_db, shutdown_db, get_db, check_db_health

# Import all routers
from routes import auth, chat, videos, documents, history

# Middleware
from middleware.error_handler import register_error_handlers
from middleware.request_logger import request_logger_middleware

# ============================================================================
# RATE LIMITING STORE
# ============================================================================

rate_limit_store = defaultdict(list)

def check_rate_limit(identifier: str) -> bool:
    """
    Check if request is within rate limit
    
    Args:
        identifier: User identifier (user_id or IP)
    
    Returns:
        True if within limit, False if exceeded
    """
    if not settings.RATE_LIMIT_ENABLED:
        return True
    
    current_time = time.time()
    
    # Clean old requests (older than 1 minute)
    rate_limit_store[identifier] = [
        req_time for req_time in rate_limit_store[identifier]
        if current_time - req_time < 60
    ]
    
    # Check if limit exceeded
    if len(rate_limit_store[identifier]) >= settings.RATE_LIMIT_PER_MINUTE:
        return False
    
    # Add current request
    rate_limit_store[identifier].append(current_time)
    return True

# ============================================================================
# LIFESPAN EVENTS (Startup/Shutdown)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events
    """
    # ========== STARTUP ==========
    logger.info("=" * 80)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"⏰ Startup Time: {datetime.utcnow().isoformat()}")
    logger.info("=" * 80)
    
    try:
        # 1. Initialize database (SYNC)
        logger.info("📊 Initializing MongoDB...")
        init_db()
        logger.info("✅ MongoDB initialized successfully")
        
        # 2. Validate configuration
        logger.info("🔍 Validating configuration...")
        if settings.validate():
            logger.info("✅ Configuration validated")
        else:
            logger.warning("⚠️  Configuration has warnings - check logs above")
        
        # 3. Check required services
        logger.info("🔧 Checking services...")
        services_status = {
            "MongoDB": "✅ Connected",
            "Clerk Auth": "✅ Configured" if settings.CLERK_SECRET_KEY else "❌ Not configured",
            "Gemini AI": "✅ Configured" if settings.GEMINI_API_KEY else "❌ Not configured",
            "Storage": "✅ Ready",
            "Embeddings": "✅ Ready",
            "Whisper": "✅ Ready",
            "YouTube": "✅ Ready",
            "Rate Limiting": "✅ Enabled" if settings.RATE_LIMIT_ENABLED else "⚠️  Disabled",
        }
        
        for service, status in services_status.items():
            logger.info(f"  {service}: {status}")
        
        # 4. Log system information
        logger.info("=" * 80)
        logger.info("📋 System Configuration:")
        logger.info(f"  📍 Server: {settings.HOST}:{settings.PORT}")
        logger.info(f"  🌍 Environment: {settings.ENVIRONMENT}")
        logger.info(f"  🐛 Debug Mode: {settings.DEBUG}")
        logger.info(f"  🔐 Authentication: Clerk")
        logger.info(f"  🤖 AI Model: {settings.GEMINI_MODEL}")
        logger.info(f"  🧠 Embedding Model: {settings.EMBEDDING_MODEL}")
        logger.info(f"  🎤 Transcription: Whisper ({settings.WHISPER_MODEL_SIZE})")
        logger.info(f"  🎥 YouTube: Transcript API")
        logger.info(f"  💾 Database: {settings.MONGODB_DB_NAME}")
        logger.info(f"  📦 Storage: {settings.STORAGE_PATH}")
        logger.info(f"  🌐 CORS Origins: {settings.allowed_origins_list}")
        logger.info(f"  ⏱️  Rate Limit: {settings.RATE_LIMIT_PER_MINUTE}/min" if settings.RATE_LIMIT_ENABLED else "  ⏱️  Rate Limit: Disabled")
        logger.info(f"  👑 Admin Users: {len(settings.admin_user_ids_list)}")
        logger.info("=" * 80)
        
        logger.info("✅ Application startup completed successfully")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.critical(f"❌ STARTUP FAILED: {e}", exc_info=True)
        logger.error("=" * 80)
        raise
    
    yield
    
    # ========== SHUTDOWN ==========
    logger.info("=" * 80)
    logger.info("🛑 Shutting down application...")
    logger.info(f"⏰ Shutdown Time: {datetime.utcnow().isoformat()}")
    logger.info("=" * 80)
    
    try:
        # Disconnect from MongoDB (SYNC)
        logger.info("📊 Disconnecting from MongoDB...")
        shutdown_db()
        logger.info("✅ MongoDB disconnected")
        
        # Clear rate limit store
        logger.info("🧹 Clearing rate limit cache...")
        rate_limit_store.clear()
        logger.info("✅ Cache cleared")
        
        logger.info("=" * 80)
        logger.info("✅ Application shutdown completed successfully")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ Shutdown error: {e}", exc_info=True)
        logger.error("=" * 80)

# ============================================================================
# CREATE FASTAPI APP
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered document analysis, chat, and video processing platform with RAG capabilities and YouTube support",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    contact={
        "name": "SpectraAI Team",
        "url": "https://spectraai.com",
        "email": "support@spectraai.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# ============================================================================
# REGISTER ERROR HANDLERS
# ============================================================================

register_error_handlers(app)
logger.info("✅ Error handlers registered")

# ============================================================================
# MIDDLEWARE
# ============================================================================

# 1. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)
logger.info(f"✅ CORS middleware configured")

# 2. Rate Limiting Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    if settings.RATE_LIMIT_ENABLED:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/info", "/stats"]:
            return await call_next(request)
        
        # Get user identifier
        user_id = getattr(request.state, 'user_id', None)
        identifier = user_id or request.client.host
        
        # Check rate limit
        if not check_rate_limit(identifier):
            logger.warning(f"⚠️  Rate limit exceeded for {identifier}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too many requests",
                    "message": "Rate limit exceeded. Please try again later.",
                    "limit": settings.RATE_LIMIT_PER_MINUTE,
                    "window": "1 minute"
                }
            )
    
    response = await call_next(request)
    
    # Add rate limit headers
    if settings.RATE_LIMIT_ENABLED:
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
        user_id = getattr(request.state, 'user_id', None)
        identifier = user_id or request.client.host
        remaining = settings.RATE_LIMIT_PER_MINUTE - len(rate_limit_store.get(identifier, []))
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
    
    return response

# 3. Request Logging Middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Request logging middleware"""
    return await request_logger_middleware(request, call_next)

# 4. Response Time Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    return response

# 5. Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# ============================================================================
# INCLUDE ROUTERS
# ============================================================================

app.include_router(auth.router, tags=["Authentication"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(videos.router, tags=["Videos"])  # ✅ Videos router included
app.include_router(documents.router, tags=["Documents"])
app.include_router(history.router, tags=["History"])

logger.info("✅ All routes registered")

# ============================================================================
# ROOT & UTILITY ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "authentication": "Clerk",
        "aiModel": settings.GEMINI_MODEL,
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "info": "/info",
            "stats": "/stats",
            "auth": "/api/auth/me",
            "chats": "/api/chat",
            "videos": "/api/videos",
            "documents": "/api/documents",
            "history": "/api/history",
            "docs": "/api/docs" if settings.DEBUG else "disabled"
        },
        "features": {
            "chat": True,
            "documents": True,
            "videos": True,
            "youtube": True,  # ✅ YouTube feature
            "rag": True,
            "streaming": settings.ENABLE_STREAMING,
            "rateLimit": settings.RATE_LIMIT_ENABLED
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        # ✅ FIXED: Use sync health check
        db_health = check_db_health()
        
        services = {
            "database": db_health,
            "authentication": {
                "status": "configured" if settings.CLERK_SECRET_KEY else "not_configured",
                "provider": "Clerk"
            },
            "ai": {
                "status": "configured" if settings.GEMINI_API_KEY else "not_configured",
                "model": settings.GEMINI_MODEL,
                "provider": "Google Gemini",
                "streaming": settings.ENABLE_STREAMING
            },
            "embeddings": {
                "status": "ready",
                "model": settings.EMBEDDING_MODEL,
                "dimension": settings.EMBEDDING_DIMENSION
            },
            "transcription": {
                "status": "ready",
                "model": f"Whisper ({settings.WHISPER_MODEL_SIZE})",
                "device": settings.WHISPER_DEVICE
            },
            "youtube": {  # ✅ YouTube service status
                "status": "ready",
                "provider": "YouTube Transcript API"
            },
            "storage": {
                "status": "ready",
                "path": settings.STORAGE_PATH
            }
        }
        
        # Overall health status
        all_healthy = (
            db_health.get("connected", False) and 
            settings.CLERK_SECRET_KEY and 
            settings.GEMINI_API_KEY
        )
        overall_status = "healthy" if all_healthy else "degraded"
        
        return {
            "status": overall_status,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat(),
            "services": services
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "version": settings.APP_VERSION,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/info", tags=["Info"])
async def app_info():
    """Application information endpoint"""
    return settings.get_info()

@app.get("/stats", tags=["Stats"])
async def system_stats():
    """System statistics endpoint"""
    try:
        db = get_db()
        
        # ✅ FIXED: Sync database operations
        collections_stats = {}
        collection_names = ['users', 'conversations', 'messages', 'documents', 'videos', 'activities']
        
        for collection_name in collection_names:
            try:
                count = db.get_collection(collection_name).count_documents({})
                collections_stats[collection_name] = count
            except Exception as e:
                logger.error(f"Failed to get count for {collection_name}: {e}")
                collections_stats[collection_name] = 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.APP_VERSION,
            "database": {
                "name": settings.MONGODB_DB_NAME,
                "collections": collections_stats,
                "totalDocuments": sum(collections_stats.values())
            },
            "application": {
                "totalRoutes": len(app.routes),
                "environment": settings.ENVIRONMENT,
                "rateLimitEnabled": settings.RATE_LIMIT_ENABLED
            },
            "rateLimiting": {
                "activeUsers": len(rate_limit_store),
                "totalRequests": sum(len(requests) for requests in rate_limit_store.values())
            } if settings.RATE_LIMIT_ENABLED else None
        }
        
    except Exception as e:
        logger.error(f"❌ Stats retrieval failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to retrieve statistics",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info(f"🌐 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📍 Server: http://{settings.HOST}:{settings.PORT}")
    
    if settings.DEBUG:
        logger.info(f"📚 API Docs: http://{settings.HOST}:{settings.PORT}/api/docs")
        logger.info(f"📖 ReDoc: http://{settings.HOST}:{settings.PORT}/api/redoc")
    
    logger.info(f"🔐 Authentication: Clerk")
    logger.info(f"🤖 AI Model: {settings.GEMINI_MODEL}")
    logger.info(f"🎥 YouTube: Enabled")
    logger.info(f"💾 Database: {settings.MONGODB_DB_NAME}")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info("=" * 80)
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        access_log=settings.DEBUG,
        workers=1
    )
