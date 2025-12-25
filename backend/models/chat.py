# models/chat.py
from database.connection import db_connection  # ✅ Changed
from datetime import datetime
import uuid

def create_chat(user_id: str, text: str = None, title: str = "New Chat"):
    """Create new chat"""
    db = db_connection.db  # ✅ Changed
    chat_id = str(uuid.uuid4())
    
    chat_doc = {
        'chatId': chat_id,
        'userId': user_id,
        'title': title,
        'history': [],
        'createdAt': datetime.utcnow()
    }
    
    if text:
        chat_doc['history'].append({
            'role': 'user',
            'content': text,
            'timestamp': datetime.utcnow()
        })
    
    db.chats.insert_one(chat_doc)
    return chat_id

def get_chat(chat_id: str, user_id: str):
    """Get chat by ID"""
    db = db_connection.db  # ✅ Changed
    return db.chats.find_one({'chatId': chat_id, 'userId': user_id})

def add_to_chat(chat_id: str, user_id: str, question: str, answer: str):
    """Add message to chat"""
    db = db_connection.db  # ✅ Changed
    
    db.chats.update_one(
        {'chatId': chat_id, 'userId': user_id},
        {'$push': {
            'history': {
                '$each': [
                    {'role': 'user', 'content': question, 'timestamp': datetime.utcnow()},
                    {'role': 'assistant', 'content': answer, 'timestamp': datetime.utcnow()}
                ]
            }
        }}
    )

def delete_chat(chat_id: str, user_id: str):
    """Delete chat"""
    db = db_connection.db  # ✅ Changed
    result = db.chats.delete_one({'chatId': chat_id, 'userId': user_id})
    return result.deleted_count > 0
