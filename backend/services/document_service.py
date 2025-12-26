# services/document_service.py - DOCUMENT SERVICE

from typing import List, Dict, Optional
import time
from config.logging_config import logger
from database.database import get_db


class DocumentService:
    """Service for managing document metadata"""
    
    def __init__(self):
        """Initialize document service"""
        self.db = get_db()
    
    async def create_document(
        self,
        document_id: str,
        user_id: str,
        title: str,
        description: Optional[str],
        file_name: str,
        file_type: str,
        file_size: int,
        file_url: str
    ) -> Dict:
        """
        Create document record
        
        Args:
            document_id: Unique document ID
            user_id: User ID
            title: Document title
            description: Optional description
            file_name: Original file name
            file_type: MIME type
            file_size: File size in bytes
            file_url: Storage URL
        
        Returns:
            Created document
        """
        try:
            timestamp = time.time()
            
            document = {
                "document_id": document_id,
                "user_id": user_id,
                "title": title,
                "description": description,
                "file_name": file_name,
                "file_type": file_type,
                "file_size": file_size,
                "file_url": file_url,
                "status": "active",
                "created_at": timestamp,
                "updated_at": timestamp
            }
            
            await self.db.documents.insert_one(document)
            
            logger.info(f"Document created: {document_id}")
            return document
        
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise
    
    async def get_document(
        self,
        document_id: str,
        user_id: str
    ) -> Optional[Dict]:
        """
        Get document by ID
        
        Args:
            document_id: Document ID
            user_id: User ID
        
        Returns:
            Document or None
        """
        try:
            document = await self.db.documents.find_one({
                "document_id": document_id,
                "user_id": user_id
            })
            
            return document
        
        except Exception as e:
            logger.error(f"Error fetching document: {e}")
            return None
    
    async def get_user_documents(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        file_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict]:
        """
        Get user's documents
        
        Args:
            user_id: User ID
            limit: Number to return
            offset: Pagination offset
            file_type: Filter by file type
            search: Search query
        
        Returns:
            List of documents
        """
        try:
            query = {"user_id": user_id, "status": "active"}
            
            if file_type:
                query["file_type"] = file_type
            
            if search:
                query["$or"] = [
                    {"title": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]
            
            documents = await self.db.documents.find(query).sort(
                "created_at", -1
            ).skip(offset).limit(limit).to_list(length=limit)
            
            return documents
        
        except Exception as e:
            logger.error(f"Error fetching documents: {e}")
            return []
    
    async def count_user_documents(
        self,
        user_id: str,
        file_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> int:
        """
        Count user's documents
        
        Args:
            user_id: User ID
            file_type: Filter by file type
            search: Search query
        
        Returns:
            Document count
        """
        try:
            query = {"user_id": user_id, "status": "active"}
            
            if file_type:
                query["file_type"] = file_type
            
            if search:
                query["$or"] = [
                    {"title": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]
            
            count = await self.db.documents.count_documents(query)
            return count
        
        except Exception as e:
            logger.error(f"Error counting documents: {e}")
            return 0
    
    async def update_document(
        self,
        document_id: str,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Update document metadata
        
        Args:
            document_id: Document ID
            user_id: User ID
            title: New title
            description: New description
        
        Returns:
            Updated document
        """
        try:
            update_fields = {"updated_at": time.time()}
            
            if title is not None:
                update_fields["title"] = title
            
            if description is not None:
                update_fields["description"] = description
            
            result = await self.db.documents.find_one_and_update(
                {"document_id": document_id, "user_id": user_id},
                {"$set": update_fields},
                return_document=True
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            return None
    
    async def delete_document(
        self,
        document_id: str,
        user_id: str
    ):
        """
        Delete document
        
        Args:
            document_id: Document ID
            user_id: User ID
        """
        try:
            await self.db.documents.delete_one({
                "document_id": document_id,
                "user_id": user_id
            })
            
            logger.info(f"Document deleted: {document_id}")
        
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise
