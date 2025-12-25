# # database/connection.py
# from pymongo import MongoClient
# from config.settings import settings
# from config.logging_config import logger
# import certifi

# class DatabaseConnection:
#     _instance = None
#     _client = None
#     _db = None
    
#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super(DatabaseConnection, cls).__new__(cls)
#         return cls._instance
    
#     def connect(self):
#         if self._client is not None:
#             return self._db
        
#         try:
#             logger.info(f"🔌 Connecting to MongoDB...")
            
#             # Use certifi CA bundle for SSL
#             self._client = MongoClient(
#                 settings.MONGODB_URI,
#                 serverSelectionTimeoutMS=10000,
#                 connectTimeoutMS=10000,
#                 socketTimeoutMS=10000,
#                 tls=True,
#                 tlsCAFile=certifi.where(),  # Use certifi certificates
#                 retryWrites=True,
#                 w='majority'
#             )
            
#             # Test connection
#             self._client.admin.command('ping')
#             self._db = self._client[settings.MONGODB_DB_NAME]
            
#             logger.info(f"✅ MongoDB connected successfully!")
#             logger.info(f"📊 Database: {settings.MONGODB_DB_NAME}")
#             return self._db
            
#         except Exception as e:
#             error_msg = str(e)
#             logger.error(f"❌ MongoDB connection failed: {error_msg[:100]}")
#             logger.info("ℹ️  App will continue WITHOUT database (limited functionality)")
#             logger.info("ℹ️  Features available: Video processing, Transcription, Q&A")
#             logger.info("ℹ️  Features unavailable: History, Persistent storage")
            
#             # Don't raise error, allow app to run without DB
#             self._client = None
#             self._db = None
#             return None
    
#     def get_db(self):
#         if self._db is None:
#             return self.connect()
#         return self._db
    
#     def close(self):
#         if self._client:
#             self._client.close()
#             self._client = None
#             self._db = None
#             logger.info("🔌 MongoDB connection closed")
    
#     def health_check(self):
#         try:
#             if self._client:
#                 self._client.admin.command('ping')
#                 return True
#             return False
#         except:
#             return False

# db_connection = DatabaseConnection()
# db = db_connection.get_db()


# database/connection.py
# database/connection.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config.settings import settings
from config.logging_config import logger
import sys

class DatabaseConnection:
    """MongoDB Connection Manager"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection"""
        try:
            logger.info("🔌 Connecting to MongoDB...")
            
            # Parse connection string
            if "mongodb+srv://" in settings.MONGODB_URI or "mongodb.net" in settings.MONGODB_URI:
                logger.info("☁️  Connecting to MongoDB Atlas...")
                is_atlas = True
            else:
                logger.info("🖥️  Connecting to Local MongoDB...")
                is_atlas = False
            
            # Create client
            self.client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=settings.MONGODB_SERVER_TIMEOUT,
                connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[settings.MONGODB_DB_NAME]
            
            logger.info("✅ MongoDB connected successfully!")
            logger.info(f"📊 Database: {settings.MONGODB_DB_NAME}")
            
            if is_atlas:
                logger.info("🌐 Host: MongoDB Atlas (Cloud)")
            else:
                logger.info(f"🌐 Host: Local ({settings.MONGODB_URI.split('/')[-1].split('?')[0]})")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            logger.error("Make sure MongoDB is running!")
            sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Unexpected database error: {e}")
            sys.exit(1)
    
    def health_check(self) -> bool:
        """Check if database is connected"""
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
            return False
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("🔌 MongoDB connection closed")


# Create global connection instance
db_connection = DatabaseConnection()

# ✅ ADDED: Function to get database instance
def get_db():
    """Get database instance"""
    if db_connection.db is None:
        db_connection._connect()
    return db_connection.db
