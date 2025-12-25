# models/chunk.py
from database.connection import db_connection  # ✅ Changed
from config.logging_config import logger

def save_chunks(video_id: str, chunk_data: list):
    """Save chunks to MongoDB"""
    try:
        db = db_connection.db  # ✅ Changed
        
        chunks = []
        for chunk in chunk_data:
            chunks.append({
                'videoId': video_id,
                'text': chunk['text'],
                'chunkIndex': chunk['chunk_index']
            })
        
        if chunks:
            db.chunks.insert_many(chunks)
            logger.info(f"💾 Saved {len(chunks)} chunks to MongoDB")
        
    except Exception as e:
        logger.error(f"Failed to save chunks: {e}")
        raise

def get_chunks_by_video(video_id: str):
    """Get all chunks for a video"""
    try:
        db = db_connection.db  # ✅ Changed
        chunks = list(db.chunks.find({'videoId': video_id}).sort('chunkIndex', 1))
        return chunks
    except Exception as e:
        logger.error(f"Failed to get chunks: {e}")
        return []
