# services/embedding_service.py - FASTAPI ASYNC VERSION
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime

from config.settings import settings
from config.logging_config import logger


# ============================================================================
# EMBEDDING MODEL MANAGER
# ============================================================================

class EmbeddingModelManager:
    """Manage embedding model lifecycle"""
    
    def __init__(self):
        self._model: Optional[SentenceTransformer] = None
        self._model_name: str = settings.EMBEDDING_MODEL
        self._loading_lock = asyncio.Lock()
    
    def get_model_sync(self) -> SentenceTransformer:
        """Get embedding model (synchronous)"""
        if self._model is None:
            logger.info(f"🔄 Loading embedding model: {self._model_name}")
            try:
                self._model = SentenceTransformer(self._model_name)
                logger.info(f"✅ Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"❌ Failed to load embedding model: {e}")
                raise
        
        return self._model
    
    async def get_model(self) -> SentenceTransformer:
        """Get embedding model (async)"""
        if self._model is None:
            async with self._loading_lock:
                if self._model is None:
                    loop = asyncio.get_event_loop()
                    self._model = await loop.run_in_executor(
                        None,
                        self.get_model_sync
                    )
        
        return self._model
    
    def unload_model(self):
        """Unload model from memory"""
        if self._model is not None:
            logger.info("🗑️  Unloading embedding model from memory")
            self._model = None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        if self._model is None:
            return {
                "model_name": self._model_name,
                "loaded": False
            }
        
        return {
            "model_name": self._model_name,
            "loaded": True,
            "max_seq_length": self._model.max_seq_length,
            "embedding_dimension": self._model.get_sentence_embedding_dimension()
        }


# Global model manager
model_manager = EmbeddingModelManager()


# ============================================================================
# TEXT CHUNKING
# ============================================================================

class TextChunker:
    """Chunk text for embedding generation"""
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separator: str = " "
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.separator = separator
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text to chunk
        
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            logger.warning("⚠️  Empty text provided for chunking")
            return []
        
        words = text.split(self.separator)
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk = self.separator.join(chunk_words)
            
            if chunk.strip():
                chunks.append(chunk.strip())
        
        logger.info(f"📄 Created {len(chunks)} chunks from text")
        return chunks
    
    def chunk_by_sentences(
        self,
        text: str,
        max_sentences_per_chunk: int = 5
    ) -> List[str]:
        """
        Chunk text by sentences
        
        Args:
            text: Input text
            max_sentences_per_chunk: Maximum sentences per chunk
        
        Returns:
            List of text chunks
        """
        import re
        
        # Split by sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        
        for i in range(0, len(sentences), max_sentences_per_chunk):
            chunk = ' '.join(sentences[i:i + max_sentences_per_chunk])
            if chunk.strip():
                chunks.append(chunk.strip())
        
        logger.info(f"📄 Created {len(chunks)} sentence-based chunks")
        return chunks
    
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Chunk text by paragraphs
        
        Args:
            text: Input text
        
        Returns:
            List of paragraphs
        """
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        logger.info(f"📄 Created {len(paragraphs)} paragraph chunks")
        return paragraphs
    
    def smart_chunk(
        self,
        text: str,
        max_chunk_size: Optional[int] = None
    ) -> List[str]:
        """
        Intelligently chunk text preserving sentence boundaries
        
        Args:
            text: Input text
            max_chunk_size: Maximum chunk size in words
        
        Returns:
            List of chunks
        """
        import re
        
        max_size = max_chunk_size or self.chunk_size
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            
            if current_size + sentence_words > max_size and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_words
            else:
                current_chunk.append(sentence)
                current_size += sentence_words
        
        # Add last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        logger.info(f"📄 Created {len(chunks)} smart chunks")
        return chunks


# Global chunker
text_chunker = TextChunker()


# ============================================================================
# EMBEDDING GENERATION
# ============================================================================

class EmbeddingService:
    """Generate and manage embeddings"""
    
    def __init__(self):
        self.model_manager = model_manager
        self.chunker = text_chunker
    
    def generate_embeddings_sync(
        self,
        chunks: List[str],
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Generate embeddings for text chunks (synchronous)
        
        Args:
            chunks: List of text chunks
            batch_size: Batch size for processing
        
        Returns:
            NumPy array of embeddings
        """
        try:
            if not chunks:
                logger.warning("⚠️  No chunks provided for embedding")
                return np.array([])
            
            logger.info(f"🔄 Generating embeddings for {len(chunks)} chunks...")
            
            model = self.model_manager.get_model_sync()
            
            # Generate embeddings in batches
            embeddings = model.encode(
                chunks,
                batch_size=batch_size,
                show_progress_bar=len(chunks) > 50,
                convert_to_numpy=True
            )
            
            logger.info(f"✅ Generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            raise
    
    async def generate_embeddings(
        self,
        chunks: List[str],
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Generate embeddings for text chunks (async)
        
        Args:
            chunks: List of text chunks
            batch_size: Batch size for processing
        
        Returns:
            NumPy array of embeddings
        """
        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self.generate_embeddings_sync,
                chunks,
                batch_size
            )
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Async embedding generation failed: {e}")
            raise
    
    def generate_chunk_data_sync(
        self,
        chunks: List[str],
        video_id: Optional[str] = None,
        document_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings and format as chunk data (synchronous)
        
        Args:
            chunks: List of text chunks
            video_id: Optional video ID
            document_id: Optional document ID
            user_id: Optional user ID
        
        Returns:
            List of chunk data dictionaries
        """
        try:
            embeddings = self.generate_embeddings_sync(chunks)
            
            chunk_data = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                data = {
                    "chunk_index": i,
                    "text": chunk,
                    "embedding": embedding.tolist(),
                    "created_at": datetime.utcnow()
                }
                
                if video_id:
                    data["video_id"] = video_id
                
                if document_id:
                    data["document_id"] = document_id
                
                if user_id:
                    data["user_id"] = user_id
                
                chunk_data.append(data)
            
            logger.info(f"✅ Generated {len(chunk_data)} chunk data entries")
            return chunk_data
            
        except Exception as e:
            logger.error(f"❌ Chunk data generation failed: {e}")
            raise
    
    async def generate_chunk_data(
        self,
        chunks: List[str],
        video_id: Optional[str] = None,
        document_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings and format as chunk data (async)
        
        Args:
            chunks: List of text chunks
            video_id: Optional video ID
            document_id: Optional document ID
            user_id: Optional user ID
        
        Returns:
            List of chunk data dictionaries
        """
        try:
            loop = asyncio.get_event_loop()
            chunk_data = await loop.run_in_executor(
                None,
                self.generate_chunk_data_sync,
                chunks,
                video_id,
                document_id,
                user_id
            )
            return chunk_data
            
        except Exception as e:
            logger.error(f"❌ Async chunk data generation failed: {e}")
            raise
    
    def generate_single_embedding_sync(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text (synchronous)
        
        Args:
            text: Input text
        
        Returns:
            NumPy array embedding
        """
        try:
            model = self.model_manager.get_model_sync()
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Single embedding generation failed: {e}")
            raise
    
    async def generate_single_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text (async)
        
        Args:
            text: Input text
        
        Returns:
            NumPy array embedding
        """
        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                self.generate_single_embedding_sync,
                text
            )
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Async single embedding generation failed: {e}")
            raise
    
    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
        
        Returns:
            Similarity score (0-1)
        """
        from sklearn.metrics.pairwise import cosine_similarity
        
        similarity = cosine_similarity(
            embedding1.reshape(1, -1),
            embedding2.reshape(1, -1)
        )[0][0]
        
        return float(similarity)
    
    def find_similar_chunks(
        self,
        query_embedding: np.ndarray,
        chunk_embeddings: List[np.ndarray],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Find most similar chunks to query
        
        Args:
            query_embedding: Query embedding
            chunk_embeddings: List of chunk embeddings
            top_k: Number of results to return
        
        Returns:
            List of (index, similarity_score) tuples
        """
        from sklearn.metrics.pairwise import cosine_similarity
        
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1),
            np.array(chunk_embeddings)
        )[0]
        
        # Get top k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = [
            (int(idx), float(similarities[idx]))
            for idx in top_indices
        ]
        
        return results


# Global embedding service
embedding_service = EmbeddingService()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_embedding_model():
    """Get embedding model (backward compatibility)"""
    return model_manager.get_model_sync()


def chunk_text(text: str) -> List[str]:
    """Chunk text (backward compatibility)"""
    return text_chunker.chunk_text(text)


def generate_embeddings(
    chunks: List[str],
    video_id: str = None
) -> List[Dict[str, Any]]:
    """Generate embeddings (backward compatibility)"""
    return embedding_service.generate_chunk_data_sync(
        chunks,
        video_id=video_id
    )


async def generate_embeddings_async(
    chunks: List[str],
    video_id: Optional[str] = None,
    document_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Generate embeddings asynchronously"""
    return await embedding_service.generate_chunk_data(
        chunks,
        video_id=video_id,
        document_id=document_id,
        user_id=user_id
    )


async def chunk_and_embed_async(
    text: str,
    video_id: Optional[str] = None,
    document_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Chunk text and generate embeddings in one step (async)
    
    Args:
        text: Input text
        video_id: Optional video ID
        document_id: Optional document ID
        user_id: Optional user ID
    
    Returns:
        List of chunk data with embeddings
    """
    try:
        # Chunk text
        chunks = text_chunker.chunk_text(text)
        
        # Generate embeddings
        chunk_data = await embedding_service.generate_chunk_data(
            chunks,
            video_id=video_id,
            document_id=document_id,
            user_id=user_id
        )
        
        return chunk_data
        
    except Exception as e:
        logger.error(f"❌ Chunk and embed failed: {e}")
        raise


async def generate_query_embedding_async(query: str) -> np.ndarray:
    """
    Generate embedding for a query (async)
    
    Args:
        query: Query text
    
    Returns:
        Query embedding
    """
    return await embedding_service.generate_single_embedding(query)


def get_embedding_model_info() -> Dict[str, Any]:
    """Get embedding model information"""
    return model_manager.get_model_info()
