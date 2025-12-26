# routes/documents.py - FASTAPI DOCUMENT ROUTES
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Form
from typing import List, Optional
import os
from pathlib import Path

from models.document import (
    save_document,
    get_document_by_id,
    get_user_documents,
    get_user_document_count,
    update_document,
    delete_document,
    search_documents,
    get_document_stats,
    check_document_exists,
    SaveDocumentRequest,
    UpdateDocumentRequest
)
from models.chunk import (
    save_chunks,
    get_chunks_by_document,
    delete_chunks_by_document
)
from services.document_processor import (
    process_pdf,
    process_text_file,
    process_docx,
    extract_text_from_file
)
from services.embedding_service import chunk_and_embed_async
from services.vector_store import vector_store
from core.auth import get_current_user
from core.responses import (
    success_response,
    created_response,
    not_found_response,
    no_content_response,
    error_response
)
from config.settings import settings
from config.logging_config import logger

router = APIRouter(prefix="/api/documents", tags=["documents"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.doc', '.md'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """
    Validate uploaded file
    
    Returns:
        (is_valid, error_message)
    """
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    
    return True, ""


async def save_uploaded_file(file: UploadFile, document_id: str) -> str:
    """
    Save uploaded file to disk
    
    Returns:
        File path
    """
    try:
        # Create documents directory
        docs_dir = settings.DOCUMENTS_DIR
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate file path
        file_ext = Path(file.filename).suffix
        file_path = docs_dir / f"{document_id}{file_ext}"
        
        # Save file
        contents = await file.read()
        
        # Check file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        with open(file_path, 'wb') as f:
            f.write(contents)
        
        logger.info(f"💾 Saved file: {file_path}")
        return str(file_path)
        
    except Exception as e:
        logger.error(f"❌ Failed to save file: {e}")
        raise


# ============================================================================
# DOCUMENT UPLOAD & PROCESSING
# ============================================================================

@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    process_immediately: bool = Form(True),
    user_id: str = Depends(get_current_user)
):
    """
    Upload a document
    
    - **file**: Document file (PDF, TXT, DOCX, MD)
    - **title**: Optional document title
    - **description**: Optional description
    - **process_immediately**: Process document immediately
    """
    try:
        # Validate file
        is_valid, error_msg = validate_file(file)
        if not is_valid:
            return error_response(error_msg, 400)
        
        logger.info(f"📤 Uploading document: {file.filename}")
        
        # Generate document ID
        import uuid
        document_id = f"doc_{str(uuid.uuid4())[:8]}"
        
        # Save file
        file_path = await save_uploaded_file(file, document_id)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        file_type = Path(file.filename).suffix.lower()
        
        # Use filename as title if not provided
        doc_title = title or Path(file.filename).stem
        
        # Save document to database
        await save_document(
            user_id=user_id,
            document_id=document_id,
            title=doc_title,
            description=description,
            file_path=file_path,
            file_name=file.filename,
            file_type=file_type,
            file_size=file_size
        )
        
        # Process document if requested
        if process_immediately:
            try:
                # Extract text
                text = await extract_text_from_file(file_path)
                
                # Update document with text
                await update_document(
                    user_id=user_id,
                    document_id=document_id,
                    updates={
                        'text': text,
                        'processingStatus': 'completed'
                    }
                )
                
                # Generate embeddings
                chunk_data = await chunk_and_embed_async(
                    text,
                    document_id=document_id,
                    user_id=user_id
                )
                
                # Save chunks to database
                await save_chunks(document_id, chunk_data, user_id)
                
                # Add to vector store
                vector_store.add_vectors(chunk_data)
                
                # Update chunk count
                await update_document(
                    user_id=user_id,
                    document_id=document_id,
                    updates={'chunkCount': len(chunk_data)}
                )
                
                logger.info(f"✅ Document processed: {document_id} ({len(chunk_data)} chunks)")
                
                return created_response(
                    data={
                        "documentId": document_id,
                        "title": doc_title,
                        "fileType": file_type,
                        "fileSize": file_size,
                        "chunks": len(chunk_data),
                        "status": "completed"
                    },
                    message="Document uploaded and processed successfully",
                    resource_id=document_id
                )
                
            except Exception as e:
                logger.error(f"❌ Processing failed: {e}")
                
                # Update status to failed
                await update_document(
                    user_id=user_id,
                    document_id=document_id,
                    updates={'processingStatus': 'failed'}
                )
                
                return created_response(
                    data={
                        "documentId": document_id,
                        "title": doc_title,
                        "status": "failed",
                        "error": str(e)
                    },
                    message="Document uploaded but processing failed",
                    resource_id=document_id
                )
        
        else:
            # Just upload without processing
            return created_response(
                data={
                    "documentId": document_id,
                    "title": doc_title,
                    "fileType": file_type,
                    "fileSize": file_size,
                    "status": "pending"
                },
                message="Document uploaded successfully",
                resource_id=document_id
            )
        
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        return error_response(str(e), 500)


@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Process an uploaded document
    
    - **document_id**: Document ID
    """
    try:
        # Get document
        document = await get_document_by_id(user_id, document_id)
        
        if not document:
            return not_found_response("Document", document_id)
        
        # Check if already processed
        if document.get('processingStatus') == 'completed':
            return error_response("Document already processed", 400)
        
        file_path = document.get('filePath')
        
        if not file_path or not os.path.exists(file_path):
            return error_response("Document file not found", 404)
        
        logger.info(f"🔄 Processing document: {document_id}")
        
        # Update status to processing
        await update_document(
            user_id=user_id,
            document_id=document_id,
            updates={'processingStatus': 'processing'}
        )
        
        # Extract text
        text = await extract_text_from_file(file_path)
        
        # Update document with text
        await update_document(
            user_id=user_id,
            document_id=document_id,
            updates={'text': text}
        )
        
        # Generate embeddings
        chunk_data = await chunk_and_embed_async(
            text,
            document_id=document_id,
            user_id=user_id
        )
        
        # Save chunks
        await save_chunks(document_id, chunk_data, user_id)
        
        # Add to vector store
        vector_store.add_vectors(chunk_data)
        
        # Update document
        await update_document(
            user_id=user_id,
            document_id=document_id,
            updates={
                'chunkCount': len(chunk_data),
                'processingStatus': 'completed'
            }
        )
        
        logger.info(f"✅ Document processed: {document_id}")
        
        return success_response(
            data={
                "documentId": document_id,
                "chunks": len(chunk_data),
                "status": "completed"
            },
            message="Document processed successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        
        # Update status to failed
        await update_document(
            user_id=user_id,
            document_id=document_id,
            updates={'processingStatus': 'failed'}
        )
        
        return error_response(str(e), 500)


# ============================================================================
# DOCUMENT MANAGEMENT
# ============================================================================

@router.get("")
async def get_documents(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """
    Get all documents for user
    
    - **limit**: Maximum documents to return
    - **skip**: Number to skip (pagination)
    - **status**: Filter by processing status
    """
    try:
        documents = await get_user_documents(user_id, limit, skip, status)
        total = await get_user_document_count(user_id)
        
        return success_response(
            data={
                "documents": documents,
                "total": total,
                "count": len(documents)
            },
            message=f"Retrieved {len(documents)} documents"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get documents: {e}")
        return error_response(str(e), 500)


@router.get("/stats")
async def get_stats(user_id: str = Depends(get_current_user)):
    """Get document statistics"""
    
    try:
        stats = await get_document_stats(user_id)
        
        return success_response(data=stats)
        
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        return error_response(str(e), 500)


@router.get("/search")
async def search_user_documents(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user)
):
    """
    Search documents by title or description
    
    - **q**: Search query
    - **limit**: Maximum results
    """
    try:
        documents = await search_documents(user_id, q, limit)
        
        return success_response(
            data={
                "documents": documents,
                "count": len(documents)
            },
            message=f"Found {len(documents)} matching documents"
        )
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        return error_response(str(e), 500)


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    include_text: bool = Query(False),
    user_id: str = Depends(get_current_user)
):
    """
    Get specific document
    
    - **document_id**: Document ID
    - **include_text**: Include full text in response
    """
    try:
        document = await get_document_by_id(user_id, document_id)
        
        if not document:
            return not_found_response("Document", document_id)
        
        # Remove text if not requested
        if not include_text and 'text' in document:
            document['textLength'] = len(document.get('text', ''))
            del document['text']
        
        return success_response(
            data=document,
            message="Document retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get document: {e}")
        return error_response(str(e), 500)


@router.patch("/{document_id}")
async def update_document_info(
    document_id: str,
    data: UpdateDocumentRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Update document information
    
    - **document_id**: Document ID
    - **title**: New title
    - **description**: New description
    """
    try:
        updates = {}
        if data.title is not None:
            updates['title'] = data.title
        if data.description is not None:
            updates['description'] = data.description
        
        success = await update_document(user_id, document_id, updates)
        
        if not success:
            return not_found_response("Document", document_id)
        
        return success_response(message="Document updated successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to update document: {e}")
        return error_response(str(e), 500)


@router.delete("/{document_id}", status_code=204)
async def remove_document(
    document_id: str,
    delete_file: bool = Query(True),
    user_id: str = Depends(get_current_user)
):
    """
    Delete a document
    
    - **document_id**: Document ID
    - **delete_file**: Also delete the file from disk
    """
    try:
        # Get document to get file path
        document = await get_document_by_id(user_id, document_id)
        
        if not document:
            return not_found_response("Document", document_id)
        
        # Delete from database
        deleted = await delete_document(user_id, document_id)
        
        if not deleted:
            return not_found_response("Document", document_id)
        
        # Delete chunks
        await delete_chunks_by_document(document_id, user_id)
        
        # Delete from vector store
        vector_store.delete_index(document_id)
        
        # Delete file if requested
        if delete_file:
            file_path = document.get('filePath')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"🗑️  Deleted file: {file_path}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to delete file: {e}")
        
        return no_content_response()
        
    except Exception as e:
        logger.error(f"❌ Failed to delete document: {e}")
        return error_response(str(e), 500)


# ============================================================================
# DOCUMENT CHUNKS
# ============================================================================

@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    limit: int = Query(100, ge=1, le=500),
    include_embeddings: bool = Query(False),
    user_id: str = Depends(get_current_user)
):
    """
    Get chunks for a document
    
    - **document_id**: Document ID
    - **limit**: Maximum chunks to return
    - **include_embeddings**: Include embedding vectors
    """
    try:
        # Verify document exists
        document = await get_document_by_id(user_id, document_id)
        
        if not document:
            return not_found_response("Document", document_id)
        
        chunks = await get_chunks_by_document(
            document_id,
            limit=limit,
            include_embeddings=include_embeddings
        )
        
        return success_response(
            data={
                "chunks": chunks,
                "count": len(chunks)
            },
            message=f"Retrieved {len(chunks)} chunks"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get chunks: {e}")
        return error_response(str(e), 500)


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Download original document file
    
    - **document_id**: Document ID
    """
    try:
        from fastapi.responses import FileResponse
        
        document = await get_document_by_id(user_id, document_id)
        
        if not document:
            return not_found_response("Document", document_id)
        
        file_path = document.get('filePath')
        
        if not file_path or not os.path.exists(file_path):
            return error_response("Document file not found", 404)
        
        file_name = document.get('fileName', 'document')
        
        return FileResponse(
            path=file_path,
            filename=file_name,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        return error_response(str(e), 500)
