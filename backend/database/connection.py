# database/connection.py - FASTAPI VERSION with Motor (Async MongoDB)
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Optional
import asyncio

from config.settings import settings
from config.logging_config import logger


# ============================================================================
# ASYNC DATABASE CONNECTION (Motor - Async PyMongo)
# ============================================================================

class DatabaseConnection:
    """Async MongoDB Connection Manager using Motor"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self._is_connected = False
    
    async def connect(self):
        """Establish MongoDB connection"""
        if self._is_connected and self.client is not None:
            return self.db
        
        try:
            logger.info("🔌 Connecting to MongoDB...")
            
            # Determine connection type
            is_atlas = "mongodb+srv://" in settings.MONGODB_URI or "mongodb.net" in settings.MONGODB_URI
            
            if is_atlas:
                logger.info("☁️  Connecting to MongoDB Atlas...")
            else:
                logger.info("🖥️  Connecting to Local MongoDB...")
            
            # Create async client
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=settings.MONGODB_SERVER_TIMEOUT,
                connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT,
                maxPoolSize=10,
                minPoolSize=1
            )
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[settings.MONGODB_DB_NAME]
            self._is_connected = True
            
            logger.info("✅ MongoDB connected successfully!")
            logger.info(f"📊 Database: {settings.MONGODB_DB_NAME}")
            
            if is_atlas:
                logger.info("🌐 Host: MongoDB Atlas (Cloud)")
            else:
                logger.info(f"🌐 Host: Local")
            
            return self.db
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ MongoDB connection failed: {str(e)[:200]}")
            logger.error("💡 Make sure MongoDB is running and connection string is correct!")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected database error: {str(e)[:200]}")
            raise
    
    async def disconnect(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self._is_connected = False
            logger.info("🔌 MongoDB connection closed")
    
    async def health_check(self) -> bool:
        """Check if database is connected and responsive"""
        try:
            if self.client and self._is_connected:
                await self.client.admin.command('ping')
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Database health check failed: {e}")
            return False
    
    def get_db(self):
        """Get database instance (for sync contexts)"""
        if not self._is_connected or self.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db
    
    async def get_collection(self, collection_name: str):
        """Get a specific collection"""
        if self.db is None:
            await self.connect()
        return self.db[collection_name]


# ============================================================================
# GLOBAL DATABASE INSTANCE
# ============================================================================

db_connection = DatabaseConnection()


# ============================================================================
# DEPENDENCY INJECTION FOR FASTAPI
# ============================================================================

async def get_database():
    """
    FastAPI dependency to get database instance
    
    Usage:
        @app.get("/api/chats")
        async def get_chats(db = Depends(get_database)):
            chats = await db.chats.find().to_list(100)
            return chats
    """
    if db_connection.db is None:
        await db_connection.connect()
    return db_connection.db


async def get_collection(collection_name: str):
    """
    Get a specific collection
    
    Usage:
        chats_collection = await get_collection("chats")
        chat = await chats_collection.find_one({"_id": chat_id})
    """
    db = await get_database()
    return db[collection_name]


# ============================================================================
# ALTERNATIVE: SYNC CONNECTION (If you need PyMongo instead of Motor)
# ============================================================================

class SyncDatabaseConnection:
    """Synchronous MongoDB Connection Manager using PyMongo"""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db = None
        self._is_connected = False
    
    def connect(self):
        """Establish MongoDB connection (sync)"""
        if self._is_connected and self.client is not None:
            return self.db
        
        try:
            from pymongo import MongoClient
            
            logger.info("🔌 Connecting to MongoDB (Sync)...")
            
            is_atlas = "mongodb+srv://" in settings.MONGODB_URI
            
            if is_atlas:
                logger.info("☁️  Connecting to MongoDB Atlas...")
            else:
                logger.info("🖥️  Connecting to Local MongoDB...")
            
            # Create sync client
            self.client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=settings.MONGODB_SERVER_TIMEOUT,
                connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[settings.MONGODB_DB_NAME]
            self._is_connected = True
            
            logger.info("✅ MongoDB connected successfully!")
            logger.info(f"📊 Database: {settings.MONGODB_DB_NAME}")
            
            return self.db
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self._is_connected = False
            logger.info("🔌 MongoDB connection closed")
    
    def health_check(self) -> bool:
        """Check database health"""
        try:
            if self.client and self._is_connected:
                self.client.admin.command('ping')
                return True
            return False
        except:
            return False
    
    def get_db(self):
        """Get database instance"""
        if not self._is_connected or self.db is None:
            return self.connect()
        return self.db


