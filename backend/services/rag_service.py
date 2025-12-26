# backend/services/rag_service.py - COMPLETE RAG SYSTEM

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import uuid
from config.logging_config import logger

class RAGService:
    """RAG Service for document and video embeddings"""
    
    def __init__(self):
        """Initialize RAG with ChromaDB and embeddings"""
        try:
            # Initialize ChromaDB
            self.chroma_client = chromadb.Client(ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            ))
            
            # Get or create collections
            self.doc_collection = self.chroma_client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
            
            self.video_collection = self.chroma_client.get_or_create_collection(
                name="videos",
                metadata={"hnsw:space": "cosine"}
            )
            
            # Initialize embedding model
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            
            logger.info("✅ RAG Service initialized")
            
        except Exception as e:
            logger.error(f"❌ RAG initialization failed: {e}")
            raise
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk (words)
            overlap: Overlap between chunks (words)
            
        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        logger.info(f"📚 Created {len(chunks)} chunks from text")
        return chunks
    
    def add_document(
        self,
        document_id: str,
        title: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add document to vector database
        
        Args:
            document_id: Unique document ID
            title: Document title
            content: Document content
            metadata: Additional metadata
        """
        try:
            # Chunk the content
            chunks = self.chunk_text(content, chunk_size=500, overlap=50)
            
            # Generate embeddings
            embeddings = self.embedder.encode(chunks).tolist()
            
            # Create IDs for each chunk
            chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
            
            # Create metadata for each chunk
            metadatas = []
            for i, chunk in enumerate(chunks):
                meta = {
                    "document_id": document_id,
                    "title": title,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "type": "document"
                }
                if metadata:
                    meta.update(metadata)
                metadatas.append(meta)
            
            # Add to collection
            self.doc_collection.add(
                ids=chunk_ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"✅ Added document {document_id} ({len(chunks)} chunks)")
            
        except Exception as e:
            logger.error(f"❌ Failed to add document: {e}")
            raise
    
    def add_video(
        self,
        video_id: str,
        title: str,
        transcript: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add video transcript to vector database
        
        Args:
            video_id: Unique video ID
            title: Video title
            transcript: Video transcript
            metadata: Additional metadata
        """
        try:
            # Chunk the transcript
            chunks = self.chunk_text(transcript, chunk_size=500, overlap=50)
            
            # Generate embeddings
            embeddings = self.embedder.encode(chunks).tolist()
            
            # Create IDs for each chunk
            chunk_ids = [f"{video_id}_chunk_{i}" for i in range(len(chunks))]
            
            # Create metadata for each chunk
            metadatas = []
            for i, chunk in enumerate(chunks):
                meta = {
                    "video_id": video_id,
                    "title": title,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "type": "video"
                }
                if metadata:
                    meta.update(metadata)
                metadatas.append(meta)
            
            # Add to collection
            self.video_collection.add(
                ids=chunk_ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"✅ Added video {video_id} ({len(chunks)} chunks)")
            
        except Exception as e:
            logger.error(f"❌ Failed to add video: {e}")
            raise
    
    def search_documents(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Search for relevant document chunks
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of relevant chunks with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embedder.encode([query])[0].tolist()
            
            # Search in document collection
            results = self.doc_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    })
            
            logger.info(f"🔍 Found {len(formatted_results)} relevant document chunks")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Document search failed: {e}")
            return []
    
    def search_videos(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Search for relevant video chunks
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of relevant chunks with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embedder.encode([query])[0].tolist()
            
            # Search in video collection
            results = self.video_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    })
            
            logger.info(f"🔍 Found {len(formatted_results)} relevant video chunks")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Video search failed: {e}")
            return []
    
    def search_all(self, query: str, n_results: int = 5) -> Dict[str, List[Dict]]:
        """
        Search across both documents and videos
        
        Args:
            query: Search query
            n_results: Number of results per collection
            
        Returns:
            Dictionary with document and video results
        """
        return {
            "documents": self.search_documents(query, n_results),
            "videos": self.search_videos(query, n_results)
        }
    
    def delete_document(self, document_id: str):
        """Delete all chunks of a document"""
        try:
            # Get all chunk IDs for this document
            results = self.doc_collection.get(
                where={"document_id": document_id}
            )
            
            if results['ids']:
                self.doc_collection.delete(ids=results['ids'])
                logger.info(f"✅ Deleted document {document_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document: {e}")
    
    def delete_video(self, video_id: str):
        """Delete all chunks of a video"""
        try:
            # Get all chunk IDs for this video
            results = self.video_collection.get(
                where={"video_id": video_id}
            )
            
            if results['ids']:
                self.video_collection.delete(ids=results['ids'])
                logger.info(f"✅ Deleted video {video_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to delete video: {e}")
