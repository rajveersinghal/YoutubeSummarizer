# models/query.py - FASTAPI ASYNC VERSION
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid

from database.session import get_db, Collections
from config.logging_config import logger


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class QueryModel(BaseModel):
    """Query document model"""
    queryId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str = Field(..., description="User ID who made the query")
    chatId: Optional[str] = Field(None, description="Associated chat ID")
    videoId: Optional[str] = Field(None, description="Associated video ID")
    documentId: Optional[str] = Field(None, description="Associated document ID")
    question: str = Field(..., min_length=1, max_length=5000)
    answer: str = Field(..., min_length=1)
    context: Optional[List[str]] = Field(default_factory=list, description="Retrieved context chunks")
    mode: str = Field(default="chat", description="Query mode: chat/rag/youtube/document")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    responseTime: Optional[float] = Field(None, description="Response time in seconds")
    tokensUsed: Optional[int] = Field(None, description="Number of tokens used")
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "queryId": "query_123",
                "userId": "user_123",
                "chatId": "chat_456",
                "question": "What is the main topic?",
                "answer": "The main topic is...",
                "context": ["Relevant chunk 1", "Relevant chunk 2"],
                "mode": "rag",
                "metadata": {"model": "gemini-flash"},
                "responseTime": 1.23,
                "tokensUsed": 150,
                "createdAt": "2025-12-25T17:00:00Z"
            }
        }


class SaveQueryRequest(BaseModel):
    """Request model for saving a query"""
    chatId: Optional[str] = None
    videoId: Optional[str] = None
    documentId: Optional[str] = None
    question: str = Field(..., min_length=1, max_length=5000)
    answer: str = Field(..., min_length=1)
    context: Optional[List[str]] = None
    mode: str = Field(default="chat")
    metadata: Optional[Dict[str, Any]] = None
    responseTime: Optional[float] = None
    tokensUsed: Optional[int] = None


class QueryStatsModel(BaseModel):
    """Query statistics model"""
    totalQueries: int
    avgResponseTime: float
    totalTokensUsed: int
    modeBreakdown: Dict[str, int]
    recentQueries: int


# ============================================================================
# QUERY DATABASE OPERATIONS (Async)
# ============================================================================

async def save_query(
    user_id: str,
    question: str,
    answer: str,
    chat_id: Optional[str] = None,
    video_id: Optional[str] = None,
    document_id: Optional[str] = None,
    context: Optional[List[str]] = None,
    mode: str = "chat",
    metadata: Optional[Dict[str, Any]] = None,
    response_time: Optional[float] = None,
    tokens_used: Optional[int] = None
) -> str:
    """
    Save a query to the database
    
    Args:
        user_id: User ID
        question: User's question
        answer: AI's answer
        chat_id: Optional chat ID
        video_id: Optional video ID
        document_id: Optional document ID
        context: Retrieved context chunks
        mode: Query mode (chat/rag/youtube/document)
        metadata: Additional metadata
        response_time: Response time in seconds
        tokens_used: Number of tokens used
    
    Returns:
        query_id: ID of saved query
    """
    try:
        db = await get_db()
        
        query_id = str(uuid.uuid4())
        
        query_doc = {
            'queryId': query_id,
            'userId': user_id,
            'chatId': chat_id,
            'videoId': video_id,
            'documentId': document_id,
            'question': question,
            'answer': answer,
            'context': context or [],
            'mode': mode,
            'metadata': metadata or {},
            'responseTime': response_time,
            'tokensUsed': tokens_used,
            'createdAt': datetime.utcnow()
        }
        
        await db[Collections.QUERIES].insert_one(query_doc)
        
        logger.info(f"💾 Saved query {query_id} for user {user_id}")
        return query_id
        
    except Exception as e:
        logger.error(f"❌ Failed to save query: {e}")
        raise


async def get_query_by_id(
    user_id: str,
    query_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get a specific query by ID
    
    Args:
        user_id: User ID (for authorization)
        query_id: Query ID
    
    Returns:
        Query document or None
    """
    try:
        db = await get_db()
        
        query = await db[Collections.QUERIES].find_one(
            {
                'queryId': query_id,
                'userId': user_id
            },
            {'_id': 0}
        )
        
        return query
        
    except Exception as e:
        logger.error(f"❌ Failed to get query {query_id}: {e}")
        return None


async def get_queries_by_user(
    user_id: str,
    limit: int = 100,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """
    Get all queries for a user
    
    Args:
        user_id: User ID
        limit: Maximum number of queries
        skip: Number to skip (pagination)
    
    Returns:
        List of query documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.QUERIES].find(
            {'userId': user_id},
            {'_id': 0}
        ).sort('createdAt', -1).skip(skip).limit(limit)
        
        queries = await cursor.to_list(length=limit)
        
        logger.info(f"📜 Retrieved {len(queries)} queries for user {user_id}")
        return queries
        
    except Exception as e:
        logger.error(f"❌ Failed to get queries for user {user_id}: {e}")
        return []


