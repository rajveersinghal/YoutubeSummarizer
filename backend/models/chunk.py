# models/chunk.py - FASTAPI ASYNC VERSION
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from database.session import get_db, Collections
from config.logging_config import logger


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ChunkModel(BaseModel):
    """Chunk document model"""
    videoId: str = Field(..., description="YouTube video ID")
    text: str = Field(..., description="Chunk text content")
    chunkIndex: int = Field(..., description="Chunk index/order")
    embedding: Optional[List[float]] = Field(None, description="Text embedding vector")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "videoId": "dQw4w9WgXcQ",
                "text": "This is a chunk of transcript text...",
                "chunkIndex": 0,
                "embedding": [0.1, 0.2, 0.3],
                "metadata": {
                    "startTime": "00:00:10",
                    "endTime": "00:00:30",
                    "duration": 20
                },
                "createdAt": "2025-12-25T17:00:00Z"
            }
        }


class ChunkCreateRequest(BaseModel):
    """Request model for creating chunks"""
    text: str = Field(..., min_length=1, max_length=10000)
    chunk_index: int = Field(..., ge=0, alias="chunkIndex")
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


class ChunkBatchCreateRequest(BaseModel):
    """Request model for batch creating chunks"""
    videoId: str
    chunks: List[ChunkCreateRequest]


# ============================================================================
# CHUNK DATABASE OPERATIONS (Async)
# ============================================================================

async def save_chunks(
    video_id: str,
    chunk_data: List[Dict[str, Any]],
    user_id: Optional[str] = None
) -> int:
    """
    Save chunks to MongoDB
    
    Args:
        video_id: YouTube video ID
        chunk_data: List of chunk dictionaries with 'text' and 'chunk_index'
        user_id: Optional user ID for ownership tracking
    
    Returns:
        Number of chunks saved
    
    Example chunk_data:
        [
            {"text": "chunk 1 text", "chunk_index": 0},
            {"text": "chunk 2 text", "chunk_index": 1}
        ]
    """
    try:
        db = await get_db()
        
        if not chunk_data:
            logger.warning(f"⚠️  No chunks to save for video {video_id}")
            return 0
        
        # Prepare chunks for insertion
        chunks = []
        for chunk in chunk_data:
            chunk_doc = {
                'videoId': video_id,
                'text': chunk.get('text', ''),
                'chunkIndex': chunk.get('chunk_index', 0),
                'embedding': chunk.get('embedding'),
                'metadata': chunk.get('metadata', {}),
                'createdAt': datetime.utcnow()
            }
            
            # Add user ID if provided
            if user_id:
                chunk_doc['userId'] = user_id
            
            chunks.append(chunk_doc)
        
        # Insert all chunks
        result = await db[Collections.CHUNKS].insert_many(chunks)
        
        logger.info(f"💾 Saved {len(result.inserted_ids)} chunks for video {video_id}")
        return len(result.inserted_ids)
        
    except Exception as e:
        logger.error(f"❌ Failed to save chunks for video {video_id}: {e}")
        raise


async def get_chunks_by_video(
    video_id: str,
    include_embeddings: bool = False
) -> List[Dict[str, Any]]:
    """
    Get all chunks for a video, sorted by chunk index
    
    Args:
        video_id: YouTube video ID
        include_embeddings: Whether to include embedding vectors in response
    
    Returns:
        List of chunk documents
    """
    try:
        db = await get_db()
        
        # Projection to exclude embeddings if not needed (saves bandwidth)
        projection = None
        if not include_embeddings:
            projection = {'embedding': 0, '_id': 0}
        else:
            projection = {'_id': 0}
        
        cursor = db[Collections.CHUNKS].find(
            {'videoId': video_id},
            projection
        ).sort('chunkIndex', 1)
        
        chunks = await cursor.to_list(length=None)
        
        logger.info(f"📄 Retrieved {len(chunks)} chunks for video {video_id}")
        return chunks
        
    except Exception as e:
        logger.error(f"❌ Failed to get chunks for video {video_id}: {e}")
        return []


async def get_chunk_by_index(
    video_id: str,
    chunk_index: int
) -> Optional[Dict[str, Any]]:
    """
    Get a specific chunk by video ID and index
    
    Args:
        video_id: YouTube video ID
        chunk_index: Chunk index
    
    Returns:
        Chunk document or None
    """
    try:
        db = await get_db()
        
        chunk = await db[Collections.CHUNKS].find_one({
            'videoId': video_id,
            'chunkIndex': chunk_index
        })
        
        if chunk:
            chunk.pop('_id', None)
        
        return chunk
        
    except Exception as e:
        logger.error(f"❌ Failed to get chunk {chunk_index} for video {video_id}: {e}")
        return None


async def get_chunk_count(video_id: str) -> int:
    """
    Get total number of chunks for a video
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Number of chunks
    """
    try:
        db = await get_db()
        
        count = await db[Collections.CHUNKS].count_documents({
            'videoId': video_id
        })
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to get chunk count for video {video_id}: {e}")
        return 0


