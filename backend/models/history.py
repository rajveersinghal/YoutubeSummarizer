# models/history.py
from database.connection import db_connection  # ✅ Changed
from datetime import datetime

def save_history(user_id: str, video_id: str, title: str, summary: str, mode: str):
    """Save to history"""
    db = db_connection.db  # ✅ Changed
    
    history_doc = {
        'userId': user_id,
        'videoId': video_id,
        'title': title,
        'summary': summary,
        'mode': mode,
        'createdAt': datetime.utcnow()
    }
    
    db.history.insert_one(history_doc)

def get_all_history(user_id: str, limit: int = 50):
    """Get user history"""
    db = db_connection.db  # ✅ Changed
    return list(db.history.find({'userId': user_id}).sort('createdAt', -1).limit(limit))

def get_history_by_video(user_id: str, video_id: str):
    """Get history for specific video"""
    db = db_connection.db  # ✅ Changed
    return list(db.history.find({'userId': user_id, 'videoId': video_id}).sort('createdAt', -1))
