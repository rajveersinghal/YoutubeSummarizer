# routes/videos.py - FASTAPI VIDEO ROUTES
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
import uuid

from models.video import (
    save_video,
    get_video_by_id,
    get_user_videos,
    get_user_video_count,
    update_video,
    update_video_chunk_count,
    update_video_embedding_status,
    delete_video,
    search_videos,
    get_video_stats,
    check_video_exists,
    get_recent_videos,
    SaveVideoRequest
)
from models.chunk import (
    save_chunks,
    get_chunks_by_video,
    delete_chunks_by_video
)
from models.history import add_history_entry
from services.youtube_captions import get_youtube_captions_async
from services.audio_extractor import (
    extract_youtube_audio_async,
    get_youtube_video_info_async,
    delete_youtube_audio_async
)
from services.transcription_service import transcribe_audio_async
from services.embedding_service import chunk_and_embed_async
from services.vector_store import vector_store
from services.rag_service import answer_question_async, summarize_video_async
from utils.validators import validate_youtube_url
from core.auth import get_current_user
from core.responses import (
    success_response,
    created_response,
    not_found_response,
    no_content_response,
    error_response,
    accepted_response
)
from config.logging_config import logger


router = APIRouter(prefix="/api/videos", tags=["videos"])


# ============================================================================
# VIDEO PROCESSING
# ============================================================================

@router.post("/process", status_code=201)
async def process_youtube_video(
    url: str,
    background_tasks: BackgroundTasks,
    use_captions: bool = Query(True, description="Try captions first"),
    process_async: bool = Query(False, description="Process in background"),
    user_id: str = Depends(get_current_user)
):
    """
    Process a YouTube video
    
    - **url**: YouTube video URL
    - **use_captions**: Try to get captions first (faster)
    - **process_async**: Process in background and return immediately
    """
    try:
        # Validate and extract video ID
        video_id = validate_youtube_url(url)
        
        # Check if already processed
        exists = await check_video_exists(user_id, video_id)
        if exists:
            return error_response("Video already processed", 400)
        
        logger.info(f"🎬 Processing video: {video_id}")
        
        # Get video info
        try:
            video_info = await get_youtube_video_info_async(video_id)
        except Exception as e:
            logger.warning(f"⚠️  Failed to get video info: {e}")
            video_info = {}
        
        # If async processing, return immediately
        if process_async:
            task_id = str(uuid.uuid4())
            
            background_tasks.add_task(
                process_video_background,
                video_id=video_id,
                url=url,
                user_id=user_id,
                video_info=video_info,
                use_captions=use_captions
            )
            
            return accepted_response(
                message="Video processing started",
                task_id=task_id,
                data={
                    "videoId": video_id,
                    "title": video_info.get('title'),
                    "status": "processing"
                }
            )
        
        # Synchronous processing
        transcript = None
        source = None
        
        # Try captions first if enabled
        if use_captions:
            logger.info("📝 Attempting to get captions...")
            caption_result = await get_youtube_captions_async(video_id)
            
            if caption_result:
                transcript = caption_result['transcript']
                source = f"youtube_captions_{caption_result['type']}"
                logger.info(f"✅ Got captions ({caption_result['type']})!")
        
        # Fallback to Whisper transcription
        if not transcript:
            logger.info("🎤 Using Whisper transcription...")
            
            # Extract audio
            audio_path = await extract_youtube_audio_async(video_id)
            
            # Transcribe
            transcript = await transcribe_audio_async(audio_path)
            source = "whisper_transcription"
        
        # Save video
        await save_video(
            user_id=user_id,
            video_id=video_id,
            url=url,
            transcript=transcript,
            title=video_info.get('title'),
            description=video_info.get('description'),
            thumbnail=video_info.get('thumbnail'),
            duration=video_info.get('duration'),
            channel_name=video_info.get('channelName'),
            source=source
        )
        
        # Generate embeddings
        logger.info("🔄 Generating embeddings...")
        
        chunk_data = await chunk_and_embed_async(
            transcript,
            video_id=video_id,
            user_id=user_id
        )
        
        # Save chunks
        await save_chunks(video_id, chunk_data, user_id)
        
        # Add to vector store
        vector_store.add_vectors(chunk_data)
        
        # Update video with chunk count
        await update_video_chunk_count(user_id, video_id, len(chunk_data))
        await update_video_embedding_status(user_id, video_id, 'completed')
        
        # Add to history
        await add_history_entry(
            user_id=user_id,
            action="process",
            resource_type="video",
            resource_id=video_id,
            metadata={"source": source}
        )
        
        logger.info(f"✅ Video processed successfully: {video_id}")
        
        return created_response(
            data={
                "videoId": video_id,
                "title": video_info.get('title'),
                "source": source,
                "chunks": len(chunk_data),
                "transcriptLength": len(transcript),
                "status": "completed"
            },
            message="Video processed successfully",
            resource_id=video_id
        )
        
    except Exception as e:
        logger.error(f"❌ Video processing failed: {e}")
        return error_response(str(e), 500)


