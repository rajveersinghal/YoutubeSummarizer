# models/user.py - FASTAPI ASYNC VERSION
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, EmailStr
import uuid

from database.session import get_db, Collections
from config.logging_config import logger


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UserModel(BaseModel):
    """User document model"""
    userId: str = Field(default_factory=lambda: f"user_{str(uuid.uuid4())[:8]}")
    clerkId: str = Field(..., description="Clerk authentication ID")
    email: EmailStr = Field(..., description="User email")
    firstName: Optional[str] = Field(None, max_length=100)
    lastName: Optional[str] = Field(None, max_length=100)
    username: Optional[str] = Field(None, max_length=50)
    profileImage: Optional[str] = Field(None, description="Profile image URL")
    role: str = Field(default="user", description="User role: user/admin/premium")
    isActive: bool = Field(default=True)
    isVerified: bool = Field(default=False)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    lastLoginAt: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "userId": "user_abc123",
                "clerkId": "clerk_xyz789",
                "email": "user@example.com",
                "firstName": "John",
                "lastName": "Doe",
                "username": "johndoe",
                "profileImage": "https://example.com/avatar.jpg",
                "role": "user",
                "isActive": True,
                "isVerified": True,
                "preferences": {
                    "theme": "dark",
                    "language": "en"
                },
                "metadata": {
                    "plan": "free"
                },
                "createdAt": "2025-12-25T17:00:00Z",
                "updatedAt": "2025-12-25T17:00:00Z",
                "lastLoginAt": "2025-12-25T17:00:00Z"
            }
        }


class CreateUserRequest(BaseModel):
    """Request model for creating a user"""
    clerkId: str = Field(..., min_length=1)
    email: EmailStr
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    username: Optional[str] = None
    profileImage: Optional[str] = None


class UpdateUserRequest(BaseModel):
    """Request model for updating a user"""
    firstName: Optional[str] = Field(None, max_length=100)
    lastName: Optional[str] = Field(None, max_length=100)
    username: Optional[str] = Field(None, max_length=50)
    profileImage: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class UserStatsModel(BaseModel):
    """User statistics model"""
    totalChats: int
    totalQueries: int
    totalVideosProcessed: int
    totalDocuments: int
    accountAge: int  # days
    lastActive: Optional[datetime]


# ============================================================================
# USER DATABASE OPERATIONS (Async)
# ============================================================================

async def create_user(
    clerk_id: str,
    email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    username: Optional[str] = None,
    profile_image: Optional[str] = None
) -> str:
    """
    Create a new user
    
    Args:
        clerk_id: Clerk authentication ID
        email: User email
        first_name: First name
        last_name: Last name
        username: Username
        profile_image: Profile image URL
    
    Returns:
        user_id: ID of created user
    """
    try:
        db = await get_db()
        
        # Check if user already exists
        existing = await db[Collections.USERS].find_one({
            '$or': [
                {'clerkId': clerk_id},
                {'email': email}
            ]
        })
        
        if existing:
            logger.warning(f"⚠️  User already exists: {clerk_id}")
            return existing['userId']
        
        # Generate user ID
        user_id = f"user_{str(uuid.uuid4())[:8]}"
        
        # Create user document
        user_doc = {
            'userId': user_id,
            'clerkId': clerk_id,
            'email': email,
            'firstName': first_name,
            'lastName': last_name,
            'username': username or email.split('@')[0],
            'profileImage': profile_image,
            'role': 'user',
            'isActive': True,
            'isVerified': False,
            'preferences': {
                'theme': 'light',
                'language': 'en',
                'notifications': True
            },
            'metadata': {
                'plan': 'free',
                'usage': {
                    'chats': 0,
                    'queries': 0,
                    'videos': 0,
                    'documents': 0
                }
            },
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow(),
            'lastLoginAt': datetime.utcnow()
        }
        
        await db[Collections.USERS].insert_one(user_doc)
        
        logger.info(f"✅ Created user {user_id} ({email})")
        return user_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create user: {e}")
        raise


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user by user ID
    
    Args:
        user_id: User ID
    
    Returns:
        User document or None
    """
    try:
        db = await get_db()
        
        user = await db[Collections.USERS].find_one(
            {'userId': user_id},
            {'_id': 0}
        )
        
        return user
        
    except Exception as e:
        logger.error(f"❌ Failed to get user {user_id}: {e}")
        return None


async def get_user_by_clerk_id(clerk_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user by Clerk ID
    
    Args:
        clerk_id: Clerk authentication ID
    
    Returns:
        User document or None
    """
    try:
        db = await get_db()
        
        user = await db[Collections.USERS].find_one(
            {'clerkId': clerk_id},
            {'_id': 0}
        )
        
        return user
        
    except Exception as e:
        logger.error(f"❌ Failed to get user by Clerk ID {clerk_id}: {e}")
        return None


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email
    
    Args:
        email: User email
    
    Returns:
        User document or None
    """
    try:
        db = await get_db()
        
        user = await db[Collections.USERS].find_one(
            {'email': email},
            {'_id': 0}
        )
        
        return user
        
    except Exception as e:
        logger.error(f"❌ Failed to get user by email {email}: {e}")
        return None


async def update_user(
    user_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    username: Optional[str] = None,
    profile_image: Optional[str] = None,
    preferences: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Update user information
    
    Args:
        user_id: User ID
        first_name: First name
        last_name: Last name
        username: Username
        profile_image: Profile image URL
        preferences: User preferences
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        update_fields = {'updatedAt': datetime.utcnow()}
        
        if first_name is not None:
            update_fields['firstName'] = first_name
        
        if last_name is not None:
            update_fields['lastName'] = last_name
        
        if username is not None:
            update_fields['username'] = username
        
        if profile_image is not None:
            update_fields['profileImage'] = profile_image
        
        if preferences is not None:
            update_fields['preferences'] = preferences
        
        result = await db[Collections.USERS].update_one(
            {'userId': user_id},
            {'$set': update_fields}
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Updated user {user_id}")
            return True
        
        logger.warning(f"⚠️  User {user_id} not found or not modified")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to update user {user_id}: {e}")
        raise


async def update_user_preference(
    user_id: str,
    key: str,
    value: Any
) -> bool:
    """
    Update a single user preference
    
    Args:
        user_id: User ID
        key: Preference key
        value: Preference value
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.USERS].update_one(
            {'userId': user_id},
            {
                '$set': {
                    f'preferences.{key}': value,
                    'updatedAt': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Updated preference {key} for user {user_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to update preference for user {user_id}: {e}")
        raise


async def update_user_metadata(
    user_id: str,
    key: str,
    value: Any
) -> bool:
    """
    Update user metadata
    
    Args:
        user_id: User ID
        key: Metadata key
        value: Metadata value
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.USERS].update_one(
            {'userId': user_id},
            {
                '$set': {
                    f'metadata.{key}': value,
                    'updatedAt': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Updated metadata {key} for user {user_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to update metadata for user {user_id}: {e}")
        raise


async def increment_user_usage(
    user_id: str,
    usage_type: str
) -> bool:
    """
    Increment user usage counter
    
    Args:
        user_id: User ID
        usage_type: Usage type (chats/queries/videos/documents)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.USERS].update_one(
            {'userId': user_id},
            {
                '$inc': {f'metadata.usage.{usage_type}': 1},
                '$set': {'updatedAt': datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Incremented {usage_type} usage for user {user_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to increment usage for user {user_id}: {e}")
        raise


async def update_last_login(user_id: str) -> bool:
    """
    Update user's last login timestamp
    
    Args:
        user_id: User ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.USERS].update_one(
            {'userId': user_id},
            {
                '$set': {
                    'lastLoginAt': datetime.utcnow(),
                    'updatedAt': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Updated last login for user {user_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to update last login for user {user_id}: {e}")
        raise


async def deactivate_user(user_id: str) -> bool:
    """
    Deactivate a user
    
    Args:
        user_id: User ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.USERS].update_one(
            {'userId': user_id},
            {
                '$set': {
                    'isActive': False,
                    'updatedAt': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"⚠️  Deactivated user {user_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to deactivate user {user_id}: {e}")
        raise


async def activate_user(user_id: str) -> bool:
    """
    Activate a user
    
    Args:
        user_id: User ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.USERS].update_one(
            {'userId': user_id},
            {
                '$set': {
                    'isActive': True,
                    'updatedAt': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Activated user {user_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to activate user {user_id}: {e}")
        raise


async def delete_user(user_id: str) -> bool:
    """
    Permanently delete a user
    
    Args:
        user_id: User ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.USERS].delete_one({
            'userId': user_id
        })
        
        if result.deleted_count > 0:
            logger.warning(f"🗑️  Permanently deleted user {user_id}")
            return True
        
        logger.warning(f"⚠️  User {user_id} not found")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to delete user {user_id}: {e}")
        raise


async def get_user_stats(user_id: str) -> Dict[str, Any]:
    """
    Get user statistics
    
    Args:
        user_id: User ID
    
    Returns:
        Dictionary with user statistics
    """
    try:
        db = await get_db()
        
        # Get user
        user = await get_user_by_id(user_id)
        
        if not user:
            return {}
        
        # Get counts from different collections
        total_chats = await db[Collections.CHATS].count_documents({
            'userId': user_id,
            'isDeleted': False
        })
        
        total_queries = await db[Collections.QUERIES].count_documents({
            'userId': user_id
        })
        
        total_videos = await db[Collections.YOUTUBE_VIDEOS].count_documents({
            'userId': user_id
        })
        
        total_documents = await db[Collections.DOCUMENTS].count_documents({
            'userId': user_id
        })
        
        # Calculate account age
        created_at = user.get('createdAt', datetime.utcnow())
        account_age = (datetime.utcnow() - created_at).days
        
        return {
            'totalChats': total_chats,
            'totalQueries': total_queries,
            'totalVideosProcessed': total_videos,
            'totalDocuments': total_documents,
            'accountAge': account_age,
            'lastActive': user.get('lastLoginAt'),
            'role': user.get('role'),
            'plan': user.get('metadata', {}).get('plan', 'free')
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get stats for user {user_id}: {e}")
        return {}


async def get_all_users(
    limit: int = 100,
    skip: int = 0,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    Get all users (admin function)
    
    Args:
        limit: Maximum number of users
        skip: Number to skip (pagination)
        active_only: Whether to return only active users
    
    Returns:
        List of user documents
    """
    try:
        db = await get_db()
        
        query = {}
        if active_only:
            query['isActive'] = True
        
        cursor = db[Collections.USERS].find(
            query,
            {'_id': 0}
        ).sort('createdAt', -1).skip(skip).limit(limit)
        
        users = await cursor.to_list(length=limit)
        
        logger.info(f"📋 Retrieved {len(users)} users")
        return users
        
    except Exception as e:
        logger.error(f"❌ Failed to get all users: {e}")
        return []


async def get_user_count(active_only: bool = True) -> int:
    """
    Get total number of users
    
    Args:
        active_only: Whether to count only active users
    
    Returns:
        Number of users
    """
    try:
        db = await get_db()
        
        query = {}
        if active_only:
            query['isActive'] = True
        
        count = await db[Collections.USERS].count_documents(query)
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to get user count: {e}")
        return 0


async def search_users(
    query: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search users by email, username, or name
    
    Args:
        query: Search query
        limit: Maximum number of results
    
    Returns:
        List of matching users
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.USERS].find(
            {
                '$or': [
                    {'email': {'$regex': query, '$options': 'i'}},
                    {'username': {'$regex': query, '$options': 'i'}},
                    {'firstName': {'$regex': query, '$options': 'i'}},
                    {'lastName': {'$regex': query, '$options': 'i'}}
                ]
            },
            {'_id': 0}
        ).limit(limit)
        
        users = await cursor.to_list(length=limit)
        
        logger.info(f"🔍 Found {len(users)} users matching '{query}'")
        return users
        
    except Exception as e:
        logger.error(f"❌ Failed to search users: {e}")
        return []


async def check_username_exists(username: str) -> bool:
    """
    Check if username already exists
    
    Args:
        username: Username to check
    
    Returns:
        True if exists, False otherwise
    """
    try:
        db = await get_db()
        
        count = await db[Collections.USERS].count_documents({
            'username': username
        })
        
        return count > 0
        
    except Exception as e:
        logger.error(f"❌ Failed to check username: {e}")
        return False
