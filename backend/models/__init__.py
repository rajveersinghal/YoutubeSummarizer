# models/__init__.py - MODELS MODULE

"""
Data models for SpectraAI Backend

This module contains Pydantic models for data validation and serialization.
All models are exported for easy importing throughout the application.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import time


# ============================================================================
# BASE MODELS
# ============================================================================

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class UserIdMixin(BaseModel):
    """Mixin for user_id field"""
    user_id: str = Field(..., description="User ID")


# ============================================================================
# USER MODELS
# ============================================================================

class User(BaseModel):
    """User model"""
    user_id: str
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    created_at: float
    updated_at: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123456",
                "email": "user@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "created_at": 1703001600.0,
                "updated_at": 1703001600.0
            }
        }


# ============================================================================
# CHAT MODELS
# ============================================================================

class Message(BaseModel):
    """Chat message model"""
    message_id: str
    conversation_id: str
    user_id: str
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., min_length=1, description="Message content")
    timestamp: float = Field(default_factory=time.time)
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is either user or assistant"""
        if v not in ['user', 'assistant', 'system']:
            raise ValueError("Role must be 'user', 'assistant', or 'system'")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_123456",
                "conversation_id": "conv_123456",
                "user_id": "user_123456",
                "role": "user",
                "content": "Hello, how are you?",
                "timestamp": 1703001600.0
            }
        }


class Conversation(BaseModel):
    """Conversation model"""
    conversation_id: str
    user_id: str
    title: str = Field(default="New Conversation", max_length=200)
    message_count: int = Field(default=0, ge=0)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv_123456",
                "user_id": "user_123456",
                "title": "AI Discussion",
                "message_count": 10,
                "created_at": 1703001600.0,
                "updated_at": 1703001600.0
            }
        }


# ============================================================================
# DOCUMENT MODELS
# ============================================================================

class Document(BaseModel):
    """Document model"""
    document_id: str
    user_id: str
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    file_name: str
    file_type: str
    file_size: int = Field(..., ge=0)
    file_url: str
    status: str = Field(default="active")
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate document status"""
        if v not in ['active', 'archived', 'deleted']:
            raise ValueError("Status must be 'active', 'archived', or 'deleted'")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_123456",
                "user_id": "user_123456",
                "title": "Project Report",
                "description": "Q4 2024 Report",
                "file_name": "report.pdf",
                "file_type": "application/pdf",
                "file_size": 1024000,
                "file_url": "user_123456/doc_123456.pdf",
                "status": "active",
                "created_at": 1703001600.0,
                "updated_at": 1703001600.0
            }
        }


# ============================================================================
# VIDEO MODELS
# ============================================================================

class Video(BaseModel):
    """Video model"""
    video_id: str
    user_id: str
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    file_name: str
    file_size: int = Field(..., ge=0)
    format: str
    video_url: str
    stream_url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = Field(None, ge=0)
    resolution: Optional[str] = None
    status: str = Field(default="processing")
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate video status"""
        if v not in ['processing', 'ready', 'failed', 'archived']:
            raise ValueError("Status must be 'processing', 'ready', 'failed', or 'archived'")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "vid_123456",
                "user_id": "user_123456",
                "title": "Tutorial Video",
                "description": "How to use the platform",
                "file_name": "tutorial.mp4",
                "file_size": 52428800,
                "format": "mp4",
                "video_url": "user_123456/videos/vid_123456.mp4",
                "stream_url": "/api/videos/vid_123456/stream",
                "duration": 120.5,
                "resolution": "1920x1080",
                "status": "ready",
                "created_at": 1703001600.0,
                "updated_at": 1703001600.0
            }
        }


# ============================================================================
# ACTIVITY MODELS
# ============================================================================

class Activity(BaseModel):
    """Activity log model"""
    activity_id: str
    user_id: str
    activity_type: str = Field(..., description="Type of activity")
    action: str = Field(..., description="Action performed")
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('activity_type')
    @classmethod
    def validate_activity_type(cls, v: str) -> str:
        """Validate activity type"""
        allowed_types = ['chat', 'document', 'video', 'search', 'auth', 'system']
        if v not in allowed_types:
            raise ValueError(f"Activity type must be one of {allowed_types}")
        return v
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action"""
        allowed_actions = ['view', 'create', 'update', 'delete', 'upload', 'download', 'search']
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of {allowed_actions}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "activity_id": "act_123456",
                "user_id": "user_123456",
                "activity_type": "document",
                "action": "upload",
                "resource_id": "doc_123456",
                "resource_type": "document",
                "timestamp": 1703001600.0,
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0..."
            }
        }


# ============================================================================
# EMBEDDING MODELS
# ============================================================================

class Embedding(BaseModel):
    """Vector embedding model"""
    embedding_id: str
    user_id: str
    document_id: str
    chunk_index: int = Field(..., ge=0)
    text: str = Field(..., min_length=1)
    vector: List[float]
    created_at: float = Field(default_factory=time.time)
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "embedding_id": "emb_123456",
                "user_id": "user_123456",
                "document_id": "doc_123456",
                "chunk_index": 0,
                "text": "Sample text chunk",
                "vector": [0.1, 0.2, 0.3],
                "created_at": 1703001600.0
            }
        }


# ============================================================================
# SEARCH MODELS
# ============================================================================

class SearchQuery(BaseModel):
    """Search query model"""
    query_id: str
    user_id: str
    query_text: str = Field(..., min_length=1, max_length=500)
    search_type: str = Field(default="semantic")
    results_count: int = Field(default=0, ge=0)
    timestamp: float = Field(default_factory=time.time)
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('search_type')
    @classmethod
    def validate_search_type(cls, v: str) -> str:
        """Validate search type"""
        if v not in ['semantic', 'keyword', 'hybrid']:
            raise ValueError("Search type must be 'semantic', 'keyword', or 'hybrid'")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "qry_123456",
                "user_id": "user_123456",
                "query_text": "machine learning basics",
                "search_type": "semantic",
                "results_count": 10,
                "timestamp": 1703001600.0
            }
        }


# ============================================================================
# NOTIFICATION MODELS
# ============================================================================

class Notification(BaseModel):
    """Notification model"""
    notification_id: str
    user_id: str
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    notification_type: str = Field(default="info")
    read: bool = Field(default=False)
    created_at: float = Field(default_factory=time.time)
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('notification_type')
    @classmethod
    def validate_notification_type(cls, v: str) -> str:
        """Validate notification type"""
        if v not in ['info', 'success', 'warning', 'error']:
            raise ValueError("Type must be 'info', 'success', 'warning', or 'error'")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "notification_id": "notif_123456",
                "user_id": "user_123456",
                "title": "Document Processed",
                "message": "Your document has been successfully processed",
                "notification_type": "success",
                "read": False,
                "created_at": 1703001600.0
            }
        }


# ============================================================================
# EXPORT ALL MODELS
# ============================================================================

__all__ = [
    # Base
    "TimestampMixin",
    "UserIdMixin",
    
    # User
    "User",
    
    # Chat
    "Message",
    "Conversation",
    
    # Documents
    "Document",
    
    # Videos
    "Video",
    
    # Activity
    "Activity",
    
    # Embeddings
    "Embedding",
    
    # Search
    "SearchQuery",
    
    # Notifications
    "Notification",
]
