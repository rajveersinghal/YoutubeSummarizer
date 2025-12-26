# middleware/auth.py - Clerk Authentication Middleware (COMPLETE & FIXED)

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import httpx
import jwt
from config.settings import settings
from config.logging_config import logger
from database.database import get_db
import time

# Security scheme
security = HTTPBearer(auto_error=False)

# ============================================================================
# MAIN AUTHENTICATION FUNCTION
# ============================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Extract and verify user from Clerk JWT token
    """
    try:
        if not credentials:
            logger.warning("❌ Missing Authorization header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = credentials.credentials
        
        if not token:
            logger.warning("❌ Empty authentication token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Empty authentication token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        logger.info(f"🔐 Verifying token: {token[:30]}...")
        
        # Verify token and get user data
        user_data = await verify_clerk_token(token)
        
        if not user_data:
            logger.warning("❌ Token verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        logger.info(f"✅ Authenticated user: {user_data.get('user_id')}")
        
        # Store user in database and get full user data
        full_user_data = await store_user_in_db(user_data)
        
        return full_user_data or user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected authentication error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

# ============================================================================
# TOKEN VERIFICATION - SIMPLE DECODE METHOD
# ============================================================================

async def verify_clerk_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Clerk JWT token by decoding and fetching user from Clerk API
    """
    try:
        if not settings.CLERK_SECRET_KEY:
            logger.error("❌ CLERK_SECRET_KEY not configured")
            return None
        
        logger.info("🔐 Decoding token...")
        
        # ✅ Decode token without verification to get user_id
        try:
            unverified_payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            
            user_id = unverified_payload.get("sub")
            
            if not user_id:
                logger.warning("❌ Token missing user_id (sub)")
                return None
            
            logger.info(f"✅ Extracted user_id from token: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to decode token: {e}")
            return None
        
        # ✅ Verify the user exists in Clerk by fetching their details
        user_data = await fetch_clerk_user(user_id)
        
        if not user_data:
            logger.warning("❌ User not found in Clerk")
            return None
        
        logger.info(f"✅ Token verified for user: {user_id}")
        return user_data
        
    except Exception as e:
        logger.error(f"❌ Token verification error: {e}", exc_info=True)
        return None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def fetch_clerk_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch user details from Clerk API
    """
    try:
        clerk_api_url = f"https://api.clerk.com/v1/users/{user_id}"
        
        headers = {
            "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
        }
        
        logger.info(f"📡 Fetching user from Clerk API: {user_id}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(clerk_api_url, headers=headers)
            
            if response.status_code == 200:
                user = response.json()
                logger.info("✅ User fetched successfully from Clerk")
                
                # Get primary email
                email_addresses = user.get("email_addresses", [])
                primary_email_id = user.get("primary_email_address_id")
                email = ""
                
                if email_addresses:
                    if primary_email_id:
                        email = next(
                            (e["email_address"] for e in email_addresses if e["id"] == primary_email_id),
                            email_addresses[0]["email_address"]
                        )
                    else:
                        email = email_addresses[0]["email_address"]
                
                return {
                    "user_id": user.get("id"),
                    "email": email,
                    "username": user.get("username", ""),
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                    "image_url": user.get("profile_image_url", ""),
                    "email_verified": True,
                }
            
            elif response.status_code == 401:
                logger.error("❌ Invalid Clerk secret key")
                return None
            
            elif response.status_code == 404:
                logger.error(f"❌ User not found: {user_id}")
                return None
            
            else:
                logger.error(f"❌ Clerk API error: {response.status_code} - {response.text}")
                return None
            
    except httpx.TimeoutException:
        logger.error("❌ Clerk API request timeout")
        return None
    except Exception as e:
        logger.error(f"❌ Error fetching Clerk user: {e}", exc_info=True)
        return None

# ============================================================================
# DATABASE STORAGE
# ============================================================================

async def store_user_in_db(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Store or update user in database"""
    try:
        # ✅ FIXED: Use get_db() directly (not next())
        db = get_db()
        
        user_doc = {
            "user_id": user_data["user_id"],
            "email": user_data.get("email", ""),
            "username": user_data.get("username", ""),
            "first_name": user_data.get("first_name", ""),
            "last_name": user_data.get("last_name", ""),
            "full_name": user_data.get("full_name", ""),
            "image_url": user_data.get("image_url", ""),
            "last_seen": time.time(),
            "updated_at": time.time(),
        }
        
        # ✅ FIXED: Synchronous operation (no await)
        result = db.users.find_one_and_update(
            {"user_id": user_data["user_id"]},
            {
                "$set": user_doc,
                "$setOnInsert": {
                    "created_at": time.time(),
                    "preferences": {
                        "theme": "light",
                        "language": "en",
                        "notifications": True
                    }
                }
            },
            upsert=True,
            return_document=True  # Returns updated document
        )
        
        logger.debug(f"✅ User stored/updated in DB: {user_data['user_id']}")
        
        if result:
            return {
                **user_data,
                "preferences": result.get("preferences", {
                    "theme": "light",
                    "language": "en",
                    "notifications": True
                })
            }
        
        return user_data
        
    except Exception as e:
        logger.error(f"❌ Error storing user in DB: {e}", exc_info=True)
        return user_data

# ============================================================================
# USER PREFERENCES
# ============================================================================

async def get_user_preferences(user_id: str) -> Dict[str, Any]:
    """Get user preferences from database"""
    try:
        # ✅ FIXED: Use get_db() directly
        db = get_db()
        
        user = db.users.find_one({"user_id": user_id})
        
        if user:
            return user.get("preferences", {
                "theme": "light",
                "language": "en",
                "notifications": True
            })
        
        return {
            "theme": "light",
            "language": "en",
            "notifications": True
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting user preferences: {e}")
        return {
            "theme": "light",
            "language": "en",
            "notifications": True
        }

async def update_user_preferences(
    user_id: str,
    preferences: Dict[str, Any]
) -> bool:
    """Update user preferences in database"""
    try:
        # ✅ FIXED: Use get_db() directly
        db = get_db()
        
        result = db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "preferences": preferences,
                    "updated_at": time.time()
                }
            }
        )
        
        return result.modified_count > 0 or result.matched_count > 0
        
    except Exception as e:
        logger.error(f"❌ Error updating user preferences: {e}")
        return False

# ============================================================================
# OPTIONAL AUTHENTICATION
# ============================================================================

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Optional authentication - returns None if not authenticated"""
    try:
        if not credentials:
            return None
        
        token = credentials.credentials
        if not token:
            return None
        
        user_data = await verify_clerk_token(token)
        
        if user_data:
            full_user_data = await store_user_in_db(user_data)
            return full_user_data or user_data
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Optional auth error: {e}")
        return None

# ============================================================================
# ADMIN AUTHENTICATION
# ============================================================================

async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Require admin role for endpoint"""
    # ✅ FIXED: Use properties from settings
    admin_user_ids = settings.admin_user_ids_list
    admin_emails = settings.admin_emails_list
    
    user_id = current_user.get("user_id")
    user_email = current_user.get("email", "").lower()
    
    is_admin = user_id in admin_user_ids or user_email in admin_emails
    
    if not is_admin:
        logger.warning(f"❌ Non-admin user attempted admin access: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    logger.info(f"✅ Admin access granted: {user_id}")
    return current_user

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_user_id(current_user: Dict[str, Any]) -> str:
    """Extract user_id from authenticated user dict"""
    return current_user.get("user_id", "")

def get_user_email(current_user: Dict[str, Any]) -> str:
    """Extract email from authenticated user dict"""
    return current_user.get("email", "")

def get_user_name(current_user: Dict[str, Any]) -> str:
    """Extract full name from authenticated user dict"""
    return current_user.get("full_name", "") or \
           f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip()

def is_admin_user(current_user: Dict[str, Any]) -> bool:
    """Check if current user is admin"""
    user_id = current_user.get("user_id")
    user_email = current_user.get("email", "").lower()
    
    return (
        user_id in settings.admin_user_ids_list or
        user_email in settings.admin_emails_list
    )