async def process_video_background(
    video_id: str,
    url: str,
    user_id: str,
    video_info: Dict[str, Any],
    use_captions: bool
):
    """Background task for video processing"""
    try:
        transcript = None
        source = None
        
        # Try captions
        if use_captions:
            caption_result = await get_youtube_captions_async(video_id)
            if caption_result:
                transcript = caption_result['transcript']
                source = f"youtube_captions_{caption_result['type']}"
        
        # Fallback to Whisper
        if not transcript:
            audio_path = await extract_youtube_audio_async(video_id)
            transcript = await transcribe_audio_async(audio_path)
            source = "whisper_transcription"
        
        # Save video
        await save_video(
            user_id=user_id,
            video_id=video_id,
            url=url,
            transcript=transcript,
            title=video_info.get('title'),
            description=video_info.get('description'),
            thumbnail=video_info.get('thumbnail'),
            duration=video_info.get('duration'),
            channel_name=video_info.get('channelName'),
            source=source
        )
        
        # Generate embeddings
        chunk_data = await chunk_and_embed_async(
            transcript,
            video_id=video_id,
            user_id=user_id
        )
        
        # Save chunks and update
        await save_chunks(video_id, chunk_data, user_id)
        vector_store.add_vectors(chunk_data)
        await update_video_chunk_count(user_id, video_id, len(chunk_data))
        await update_video_embedding_status(user_id, video_id, 'completed')
        
        logger.info(f"✅ Background processing completed: {video_id}")
        
    except Exception as e:
        logger.error(f"❌ Background processing failed: {e}")
        await update_video_embedding_status(user_id, video_id, 'failed')


# ============================================================================
# VIDEO MANAGEMENT
# ============================================================================

@router.get("")
async def get_videos(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    source: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """
    Get all videos for user
    
    - **limit**: Maximum videos to return
    - **skip**: Number to skip (pagination)
    - **source**: Filter by transcript source
    """
    try:
        videos = await get_user_videos(user_id, limit, skip)
        total = await get_user_video_count(user_id)
        
        return success_response(
            data={
                "videos": videos,
                "total": total,
                "count": len(videos)
            },
            message=f"Retrieved {len(videos)} videos"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get videos: {e}")
        return error_response(str(e), 500)


@router.get("/stats")
async def get_stats(user_id: str = Depends(get_current_user)):
    """Get video statistics"""
    
    try:
        stats = await get_video_stats(user_id)
        
        return success_response(
            data=stats,
            message="Video statistics retrieved"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        return error_response(str(e), 500)


@router.get("/recent")
async def get_recent(
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user)
):
    """
    Get recent videos
    
    - **limit**: Number of videos to return
    """
    try:
        videos = await get_recent_videos(user_id, limit)
        
        return success_response(
            data={"videos": videos, "count": len(videos)},
            message=f"Retrieved {len(videos)} recent videos"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get recent videos: {e}")
        return error_response(str(e), 500)


@router.get("/search")
async def search_user_videos(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user)
):
    """
    Search videos by title or description
    
    - **q**: Search query
    - **limit**: Maximum results
    """
    try:
        videos = await search_videos(user_id, q, limit)
        
        return success_response(
            data={"videos": videos, "count": len(videos)},
            message=f"Found {len(videos)} matching videos"
        )
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        return error_response(str(e), 500)


@router.get("/{video_id}")
async def get_video(
    video_id: str,
    include_transcript: bool = Query(False),
    user_id: str = Depends(get_current_user)
):
    """
    Get specific video
    
    - **video_id**: YouTube video ID
    - **include_transcript**: Include full transcript in response
    """
    try:
        video = await get_video_by_id(user_id, video_id)
        
        if not video:
            return not_found_response("Video", video_id)
        
        # Remove transcript if not requested
        if not include_transcript and 'transcript' in video:
            video['transcriptLength'] = len(video.get('transcript', ''))
            del video['transcript']
        
        # Add to history
        await add_history_entry(
            user_id=user_id,
            action="view",
            resource_type="video",
            resource_id=video_id
        )
        
        return success_response(
            data=video,
            message="Video retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get video: {e}")
        return error_response(str(e), 500)


@router.delete("/{video_id}", status_code=204)
async def remove_video(
    video_id: str,
    delete_audio: bool = Query(True, description="Also delete audio file"),
    user_id: str = Depends(get_current_user)
):
    """
    Delete a video
    
    - **video_id**: YouTube video ID
    - **delete_audio**: Also delete downloaded audio file
    """
    try:
        # Delete from database
        deleted = await delete_video(user_id, video_id)
        
        if not deleted:
            return not_found_response("Video", video_id)
        
        # Delete chunks
        await delete_chunks_by_video(video_id, user_id)
        
        # Delete from vector store
        vector_store.delete_index(video_id)
        
        # Delete audio file if requested
        if delete_audio:
            await delete_youtube_audio_async(video_id)
        
        logger.info(f"🗑️  Deleted video: {video_id}")
        
        return no_content_response()
        
    except Exception as e:
        logger.error(f"❌ Failed to delete video: {e}")
        return error_response(str(e), 500)


# ============================================================================
# VIDEO CHUNKS
# ============================================================================

@router.get("/{video_id}/chunks")
async def get_video_chunks(
    video_id: str,
    limit: int = Query(100, ge=1, le=500),
    include_embeddings: bool = Query(False),
    user_id: str = Depends(get_current_user)
):
    """
    Get chunks for a video
    
    - **video_id**: YouTube video ID
    - **limit**: Maximum chunks to return
    - **include_embeddings**: Include embedding vectors
    """
    try:
        # Verify video exists
        video = await get_video_by_id(user_id, video_id)
        
        if not video:
            return not_found_response("Video", video_id)
        
        chunks = await get_chunks_by_video(
            video_id,
            limit=limit,
            include_embeddings=include_embeddings
        )
        
        return success_response(
            data={"chunks": chunks, "count": len(chunks)},
            message=f"Retrieved {len(chunks)} chunks"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get chunks: {e}")
        return error_response(str(e), 500)


# ============================================================================
# VIDEO Q&A
# ============================================================================

@router.post("/{video_id}/ask")
async def ask_video_question(
    video_id: str,
    question: str = Query(..., min_length=1, max_length=500),
    top_k: int = Query(5, ge=1, le=20, description="Number of chunks to retrieve"),
    user_id: str = Depends(get_current_user)
):
    """
    Ask a question about a video
    
    - **video_id**: YouTube video ID
    - **question**: Question to ask
    - **top_k**: Number of relevant chunks to use
    """
    try:
        # Verify video exists
        video = await get_video_by_id(user_id, video_id)
        
        if not video:
            return not_found_response("Video", video_id)
        
        # Check if embeddings are ready
        if video.get('embeddingStatus') != 'completed':
            return error_response("Video embeddings not ready", 400)
        
        # Answer question
        result = await answer_question_async(video_id, question, top_k)
        
        # Add to history
        await add_history_entry(
            user_id=user_id,
            action="ask",
            resource_type="video",
            resource_id=video_id,
            metadata={"question": question}
        )
        
        return success_response(
            data=result,
            message="Question answered successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to answer question: {e}")
        return error_response(str(e), 500)


@router.post("/{video_id}/summarize")
async def summarize_video(
    video_id: str,
    max_chunks: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user)
):
    """
    Generate video summary
    
    - **video_id**: YouTube video ID
    - **max_chunks**: Maximum chunks to use for summary
    """
    try:
        # Verify video exists
        video = await get_video_by_id(user_id, video_id)
        
        if not video:
            return not_found_response("Video", video_id)
        
        # Generate summary
        summary = await summarize_video_async(video_id, max_chunks)
        
        return success_response(
            data={
                "videoId": video_id,
                "summary": summary,
                "chunksUsed": max_chunks
            },
            message="Summary generated successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to generate summary: {e}")
        return error_response(str(e), 500)


# ============================================================================
# VIDEO INFO
# ============================================================================

@router.get("/{video_id}/info")
async def get_video_info(
    video_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Get video information from YouTube
    
    - **video_id**: YouTube video ID
    """
    try:
        info = await get_youtube_video_info_async(video_id)
        
        return success_response(
            data=info,
            message="Video info retrieved"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get video info: {e}")
        return error_response(str(e), 500)


@router.get("/{video_id}/transcript")
async def get_video_transcript(
    video_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Get video transcript
    
    - **video_id**: YouTube video ID
    """
    try:
        video = await get_video_by_id(user_id, video_id)
        
        if not video:
            return not_found_response("Video", video_id)
        
        transcript = video.get('transcript', '')
        
        return success_response(
            data={
                "videoId": video_id,
                "transcript": transcript,
                "length": len(transcript),
                "source": video.get('source')
            },
            message="Transcript retrieved"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get transcript: {e}")
        return error_response(str(e), 500)


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

@router.post("/batch/process")
async def batch_process_videos(
    urls: List[str],
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Process multiple videos
    
    - **urls**: List of YouTube video URLs
    """
    try:
        if len(urls) > 10:
            return error_response("Maximum 10 videos per batch", 400)
        
        results = []
        
        for url in urls:
            try:
                video_id = validate_youtube_url(url)
                
                # Check if already exists
                exists = await check_video_exists(user_id, video_id)
                
                if exists:
                    results.append({
                        "url": url,
                        "videoId": video_id,
                        "status": "skipped",
                        "message": "Already processed"
                    })
                else:
                    # Add to background tasks
                    video_info = await get_youtube_video_info_async(video_id)
                    
                    background_tasks.add_task(
                        process_video_background,
                        video_id=video_id,
                        url=url,
                        user_id=user_id,
                        video_info=video_info,
                        use_captions=True
                    )
                    
                    results.append({
                        "url": url,
                        "videoId": video_id,
                        "status": "processing",
                        "message": "Processing started"
                    })
                    
            except Exception as e:
                results.append({
                    "url": url,
                    "status": "failed",
                    "error": str(e)
                })
        
        return accepted_response(
            message=f"Batch processing started for {len(urls)} videos",
            data={"results": results}
        )
        
    except Exception as e:
        logger.error(f"❌ Batch processing failed: {e}")
        return error_response(str(e), 500)
