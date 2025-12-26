# backend/routes/documents.py - DOCUMENT ROUTES

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from typing import Optional
import time
import uuid
from pathlib import Path

from middleware.auth import get_current_user
from database.database import get_db
from config.settings import settings
from config.logging_config import logger
from services.document_processor import DocumentProcessor

router = APIRouter(prefix="/api/documents", tags=["Documents"])
doc_processor = DocumentProcessor()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """Upload and process a document"""
    try:
        logger.info(f"📄 Uploading document: {file.filename}")
        
        # Validate file type
        allowed_types = ['application/pdf', 'text/plain']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and TXT files are allowed"
            )
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Save file
        doc_dir = Path(settings.STORAGE_PATH) / "documents"
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        file_extension = Path(file.filename).suffix
        file_path = doc_dir / f"{document_id}{file_extension}"
        
        file_content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Extract text
        if file.content_type == 'application/pdf':
            content = await doc_processor.process_pdf(str(file_path))
        else:
            content = await doc_processor.process_text(str(file_path))
        
        # Save to database
        doc_doc = {
            "document_id": document_id,
            "user_id": user_id,
            "title": title,
            "description": description,
            "file_path": str(file_path),
            "file_name": file.filename,
            "file_size": len(file_content),
            "content": content,
            "status": "completed",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        
        db.documents.insert_one(doc_doc)
        
        # Create conversation with document context
        conversation_id = str(uuid.uuid4())
        conversation_doc = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "title": f"📄 {title}",
            "created_at": time.time(),
            "updated_at": time.time(),
            "message_count": 0,
            "context_type": "document",
            "context_id": document_id,
        }
        
        db.conversations.insert_one(conversation_doc)
        
        logger.info(f"✅ Document uploaded: {document_id}")
        
        return {
            "success": True,
            "document_id": document_id,
            "conversation_id": conversation_id,
            "title": title,
            "content_length": len(content),
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Document upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )

@router.get("/")
async def get_all_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all documents"""
    try:
        skip = (page - 1) * page_size
        
        documents = list(
            db.documents
            .find({"user_id": user_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        
        total = db.documents.count_documents({"user_id": user_id})
        
        formatted_docs = []
        for doc in documents:
            formatted_docs.append({
                "document_id": doc.get("document_id"),
                "title": doc.get("title"),
                "file_name": doc.get("file_name"),
                "status": doc.get("status"),
                "created_at": doc.get("created_at"),
            })
        
        return {
            "success": True,
            "documents": formatted_docs,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting documents: {e}")
        return {
            "success": True,
            "documents": [],
            "total": 0,
            "page": page,
            "page_size": page_size
        }

__all__ = ["router"]
