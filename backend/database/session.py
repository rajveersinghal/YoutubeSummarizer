# database/session.py - FASTAPI ASYNC SESSION MANAGEMENT (ENHANCED)
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from typing import Optional, AsyncGenerator, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from config.settings import settings
from config.logging_config import logger


# ============================================================================
# DATABASE SESSION MANAGER
# ============================================================================

class DatabaseSessionManager:
    """Manage MongoDB connection lifecycle and sessions"""
    
    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._is_connected: bool = False
        self._connection_attempts: int = 0
        self._max_retries: int = 3
    
    async def connect(self) -> AsyncIOMotorDatabase:
        """Connect to MongoDB with retry logic"""
        if self._is_connected and self._client is not None:
            return self._db
        
        while self._connection_attempts < self._max_retries:
            try:
                logger.info(f"🔌 Initializing MongoDB session (attempt {self._connection_attempts + 1}/{self._max_retries})...")
                
                # Create async client
                self._client = AsyncIOMotorClient(
                    settings.MONGODB_URI,
                    serverSelectionTimeoutMS=settings.MONGODB_SERVER_TIMEOUT,
                    connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT,
                    maxPoolSize=50,
                    minPoolSize=10,
                    maxIdleTimeMS=45000,
                    retryWrites=True,
                    retryReads=True,
                    w='majority',
                    journal=True
                )
                
                # Test connection
                await self._client.admin.command('ping')
                
                # Get database
                self._db = self._client[settings.MONGODB_DB_NAME]
                self._is_connected = True
                self._connection_attempts = 0
                
                logger.info(f"✅ MongoDB session established - Database: {settings.MONGODB_DB_NAME}")
                return self._db
                
            except Exception as e:
                self._connection_attempts += 1
                logger.error(f"❌ MongoDB connection failed (attempt {self._connection_attempts}): {e}")
                
                if self._connection_attempts >= self._max_retries:
                    logger.error("❌ Max connection retries reached")
                    raise
                
                # Wait before retry
                import asyncio
                await asyncio.sleep(2 ** self._connection_attempts)
        
        raise Exception("Failed to connect to MongoDB")
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self._client:
            self._client.close()
            self._is_connected = False
            self._client = None
            self._db = None
            logger.info("🔌 MongoDB session closed")
    
    async def get_database(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if not self._is_connected or self._db is None:
            await self.connect()
        return self._db
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check database health and return detailed status
        
        Returns:
            Dictionary with health status
        """
        try:
            if self._client and self._is_connected:
                # Ping database
                start_time = datetime.utcnow()
                await self._client.admin.command('ping')
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Get server info
                server_info = await self._client.server_info()
                
                return {
                    "status": "healthy",
                    "connected": True,
                    "responseTime": response_time,
                    "mongoVersion": server_info.get('version'),
                    "database": settings.MONGODB_DB_NAME
                }
            
            return {
                "status": "unhealthy",
                "connected": False,
                "error": "Not connected"
            }
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
    
    @asynccontextmanager
    async def session(self):
        """
        Context manager for MongoDB sessions
        
        Usage:
            async with session_manager.session() as session:
                await db.collection.insert_one(doc, session=session)
        """
        if not self._is_connected:
            await self.connect()
        
        async with await self._client.start_session() as session:
            try:
                yield session
            except Exception as e:
                logger.error(f"❌ Session error: {e}")
                raise
    
    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for MongoDB transactions with automatic commit/rollback
        
        Usage:
            async with session_manager.transaction() as session:
                await db.chats.insert_one(chat, session=session)
                await db.messages.insert_many(messages, session=session)
        """
        if not self._is_connected:
            await self.connect()
        
        async with await self._client.start_session() as session:
            async with session.start_transaction():
                try:
                    yield session
                    logger.debug("✅ Transaction committed successfully")
                except Exception as e:
                    logger.error(f"❌ Transaction failed, rolling back: {e}")
                    await session.abort_transaction()
                    raise
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection information"""
        if not self._is_connected:
            return {
                "connected": False,
                "status": "disconnected"
            }
        
        return {
            "connected": True,
            "status": "connected",
            "database": settings.MONGODB_DB_NAME,
            "uri": settings.MONGODB_URI.split('@')[-1] if '@' in settings.MONGODB_URI else "localhost"
        }


# ============================================================================
# GLOBAL SESSION MANAGER INSTANCE
# ============================================================================

session_manager = DatabaseSessionManager()


# ============================================================================
# FASTAPI DEPENDENCY INJECTION
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    FastAPI dependency for database access
    
    Usage:
        @router.get("/api/items")
        async def get_items(db: AsyncIOMotorDatabase = Depends(get_db)):
            items = await db.items.find().to_list(100)
            return items
    """
    db = await session_manager.get_database()
    try:
        yield db
    finally:
        pass  # Connection is managed by session_manager


async def get_session():
    """
    FastAPI dependency for MongoDB session
    
    Usage:
        @router.post("/api/items")
        async def create_item(
            data: ItemRequest,
            session = Depends(get_session)
        ):
            await db.items.insert_one(data.dict(), session=session)
    """
    async with session_manager.session() as session:
        yield session


async def get_transaction():
    """
    FastAPI dependency for MongoDB transaction
    
    Usage:
        @router.post("/api/bulk-operation")
        async def bulk_operation(
            data: BulkRequest,
            session = Depends(get_transaction)
        ):
            await db.items.insert_one(item, session=session)
            await db.logs.insert_many(logs, session=session)
    """
    async with session_manager.transaction() as session:
        yield session


# ============================================================================
# COLLECTION HELPERS
# ============================================================================

class Collections:
    """Database collection names"""
    
    USERS = "users"
    CHATS = "chats"
    MESSAGES = "messages"
    DOCUMENTS = "documents"
    YOUTUBE_VIDEOS = "youtube_videos"
    CHUNKS = "chunks"
    EMBEDDINGS = "embeddings"
    QUERIES = "queries"
    HISTORY = "history"
    USER_CHATS = "user_chats"
    SESSIONS = "sessions"
    AUDIT_LOGS = "audit_logs"


async def get_collection(collection_name: str) -> AsyncIOMotorCollection:
    """
    Get a specific collection
    
    Usage:
        chats = await get_collection(Collections.CHATS)
        chat = await chats.find_one({"chatId": chat_id})
    """
    db = await session_manager.get_database()
    return db[collection_name]


# ============================================================================
# DATABASE INDEXES
# ============================================================================

async def ensure_indexes():
    """Create database indexes for optimal performance"""
    try:
        db = await session_manager.get_database()
        
        logger.info("📊 Creating database indexes...")
        
        # Users collection
        await db[Collections.USERS].create_index([("email", 1)], unique=True)
        await db[Collections.USERS].create_index([("username", 1)], unique=True)
        await db[Collections.USERS].create_index([("createdAt", -1)])
        
        # Chats collection
        await db[Collections.CHATS].create_index([("userId", 1), ("createdAt", -1)])
        await db[Collections.CHATS].create_index([("userId", 1), ("updatedAt", -1)])
        await db[Collections.CHATS].create_index([("chatId", 1), ("userId", 1)], unique=True)
        await db[Collections.CHATS].create_index([("isDeleted", 1)])
        await db[Collections.CHATS].create_index([("mode", 1)])
        
        # Messages collection
        await db[Collections.MESSAGES].create_index([("chatId", 1), ("createdAt", 1)])
        await db[Collections.MESSAGES].create_index([("userId", 1), ("createdAt", -1)])
        await db[Collections.MESSAGES].create_index([("messageId", 1)])
        
        # Documents collection
        await db[Collections.DOCUMENTS].create_index([("userId", 1), ("uploadedAt", -1)])
        await db[Collections.DOCUMENTS].create_index([("userId", 1), ("fileName", 1)])
        await db[Collections.DOCUMENTS].create_index([("documentId", 1), ("userId", 1)], unique=True)
        await db[Collections.DOCUMENTS].create_index([("processingStatus", 1)])
        
        # YouTube videos collection
        await db[Collections.YOUTUBE_VIDEOS].create_index([("userId", 1), ("createdAt", -1)])
        await db[Collections.YOUTUBE_VIDEOS].create_index([("videoId", 1), ("userId", 1)], unique=True)
        await db[Collections.YOUTUBE_VIDEOS].create_index([("embeddingStatus", 1)])
        
        # Chunks collection (ENHANCED)
        await db[Collections.CHUNKS].create_index([("videoId", 1), ("chunkIndex", 1)])
        await db[Collections.CHUNKS].create_index([("documentId", 1), ("chunkIndex", 1)])
        await db[Collections.CHUNKS].create_index([("userId", 1), ("createdAt", -1)])
        await db[Collections.CHUNKS].create_index([("videoId", 1)])
        await db[Collections.CHUNKS].create_index([("documentId", 1)])
        
        # Text search index for chunks
        try:
            await db[Collections.CHUNKS].create_index([("text", "text")])
            logger.info("✅ Text search index created for chunks")
        except Exception as e:
            logger.debug(f"Text index exists or creation skipped: {e}")
        
        # Embeddings collection
        await db[Collections.EMBEDDINGS].create_index([("videoId", 1)])
        await db[Collections.EMBEDDINGS].create_index([("documentId", 1)])
        await db[Collections.EMBEDDINGS].create_index([("userId", 1)])
        await db[Collections.EMBEDDINGS].create_index([("chunkId", 1)])
        
        # Queries collection
        await db[Collections.QUERIES].create_index([("userId", 1), ("createdAt", -1)])
        await db[Collections.QUERIES].create_index([("videoId", 1)])
        await db[Collections.QUERIES].create_index([("chatId", 1)])
        
        # History collection
        await db[Collections.HISTORY].create_index([("userId", 1), ("createdAt", -1)])
        await db[Collections.HISTORY].create_index([("action", 1)])
        await db[Collections.HISTORY].create_index([("resourceType", 1)])
        await db[Collections.HISTORY].create_index([("resourceId", 1)])
        
        # User chats collection
        await db[Collections.USER_CHATS].create_index([("userId", 1), ("lastMessageAt", -1)])
        await db[Collections.USER_CHATS].create_index([("chatId", 1), ("userId", 1)], unique=True)
        
        # Sessions collection
        await db[Collections.SESSIONS].create_index([("userId", 1)])
        await db[Collections.SESSIONS].create_index([("token", 1)], unique=True)
        await db[Collections.SESSIONS].create_index([("expiresAt", 1)], expireAfterSeconds=0)
        
        # Audit logs collection
        await db[Collections.AUDIT_LOGS].create_index([("userId", 1), ("timestamp", -1)])
        await db[Collections.AUDIT_LOGS].create_index([("action", 1), ("timestamp", -1)])
        await db[Collections.AUDIT_LOGS].create_index([("timestamp", 1)], expireAfterSeconds=2592000)  # 30 days
        
        logger.info("✅ Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to create indexes: {e}")
        raise


# ============================================================================
# DATABASE UTILITIES
# ============================================================================

async def drop_database():
    """Drop entire database (USE WITH CAUTION!)"""
    try:
        db = await session_manager.get_database()
        await session_manager._client.drop_database(settings.MONGODB_DB_NAME)
        logger.warning(f"⚠️  Database '{settings.MONGODB_DB_NAME}' dropped!")
    except Exception as e:
        logger.error(f"❌ Failed to drop database: {e}")
        raise


async def get_database_stats() -> Dict[str, Any]:
    """Get database statistics"""
    try:
        db = await session_manager.get_database()
        stats = await db.command("dbStats")
        
        return {
            "database": stats.get("db"),
            "collections": stats.get("collections"),
            "dataSize": stats.get("dataSize"),
            "storageSize": stats.get("storageSize"),
            "indexes": stats.get("indexes"),
            "indexSize": stats.get("indexSize"),
            "objects": stats.get("objects"),
            "avgObjSize": stats.get("avgObjSize"),
            "dataSizeMB": round(stats.get("dataSize", 0) / (1024 * 1024), 2),
            "storageSizeMB": round(stats.get("storageSize", 0) / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.error(f"❌ Failed to get database stats: {e}")
        return {}


async def get_collection_stats(collection_name: str) -> Dict[str, Any]:
    """Get collection statistics"""
    try:
        db = await session_manager.get_database()
        stats = await db.command("collStats", collection_name)
        
        return {
            "collection": stats.get("ns"),
            "count": stats.get("count"),
            "size": stats.get("size"),
            "storageSize": stats.get("storageSize"),
            "totalIndexSize": stats.get("totalIndexSize"),
            "avgObjSize": stats.get("avgObjSize"),
            "sizeMB": round(stats.get("size", 0) / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.error(f"❌ Failed to get collection stats: {e}")
        return {}


async def get_all_collections() -> List[str]:
    """Get list of all collections in database"""
    try:
        db = await session_manager.get_database()
        collections = await db.list_collection_names()
        return collections
    except Exception as e:
        logger.error(f"❌ Failed to get collections: {e}")
        return []


async def drop_collection(collection_name: str):
    """Drop a specific collection (USE WITH CAUTION!)"""
    try:
        db = await session_manager.get_database()
        await db[collection_name].drop()
        logger.warning(f"⚠️  Collection '{collection_name}' dropped!")
    except Exception as e:
        logger.error(f"❌ Failed to drop collection: {e}")
        raise


# ============================================================================
# TRANSACTION HELPERS
# ============================================================================

@asynccontextmanager
async def atomic_transaction():
    """
    Standalone transaction context manager
    
    Usage:
        async with atomic_transaction() as session:
            await db.chats.insert_one(chat, session=session)
            await db.messages.insert_many(messages, session=session)
    """
    async with session_manager.transaction() as session:
        yield session


async def execute_in_transaction(operations: List):
    """
    Execute multiple operations in a single transaction
    
    Args:
        operations: List of async functions to execute
    
    Usage:
        await execute_in_transaction([
            lambda s: db.chats.insert_one(chat, session=s),
            lambda s: db.messages.insert_many(messages, session=s)
        ])
    """
    async with session_manager.transaction() as session:
        for operation in operations:
            await operation(session)


# ============================================================================
# CLEANUP UTILITIES
# ============================================================================

async def cleanup_old_sessions(days: int = 30) -> int:
    """Remove expired sessions older than specified days"""
    try:
        db = await session_manager.get_database()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await db[Collections.SESSIONS].delete_many({
            "expiresAt": {"$lt": cutoff_date}
        })
        
        count = result.deleted_count
        logger.info(f"🧹 Cleaned up {count} expired sessions")
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to cleanup sessions: {e}")
        return 0


async def cleanup_deleted_chats(days: int = 90) -> int:
    """Permanently remove soft-deleted chats older than specified days"""
    try:
        db = await session_manager.get_database()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await db[Collections.CHATS].delete_many({
            "isDeleted": True,
            "deletedAt": {"$lt": cutoff_date}
        })
        
        count = result.deleted_count
        logger.info(f"🧹 Permanently deleted {count} old chats")
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to cleanup chats: {e}")
        return 0


async def cleanup_orphaned_chunks() -> int:
    """Remove chunks that don't have associated videos or documents"""
    try:
        db = await session_manager.get_database()
        
        # Get all unique video IDs and document IDs from chunks
        video_ids_in_chunks = await db[Collections.CHUNKS].distinct("videoId", {"videoId": {"$ne": None}})
        doc_ids_in_chunks = await db[Collections.CHUNKS].distinct("documentId", {"documentId": {"$ne": None}})
        
        # Get all video IDs and document IDs
        video_ids_in_videos = await db[Collections.YOUTUBE_VIDEOS].distinct("videoId")
        doc_ids_in_docs = await db[Collections.DOCUMENTS].distinct("documentId")
        
        # Find orphaned chunks
        orphaned_video_ids = set(video_ids_in_chunks) - set(video_ids_in_videos)
        orphaned_doc_ids = set(doc_ids_in_chunks) - set(doc_ids_in_docs)
        
        total_deleted = 0
        
        if orphaned_video_ids:
            result = await db[Collections.CHUNKS].delete_many({
                "videoId": {"$in": list(orphaned_video_ids)}
            })
            total_deleted += result.deleted_count
        
        if orphaned_doc_ids:
            result = await db[Collections.CHUNKS].delete_many({
                "documentId": {"$in": list(orphaned_doc_ids)}
            })
            total_deleted += result.deleted_count
        
        if total_deleted > 0:
            logger.info(f"🧹 Removed {total_deleted} orphaned chunks")
        else:
            logger.info("✅ No orphaned chunks found")
        
        return total_deleted
        
    except Exception as e:
        logger.error(f"❌ Failed to cleanup orphaned chunks: {e}")
        return 0


async def cleanup_old_history(days: int = 180) -> int:
    """Remove history entries older than specified days"""
    try:
        db = await session_manager.get_database()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await db[Collections.HISTORY].delete_many({
            "createdAt": {"$lt": cutoff_date}
        })
        
        count = result.deleted_count
        logger.info(f"🧹 Cleaned up {count} old history entries")
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to cleanup history: {e}")
        return 0


async def run_all_cleanups() -> Dict[str, int]:
    """Run all cleanup operations"""
    results = {
        "sessions": await cleanup_old_sessions(),
        "chats": await cleanup_deleted_chats(),
        "chunks": await cleanup_orphaned_chunks(),
        "history": await cleanup_old_history()
    }
    
    total = sum(results.values())
    logger.info(f"🧹 Total cleanup: {total} items removed")
    
    return results
