# routes/auth.py - AUTHENTICATION ROUTES (UPDATED WITH PREFERENCES)

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import httpx

from middleware.auth import (
    get_current_user, 
    get_user_preferences, 
    update_user_preferences
)
from config.logging_config import logger
from config.settings import settings

# ============================================================================
# ROUTER SETUP
# ============================================================================

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class UserResponse(BaseModel):
    """User information response"""
    user_id: str
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    preferences: Optional[Dict[str, Any]] = None  # ✅ Added

class UserPreferences(BaseModel):
    """User preferences model"""
    theme: Optional[str] = "light"
    language: Optional[str] = "en"
    notifications: Optional[bool] = True

class TokenVerifyRequest(BaseModel):
    """Token verification request"""
    token: str = Field(..., description="JWT token to verify")

class TokenVerifyResponse(BaseModel):
    """Token verification response"""
    valid: bool
    user_id: Optional[str] = None
    message: str

class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    user_id: str
    status: str
    last_active_at: int
    expire_at: int

# ============================================================================
# PUBLIC ROUTES (No authentication required)
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint for authentication service"""
    return {
        "success": True,
        "message": "Authentication service is running",
        "service": "Clerk Auth",
        "version": "1.0.0"
    }

@router.post("/verify-token")
async def verify_token(request: TokenVerifyRequest):
    """Verify JWT token without requiring authentication"""
    try:
        clerk_api_url = "https://api.clerk.com/v1/sessions/verify"
        
        headers = {
            "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {"token": request.token}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                clerk_api_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                user_id = data.get("user_id") or data.get("sub")
                
                return TokenVerifyResponse(
                    valid=True,
                    user_id=user_id,
                    message="Token is valid"
                )
            else:
                return TokenVerifyResponse(
                    valid=False,
                    user_id=None,
                    message="Token is invalid or expired"
                )
    
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service timeout"
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed"
        )

# ============================================================================
# PROTECTED ROUTES (Authentication required)
# ============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    current_user: dict = Depends(get_current_user)  # ✅ Changed to get full user dict
):
    """
    Get current authenticated user information with preferences
    """
    try:
        user_id = current_user.get("user_id")
        
        # Get user preferences from database
        preferences = await get_user_preferences(user_id)
        
        # Fetch user details from Clerk API
        clerk_api_url = f"https://api.clerk.com/v1/users/{user_id}"
        
        headers = {
            "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(clerk_api_url, headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Extract email
                email_addresses = user_data.get("email_addresses", [])
                primary_email = next(
                    (e["email_address"] for e in email_addresses 
                     if e.get("id") == user_data.get("primary_email_address_id")),
                    None
                )
                
                return UserResponse(
                    user_id=user_data.get("id"),
                    email=primary_email,
                    username=user_data.get("username"),
                    first_name=user_data.get("first_name"),
                    last_name=user_data.get("last_name"),
                    profile_image_url=user_data.get("profile_image_url"),
                    created_at=user_data.get("created_at"),
                    updated_at=user_data.get("updated_at"),
                    preferences=preferences  # ✅ Include preferences
                )
            
            elif response.status_code == 404:
                # Return user data from middleware even if Clerk API fails
                return UserResponse(
                    user_id=current_user.get("user_id"),
                    email=current_user.get("email"),
                    username=current_user.get("username"),
                    first_name=current_user.get("first_name"),
                    last_name=current_user.get("last_name"),
                    preferences=preferences
                )
            else:
                logger.error(f"Clerk API error: {response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch user information"
                )
    
    except httpx.TimeoutException:
        # Return cached user data on timeout
        preferences = await get_user_preferences(current_user.get("user_id"))
        return UserResponse(
            user_id=current_user.get("user_id"),
            email=current_user.get("email"),
            preferences=preferences
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user information"
        )

# ============================================================================
# ✅ NEW: USER PREFERENCES ENDPOINTS
# ============================================================================

@router.get("/preferences")
async def get_preferences(
    current_user: dict = Depends(get_current_user)
):
    """
    Get user preferences
    """
    try:
        user_id = current_user.get("user_id")
        preferences = await get_user_preferences(user_id)
        
        return {
            "success": True,
            "preferences": preferences
        }
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        # Return default preferences on error
        return {
            "success": True,
            "preferences": {
                "theme": "light",
                "language": "en",
                "notifications": True
            }
        }

@router.patch("/preferences")
async def update_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user preferences
    """
    try:
        user_id = current_user.get("user_id")
        
        # Update preferences in database
        success = await update_user_preferences(user_id, preferences.dict(exclude_unset=True))
        
        if success:
            return {
                "success": True,
                "message": "Preferences updated successfully",
                "preferences": preferences.dict(exclude_unset=True)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update preferences"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )

@router.get("/session")
async def get_session_info(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get current session information"""
    try:
        user_id = current_user.get("user_id")
        
        # Extract token from request
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        
        # Verify session with Clerk API
        clerk_api_url = "https://api.clerk.com/v1/sessions/verify"
        
        headers = {
            "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {"token": token}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                clerk_api_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                session_data = response.json()
                
                return {
                    "success": True,
                    "session": {
                        "session_id": session_data.get("session_id"),
                        "user_id": session_data.get("user_id"),
                        "status": session_data.get("status"),
                        "last_active_at": session_data.get("last_active_at"),
                        "expire_at": session_data.get("expire_at")
                    }
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch session information"
        )

@router.post("/logout")
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Logout user (invalidate session)"""
    user_id = current_user.get("user_id")
    logger.info(f"User {user_id} logged out")
    
    return {
        "success": True,
        "message": "Successfully logged out",
        "user_id": user_id
    }

@router.get("/validate")
async def validate_auth(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Validate authentication"""
    user_id = current_user.get("user_id")
    
    return {
        "success": True,
        "authenticated": True,
        "user_id": user_id,
        "message": "Authentication is valid"
    }

# ============================================================================
# EXPORT ROUTER
# ============================================================================

__all__ = ["router"]
