# services/vector_store.py - FASTAPI ASYNC VERSION
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np
import faiss

from config.logging_config import logger
from config.settings import settings


# ============================================================================
# VECTOR STORE (FAISS)
# ============================================================================

class VectorStore:
    """
    In-memory vector store with FAISS
    Compatible with faiss-cpu >= 1.8.0
    """
    
    def __init__(self, dimension: int = 384):
        """
        Initialize vector store
        
        Args:
            dimension: Embedding dimension (default: 384 for all-MiniLM-L6-v2)
        """
        self.indexes: Dict[str, faiss.IndexFlatL2] = {}
        self.metadata: Dict[str, List[Dict[str, Any]]] = {}
        self.dim = dimension
        self._lock = asyncio.Lock()
    
    def add_vectors(self, chunk_data: List[Dict[str, Any]]) -> bool:
        """
        Add vectors to the store (synchronous)
        
        Args:
            chunk_data: List of dicts with video_id, chunk_index, text, embedding
        
        Returns:
            True if successful
        """
        try:
            if not chunk_data:
                logger.warning("⚠️  No chunk data provided")
                return False
            
            video_id = chunk_data[0].get("video_id") or chunk_data[0].get("videoId")
            
            if not video_id:
                logger.error("❌ No video_id in chunk data")
                return False
            
            # Stack embeddings
            embeddings = []
            for chunk in chunk_data:
                emb = chunk.get("embedding")
                if isinstance(emb, list):
                    embeddings.append(emb)
                elif isinstance(emb, np.ndarray):
                    embeddings.append(emb.tolist() if emb.ndim > 0 else [emb.item()])
                else:
                    logger.warning(f"⚠️  Invalid embedding format in chunk")
                    continue
            
            if not embeddings:
                logger.error("❌ No valid embeddings found")
                return False
            
            vecs = np.array(embeddings, dtype=np.float32)
            
            # Update dimension if needed
            if vecs.shape[1] != self.dim:
                logger.info(f"📏 Updating dimension from {self.dim} to {vecs.shape[1]}")
                self.dim = vecs.shape[1]
            
            # Create or get index
            if video_id not in self.indexes:
                logger.info(f"🔧 Creating new FAISS index for video {video_id}")
                index = faiss.IndexFlatL2(self.dim)
                self.indexes[video_id] = index
                self.metadata[video_id] = []
            else:
                index = self.indexes[video_id]
            
            # Add vectors to index
            index.add(vecs)
            self.metadata[video_id].extend(chunk_data)
            
            logger.info(f"✅ Added {len(vecs)} vectors to FAISS index for video {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add vectors: {e}")
            return False
    
    async def add_vectors_async(self, chunk_data: List[Dict[str, Any]]) -> bool:
        """
        Add vectors to the store (async)
        
        Args:
            chunk_data: List of chunk dictionaries
        
        Returns:
            True if successful
        """
        async with self._lock:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.add_vectors,
                chunk_data
            )
            return result
    
    def search(
        self,
        video_id: str,
        query_vec: np.ndarray,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors (synchronous)
        
        Args:
            video_id: Video ID
            query_vec: Query embedding vector
            top_k: Number of results to return
        
        Returns:
            List of similar chunks
        """
        try:
            if video_id not in self.indexes:
                logger.warning(f"⚠️  No index found for video {video_id}")
                return []
            
            index = self.indexes[video_id]
            
            # Ensure query vector is correct shape and type
            if isinstance(query_vec, list):
                query_vec = np.array(query_vec, dtype=np.float32)
            else:
                query_vec = query_vec.astype(np.float32)
            
            query_vec = query_vec.reshape(1, -1)
            
            # Perform search
            k = min(top_k, index.ntotal)
            distances, indices = index.search(query_vec, k)
            
            # Retrieve metadata
            chunks = []
            meta_list = self.metadata[video_id]
            
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(meta_list):
                    chunk = meta_list[idx].copy()
                    chunk['distance'] = float(distances[0][i])
                    # Convert distance to similarity score (0-1)
                    chunk['similarity'] = 1 / (1 + float(distances[0][i]))
                    chunks.append(chunk)
            
            logger.info(f"🔍 Found {len(chunks)} similar chunks for video {video_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    async def search_async(
        self,
        video_id: str,
        query_vec: np.ndarray,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors (async)
        
        Args:
            video_id: Video ID
            query_vec: Query embedding vector
            top_k: Number of results
        
        Returns:
            List of similar chunks
        """
        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(
            None,
            self.search,
            video_id,
            query_vec,
            top_k
        )
        return chunks
    
    def get_index_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific index
        
        Args:
            video_id: Video ID
        
        Returns:
            Dictionary with index information
        """
        if video_id not in self.indexes:
            return None
        
        return {
            "video_id": video_id,
            "total_vectors": self.indexes[video_id].ntotal,
            "dimension": self.dim,
            "chunks": len(self.metadata.get(video_id, []))
        }
    
    def get_all_indexes_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all indexes
        
        Returns:
            List of index information dictionaries
        """
        return [
            self.get_index_info(video_id)
            for video_id in self.indexes.keys()
        ]
    
    def delete_index(self, video_id: str) -> bool:
        """
        Delete index for a video
        
        Args:
            video_id: Video ID
        
        Returns:
            True if deleted, False if not found
        """
        try:
            if video_id in self.indexes:
                del self.indexes[video_id]
                del self.metadata[video_id]
                logger.info(f"🗑️  Deleted index for video {video_id}")
                return True
            
            logger.warning(f"⚠️  Index not found for video {video_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to delete index: {e}")
            return False
    
    async def delete_index_async(self, video_id: str) -> bool:
        """
        Delete index for a video (async)
        
        Args:
            video_id: Video ID
        
        Returns:
            True if deleted
        """
        async with self._lock:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.delete_index,
                video_id
            )
            return result
    
    def clear_all(self):
        """Clear all indexes and metadata"""
        try:
            count = len(self.indexes)
            self.indexes.clear()
            self.metadata.clear()
            logger.info(f"🧹 Cleared {count} indexes from vector store")
            
        except Exception as e:
            logger.error(f"❌ Failed to clear vector store: {e}")
    
    def exists(self, video_id: str) -> bool:
        """
        Check if index exists for video
        
        Args:
            video_id: Video ID
        
        Returns:
            True if exists
        """
        return video_id in self.indexes
    
    def get_total_vectors(self) -> int:
        """
        Get total number of vectors across all indexes
        
        Returns:
            Total vector count
        """
        return sum(
            index.ntotal
            for index in self.indexes.values()
        )
    
    def save_index(self, video_id: str, filepath: str) -> bool:
        """
        Save FAISS index to disk
        
        Args:
            video_id: Video ID
            filepath: Path to save index
        
        Returns:
            True if successful
        """
        try:
            if video_id not in self.indexes:
                logger.warning(f"⚠️  Index not found for video {video_id}")
                return False
            
            faiss.write_index(self.indexes[video_id], filepath)
            logger.info(f"💾 Saved index for video {video_id} to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save index: {e}")
            return False
    
    def load_index(
        self,
        video_id: str,
        filepath: str,
        metadata: List[Dict[str, Any]]
    ) -> bool:
        """
        Load FAISS index from disk
        
        Args:
            video_id: Video ID
            filepath: Path to index file
            metadata: Chunk metadata
        
        Returns:
            True if successful
        """
        try:
            index = faiss.read_index(filepath)
            self.indexes[video_id] = index
            self.metadata[video_id] = metadata
            
            logger.info(f"📂 Loaded index for video {video_id} from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load index: {e}")
            return False


# ============================================================================
# PERSISTENT VECTOR STORE (MongoDB-backed)
# ============================================================================

class PersistentVectorStore:
    """Vector store with MongoDB persistence"""
    
    def __init__(self):
        self.memory_store = VectorStore()
        self._cache_loaded = set()
    
    async def add_vectors(
        self,
        chunk_data: List[Dict[str, Any]],
        save_to_db: bool = True
    ) -> bool:
        """
        Add vectors to memory and optionally to database
        
        Args:
            chunk_data: List of chunk dictionaries
            save_to_db: Whether to save to MongoDB
        
        Returns:
            True if successful
        """
        try:
            # Add to memory store
            success = await self.memory_store.add_vectors_async(chunk_data)
            
            if success and save_to_db:
                # Save to database
                from models.chunk import save_chunks
                
                video_id = chunk_data[0].get("video_id") or chunk_data[0].get("videoId")
                await save_chunks(video_id, chunk_data)
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to add vectors: {e}")
            return False
    
    async def search(
        self,
        video_id: str,
        query_vec: np.ndarray,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search with automatic cache loading
        
        Args:
            video_id: Video ID
            query_vec: Query embedding
            top_k: Number of results
        
        Returns:
            List of similar chunks
        """
        try:
            # Load from DB if not in cache
            if video_id not in self._cache_loaded:
                await self._load_from_db(video_id)
            
            # Search in memory
            return await self.memory_store.search_async(video_id, query_vec, top_k)
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    async def _load_from_db(self, video_id: str):
        """Load vectors from database into memory"""
        try:
            from models.chunk import get_chunks_by_video
            
            logger.info(f"📂 Loading vectors for video {video_id} from database...")
            
            chunks = await get_chunks_by_video(video_id, include_embeddings=True)
            
            if chunks:
                await self.memory_store.add_vectors_async(chunks)
                self._cache_loaded.add(video_id)
                logger.info(f"✅ Loaded {len(chunks)} vectors from database")
            
        except Exception as e:
            logger.error(f"❌ Failed to load from database: {e}")


# ============================================================================
# GLOBAL VECTOR STORE INSTANCES
# ============================================================================

# In-memory vector store
vector_store = VectorStore()

# Persistent vector store (with MongoDB)
persistent_vector_store = PersistentVectorStore()