async def delete_chunks_by_video(video_id: str) -> int:
    """
    Delete all chunks for a video
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Number of chunks deleted
    """
    try:
        db = await get_db()
        
        result = await db[Collections.CHUNKS].delete_many({
            'videoId': video_id
        })
        
        logger.info(f"🗑️  Deleted {result.deleted_count} chunks for video {video_id}")
        return result.deleted_count
        
    except Exception as e:
        logger.error(f"❌ Failed to delete chunks for video {video_id}: {e}")
        raise


async def update_chunk_embedding(
    video_id: str,
    chunk_index: int,
    embedding: List[float]
) -> bool:
    """
    Update embedding for a specific chunk
    
    Args:
        video_id: YouTube video ID
        chunk_index: Chunk index
        embedding: Embedding vector
    
    Returns:
        True if successful, False otherwise
    """
    try:
        db = await get_db()
        
        result = await db[Collections.CHUNKS].update_one(
            {
                'videoId': video_id,
                'chunkIndex': chunk_index
            },
            {
                '$set': {
                    'embedding': embedding,
                    'updatedAt': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Updated embedding for chunk {chunk_index} of video {video_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to update embedding: {e}")
        raise


async def batch_update_embeddings(
    video_id: str,
    embeddings: List[Dict[str, Any]]
) -> int:
    """
    Batch update embeddings for multiple chunks
    
    Args:
        video_id: YouTube video ID
        embeddings: List of dicts with 'chunk_index' and 'embedding'
    
    Returns:
        Number of chunks updated
    
    Example embeddings:
        [
            {"chunk_index": 0, "embedding": [0.1, 0.2, ...]},
            {"chunk_index": 1, "embedding": [0.3, 0.4, ...]}
        ]
    """
    try:
        db = await get_db()
        
        updated_count = 0
        
        for item in embeddings:
            chunk_index = item.get('chunk_index')
            embedding = item.get('embedding')
            
            if chunk_index is not None and embedding:
                result = await db[Collections.CHUNKS].update_one(
                    {
                        'videoId': video_id,
                        'chunkIndex': chunk_index
                    },
                    {
                        '$set': {
                            'embedding': embedding,
                            'updatedAt': datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    updated_count += 1
        
        logger.info(f"✅ Updated {updated_count} embeddings for video {video_id}")
        return updated_count
        
    except Exception as e:
        logger.error(f"❌ Failed to batch update embeddings: {e}")
        raise


async def search_chunks_by_text(
    query: str,
    video_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search chunks by text content
    
    Args:
        query: Search query
        video_id: Optional video ID to filter by
        limit: Maximum number of results
    
    Returns:
        List of matching chunks
    """
    try:
        db = await get_db()
        
        # Build query filter
        filter_query = {
            'text': {'$regex': query, '$options': 'i'}
        }
        
        if video_id:
            filter_query['videoId'] = video_id
        
        cursor = db[Collections.CHUNKS].find(
            filter_query,
            {'_id': 0}
        ).limit(limit)
        
        chunks = await cursor.to_list(length=limit)
        
        logger.info(f"🔍 Found {len(chunks)} chunks matching query: {query[:50]}")
        return chunks
        
    except Exception as e:
        logger.error(f"❌ Failed to search chunks: {e}")
        return []


async def get_chunks_by_user(
    user_id: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get all chunks belonging to a user
    
    Args:
        user_id: User ID
        limit: Maximum number of chunks
    
    Returns:
        List of chunk documents
    """
    try:
        db = await get_db()
        
        cursor = db[Collections.CHUNKS].find(
            {'userId': user_id},
            {'_id': 0, 'embedding': 0}
        ).sort('createdAt', -1).limit(limit)
        
        chunks = await cursor.to_list(length=limit)
        
        return chunks
        
    except Exception as e:
        logger.error(f"❌ Failed to get chunks for user {user_id}: {e}")
        return []


async def get_chunk_statistics(video_id: str) -> Dict[str, Any]:
    """
    Get statistics about chunks for a video
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Dictionary with statistics
    """
    try:
        db = await get_db()
        
        pipeline = [
            {'$match': {'videoId': video_id}},
            {
                '$group': {
                    '_id': None,
                    'totalChunks': {'$sum': 1},
                    'avgTextLength': {'$avg': {'$strLenCP': '$text'}},
                    'totalTextLength': {'$sum': {'$strLenCP': '$text'}},
                    'chunksWithEmbeddings': {
                        '$sum': {
                            '$cond': [{'$ifNull': ['$embedding', False]}, 1, 0]
                        }
                    }
                }
            }
        ]
        
        result = await db[Collections.CHUNKS].aggregate(pipeline).to_list(1)
        
        if result:
            stats = result[0]
            stats.pop('_id', None)
            return stats
        
        return {
            'totalChunks': 0,
            'avgTextLength': 0,
            'totalTextLength': 0,
            'chunksWithEmbeddings': 0
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get chunk statistics: {e}")
        return {}