async def get_queries_by_chat(
    user_id: str,
    chat_id: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get all queries for a specific chat
    
    Args:
        user_id: User ID (for authorization)
        chat_id: Chat ID
        limit: Maximum number of queries
    
    Returns:
        List of query documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.QUERIES].find(
            {
                'userId': user_id,
                'chatId': chat_id
            },
            {'_id': 0}
        ).sort('createdAt', 1).limit(limit)
        
        queries = await cursor.to_list(length=limit)
        
        return queries
        
    except Exception as e:
        logger.error(f"❌ Failed to get queries for chat {chat_id}: {e}")
        return []


async def get_queries_by_video(
    user_id: str,
    video_id: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get all queries for a specific video
    
    Args:
        user_id: User ID (for authorization)
        video_id: Video ID
        limit: Maximum number of queries
    
    Returns:
        List of query documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.QUERIES].find(
            {
                'userId': user_id,
                'videoId': video_id
            },
            {'_id': 0}
        ).sort('createdAt', -1).limit(limit)
        
        queries = await cursor.to_list(length=limit)
        
        return queries
        
    except Exception as e:
        logger.error(f"❌ Failed to get queries for video {video_id}: {e}")
        return []


async def get_queries_by_document(
    user_id: str,
    document_id: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get all queries for a specific document
    
    Args:
        user_id: User ID (for authorization)
        document_id: Document ID
        limit: Maximum number of queries
    
    Returns:
        List of query documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.QUERIES].find(
            {
                'userId': user_id,
                'documentId': document_id
            },
            {'_id': 0}
        ).sort('createdAt', -1).limit(limit)
        
        queries = await cursor.to_list(length=limit)
        
        return queries
        
    except Exception as e:
        logger.error(f"❌ Failed to get queries for document {document_id}: {e}")
        return []


async def get_queries_by_mode(
    user_id: str,
    mode: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get queries filtered by mode
    
    Args:
        user_id: User ID
        mode: Query mode (chat/rag/youtube/document)
        limit: Maximum number of queries
    
    Returns:
        List of query documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.QUERIES].find(
            {
                'userId': user_id,
                'mode': mode
            },
            {'_id': 0}
        ).sort('createdAt', -1).limit(limit)
        
        queries = await cursor.to_list(length=limit)
        
        return queries
        
    except Exception as e:
        logger.error(f"❌ Failed to get queries by mode {mode}: {e}")
        return []


async def search_queries(
    user_id: str,
    search_text: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search queries by question or answer
    
    Args:
        user_id: User ID
        search_text: Search text
        limit: Maximum number of results
    
    Returns:
        List of matching query documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.QUERIES].find(
            {
                'userId': user_id,
                '$or': [
                    {'question': {'$regex': search_text, '$options': 'i'}},
                    {'answer': {'$regex': search_text, '$options': 'i'}}
                ]
            },
            {'_id': 0}
        ).sort('createdAt', -1).limit(limit)
        
        queries = await cursor.to_list(length=limit)
        
        logger.info(f"🔍 Found {len(queries)} queries matching '{search_text}'")
        return queries
        
    except Exception as e:
        logger.error(f"❌ Failed to search queries: {e}")
        return []


