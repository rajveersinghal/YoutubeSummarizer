# services/embedding_service.py
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from config.settings import settings
from config.logging_config import logger

_model = None

def get_embedding_model():
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model

def chunk_text(text: str) -> List[str]:
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), settings.CHUNK_SIZE - settings.CHUNK_OVERLAP):
        chunk = ' '.join(words[i:i + settings.CHUNK_SIZE])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks

def generate_embeddings(chunks: List[str], video_id: str) -> List[Dict]:
    try:
        model = get_embedding_model()
        embeddings = model.encode(chunks)
        
        chunk_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_data.append({
                "video_id": video_id,
                "chunk_index": i,
                "text": chunk,
                "embedding": embedding
            })
        
        return chunk_data
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise
