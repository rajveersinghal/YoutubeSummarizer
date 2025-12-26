# database/database.py - DATABASE CONNECTION (SYNC - PyMongo)

from pymongo import MongoClient
from pymongo.database import Database as PyMongoDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config.settings import settings
from config.logging_config import logger

# ============================================================================
# SYNCHRONOUS DATABASE CONNECTION
# ============================================================================

class Database:
    """MongoDB database connection manager (synchronous with PyMongo)"""
    
    def __init__(self):
        self.client: MongoClient = None
        self.db: PyMongoDatabase = None
        self._connected = False
    
    def connect(self):
        """Connect to MongoDB"""
        if self._connected:
            logger.debug("Already connected to MongoDB")
            return
        
        try:
            logger.info(f"📡 Connecting to MongoDB...")
            logger.debug(f"URI: {settings.MONGODB_URI}")
            
            # Create MongoDB client
            self.client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=settings.MONGODB_SERVER_TIMEOUT,
                connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000
            )
            
            # Get database
            self.db = self.client[settings.MONGODB_DB_NAME]
            
            # Test connection with ping
            self.client.admin.command('ping')
            
            self._connected = True
            
            logger.info(f"✅ Connected to MongoDB: {settings.MONGODB_DB_NAME}")
            
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
        except ServerSelectionTimeoutError as e:
            logger.error(f"❌ MongoDB server selection timeout: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected MongoDB error: {e}", exc_info=True)
            raise
    
    def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            try:
                self.client.close()
                self._connected = False
                logger.info("✅ Disconnected from MongoDB")
            except Exception as e:
                logger.error(f"❌ Error disconnecting from MongoDB: {e}")
    
    def get_collection(self, collection_name: str):
        """
        Get a collection by name
        
        Args:
            collection_name: Name of the collection
        
        Returns:
            PyMongo collection object
        """
        if not self._connected or self.db is None:
            logger.warning("Database not connected, attempting to connect...")
            self.connect()
        
        return self.db[collection_name]
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        if not self._connected:
            return False
        
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            self._connected = False
            return False
    
    # ========================================================================
    # COLLECTION PROPERTIES (Easy access to common collections)
    # ========================================================================
    
    @property
    def users(self):
        """Users collection"""
        return self.get_collection("users")
    
    @property
    def conversations(self):
        """Conversations collection"""
        return self.get_collection("conversations")
    
    @property
    def messages(self):
        """Messages collection"""
        return self.get_collection("messages")
    
    @property
    def documents(self):
        """Documents collection"""
        return self.get_collection("documents")
    
    @property
    def videos(self):
        """Videos collection"""
        return self.get_collection("videos")
    
    @property
    def activities(self):
        """Activities collection"""
        return self.get_collection("activities")
    
    @property
    def searches(self):
        """Searches collection"""
        return self.get_collection("searches")
    
    @property
    def embeddings(self):
        """Embeddings collection"""
        return self.get_collection("embeddings")
    
    def __getattr__(self, name: str):
        """
        Get collection by name (fallback for dynamic access)
        
        Args:
            name: Collection name
        
        Returns:
            PyMongo collection object
        """
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        return self.get_collection(name)
    
    def __repr__(self) -> str:
        """String representation"""
        status = "connected" if self._connected else "disconnected"
        return f"<Database {settings.MONGODB_DB_NAME} ({status})>"

# ============================================================================
# GLOBAL DATABASE INSTANCE (Singleton)
# ============================================================================

_database = None

def get_db() -> Database:
    """
    Get database instance (singleton pattern)
    
    Returns:
        Database instance
    """
    global _database
    
    if _database is None:
        _database = Database()
        _database.connect()
    
    elif not _database.is_connected():
        logger.warning("Database connection lost, reconnecting...")
        _database.connect()
    
    return _database

def close_db():
    """Close database connection"""
    global _database
    
    if _database:
        _database.disconnect()
        _database = None

# ============================================================================
# STARTUP/SHUTDOWN FUNCTIONS (For FastAPI lifespan)
# ============================================================================

def init_db():
    """
    Initialize database connection
    
    Called during application startup
    """
    try:
        logger.info("🔌 Initializing database connection...")
        db = get_db()
        
        # Create indexes for better performance
        create_indexes(db)
        
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        raise

def shutdown_db():
    """
    Shutdown database connection
    
    Called during application shutdown
    """
    try:
        logger.info("🔌 Shutting down database connection...")
        close_db()
        logger.info("✅ Database shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Database shutdown failed: {e}")

def create_indexes(db: Database):
    """
    Create database indexes for better performance
    
    Args:
        db: Database instance
    """
    try:
        logger.info("📊 Creating database indexes...")
        
        # Users indexes
        db.users.create_index("user_id", unique=True)
        db.users.create_index("email")
        
        # Conversations indexes
        db.conversations.create_index("user_id")
        db.conversations.create_index("conversation_id", unique=True)
        db.conversations.create_index([("user_id", 1), ("created_at", -1)])
        
        # Messages indexes
        db.messages.create_index("conversation_id")
        db.messages.create_index([("conversation_id", 1), ("timestamp", 1)])
        
        # Documents indexes
        db.documents.create_index("user_id")
        db.documents.create_index("document_id", unique=True)
        db.documents.create_index([("user_id", 1), ("created_at", -1)])
        
        # Videos indexes
        db.videos.create_index("user_id")
        db.videos.create_index("video_id", unique=True)
        db.videos.create_index([("user_id", 1), ("created_at", -1)])
        
        # Activities indexes
        db.activities.create_index("user_id")
        db.activities.create_index([("user_id", 1), ("timestamp", -1)])
        db.activities.create_index("activity_type")
        
        # Searches indexes
        db.searches.create_index("user_id")
        db.searches.create_index([("user_id", 1), ("timestamp", -1)])
        
        logger.info("✅ Database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"⚠️ Error creating indexes (non-critical): {e}")

# ============================================================================
# HEALTH CHECK FUNCTION
# ============================================================================

def check_db_health() -> dict:
    """
    Check database health
    
    Returns:
        Dictionary with health status
    """
    try:
        db = get_db()
        
        # Ping database
        db.client.admin.command('ping')
        
        # Get server info
        server_info = db.client.server_info()
        
        # Get database stats
        stats = db.db.command("dbStats")
        
        return {
            "status": "healthy",
            "connected": True,
            "database": settings.MONGODB_DB_NAME,
            "mongodb_version": server_info.get("version"),
            "collections": stats.get("collections"),
            "data_size": stats.get("dataSize"),
            "storage_size": stats.get("storageSize")
        }
        
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }

# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "Database",
    "get_db",
    "close_db",
    "init_db",
    "shutdown_db",
    "check_db_health"
]