async def delete_query(
    user_id: str,
    query_id: str
) -> bool:
    """
    Delete a specific query
    
    Args:
        user_id: User ID (for authorization)
        query_id: Query ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.QUERIES].delete_one({
            'queryId': query_id,
            'userId': user_id
        })
        
        if result.deleted_count > 0:
            logger.info(f"🗑️  Deleted query {query_id}")
            return True
        
        logger.warning(f"⚠️  Query {query_id} not found")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to delete query {query_id}: {e}")
        raise


async def delete_queries_by_chat(
    user_id: str,
    chat_id: str
) -> int:
    """
    Delete all queries for a specific chat
    
    Args:
        user_id: User ID (for authorization)
        chat_id: Chat ID
    
    Returns:
        Number of queries deleted
    """
    try:
        db = await get_db()
        
        result = await db[Collections.QUERIES].delete_many({
            'userId': user_id,
            'chatId': chat_id
        })
        
        logger.info(f"🗑️  Deleted {result.deleted_count} queries for chat {chat_id}")
        return result.deleted_count
        
    except Exception as e:
        logger.error(f"❌ Failed to delete queries for chat {chat_id}: {e}")
        raise


async def get_query_count(user_id: str) -> int:
    """
    Get total number of queries for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Number of queries
    """
    try:
        db = await get_db()
        
        count = await db[Collections.QUERIES].count_documents({
            'userId': user_id
        })
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to get query count for user {user_id}: {e}")
        return 0


async def get_query_stats(user_id: str) -> Dict[str, Any]:
    """
    Get query statistics for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Dictionary with statistics
    """
    try:
        db = await get_db()
        
        # Total count
        total = await db[Collections.QUERIES].count_documents({
            'userId': user_id
        })
        
        # Mode breakdown
        pipeline = [
            {'$match': {'userId': user_id}},
            {
                '$group': {
                    '_id': '$mode',
                    'count': {'$sum': 1}
                }
            }
        ]
        
        mode_breakdown_cursor = db[Collections.QUERIES].aggregate(pipeline)
        mode_breakdown_list = await mode_breakdown_cursor.to_list(length=None)
        
        mode_breakdown = {
            item['_id']: item['count']
            for item in mode_breakdown_list
        }
        
        # Average response time
        avg_pipeline = [
            {
                '$match': {
                    'userId': user_id,
                    'responseTime': {'$ne': None}
                }
            },
            {
                '$group': {
                    '_id': None,
                    'avgResponseTime': {'$avg': '$responseTime'},
                    'totalTokens': {'$sum': '$tokensUsed'}
                }
            }
        ]
        
        avg_cursor = db[Collections.QUERIES].aggregate(avg_pipeline)
        avg_result = await avg_cursor.to_list(1)
        
        avg_response_time = 0
        total_tokens = 0
        
        if avg_result:
            avg_response_time = avg_result[0].get('avgResponseTime', 0) or 0
            total_tokens = avg_result[0].get('totalTokens', 0) or 0
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_count = await db[Collections.QUERIES].count_documents({
            'userId': user_id,
            'createdAt': {'$gte': week_ago}
        })
        
        return {
            'totalQueries': total,
            'avgResponseTime': round(avg_response_time, 2),
            'totalTokensUsed': total_tokens,
            'modeBreakdown': mode_breakdown,
            'recentQueries': recent_count
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get query stats for user {user_id}: {e}")
        return {
            'totalQueries': 0,
            'avgResponseTime': 0,
            'totalTokensUsed': 0,
            'modeBreakdown': {},
            'recentQueries': 0
        }


async def get_recent_queries(
    user_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get most recent queries for a user
    
    Args:
        user_id: User ID
        limit: Number of recent queries
    
    Returns:
        List of recent query documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.QUERIES].find(
            {'userId': user_id},
            {'_id': 0, 'context': 0}  # Exclude context to reduce size
        ).sort('createdAt', -1).limit(limit)
        
        queries = await cursor.to_list(length=limit)
        
        return queries
        
    except Exception as e:
        logger.error(f"❌ Failed to get recent queries for user {user_id}: {e}")
        return []


async def get_popular_questions(
    user_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get most frequently asked questions by a user
    
    Args:
        user_id: User ID
        limit: Number of results
    
    Returns:
        List of popular questions with counts
    """
    try:
        db = await get_db()
        
        pipeline = [
            {'$match': {'userId': user_id}},
            {
                '$group': {
                    '_id': '$question',
                    'count': {'$sum': 1},
                    'lastAsked': {'$max': '$createdAt'}
                }
            },
            {'$sort': {'count': -1}},
            {'$limit': limit}
        ]
        
        cursor = db[Collections.QUERIES].aggregate(pipeline)
        results = await cursor.to_list(length=limit)
        
        popular = [
            {
                'question': item['_id'],
                'count': item['count'],
                'lastAsked': item['lastAsked']
            }
            for item in results
        ]
        
        return popular
        
    except Exception as e:
        logger.error(f"❌ Failed to get popular questions: {e}")
        return []
