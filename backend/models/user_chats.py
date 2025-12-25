# models/user_chats.py
from database.connection import db_connection  # ✅ Changed
from datetime import datetime

def add_user_chat(user_id: str, chat_id: str, title: str):
    """Add chat to user's chat list"""
    db = db_connection.db  # ✅ Changed
    
    db.user_chats.update_one(
        {'userId': user_id},
        {
            '$push': {
                'chats': {
                    'chatId': chat_id,
                    'title': title,
                    'createdAt': datetime.utcnow()
                }
            }
        },
        upsert=True
    )

def get_user_chats(user_id: str):
    """Get all chats for user"""
    db = db_connection.db  # ✅ Changed
    user_doc = db.user_chats.find_one({'userId': user_id})
    
    if user_doc and 'chats' in user_doc:
        return user_doc['chats']
    return []

def remove_user_chat(user_id: str, chat_id: str):
    """Remove chat from user's list"""
    db = db_connection.db  # ✅ Changed
    
    db.user_chats.update_one(
        {'userId': user_id},
        {'$pull': {'chats': {'chatId': chat_id}}}
    )

def delete_all_user_chats(user_id: str):
    """Delete all user chats"""
    db = db_connection.db  # ✅ Changed
    db.user_chats.delete_one({'userId': user_id})
