# backend/services/vector_store.py
from typing import List, Dict
import numpy as np
import faiss

class VectorStore:
    """
    In-memory vector store with FAISS
    Compatible with faiss-cpu >= 1.8.0
    """
    def __init__(self):
        self.indexes = {}      # video_id -> faiss.IndexFlatL2
        self.metadata = {}     # video_id -> list[chunk_metadata]
        self.dim = 384  # Default dimension for all-MiniLM-L6-v2

    def add_vectors(self, chunk_data: List[Dict]):
        """
        chunk_data: list of { video_id, chunk_index, text, embedding }
        """
        if not chunk_data:
            return

        video_id = chunk_data[0]["video_id"]
        
        # Stack embeddings
        vecs = np.stack([c["embedding"] for c in chunk_data]).astype("float32")
        
        # Update dimension if needed
        if self.dim is None or self.dim != vecs.shape[1]:
            self.dim = vecs.shape[1]

        # Create or get index
        if video_id not in self.indexes:
            # Create new index
            index = faiss.IndexFlatL2(self.dim)
            self.indexes[video_id] = index
            self.metadata[video_id] = []
        else:
            index = self.indexes[video_id]

        # Add vectors to index
        index.add(vecs)
        self.metadata[video_id].extend(chunk_data)
        
        print(f"✅ Added {len(vecs)} vectors to FAISS index for video {video_id}")

    def search(self, video_id: str, query_vec: np.ndarray, top_k: int = 5) -> List[Dict]:
        """
        Return top_k most similar chunks for a given video
        """
        if video_id not in self.indexes:
            print(f"⚠️  No index found for video {video_id}")
            return []

        index = self.indexes[video_id]
        
        # Ensure query vector is correct shape
        query_vec = query_vec.astype("float32").reshape(1, -1)
        
        # Perform search
        distances, indices = index.search(query_vec, min(top_k, index.ntotal))

        # Retrieve metadata
        chunks = []
        meta_list = self.metadata[video_id]
        for idx in indices[0]:
            if 0 <= idx < len(meta_list):
                chunks.append(meta_list[idx])
        
        return chunks
    
    def get_index_info(self, video_id: str) -> dict:
        """Get information about a specific index"""
        if video_id not in self.indexes:
            return None
        
        return {
            "video_id": video_id,
            "total_vectors": self.indexes[video_id].ntotal,
            "dimension": self.dim,
            "chunks": len(self.metadata.get(video_id, []))
        }
