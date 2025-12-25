# main.py - FastAPI version of your Flask app

import os
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, APIRouter, Depends, Request, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from config.logging_config import logger
from database.connection import db_connection

# Clerk auth (reused)
from middleware.auth import initialize_clerk, get_token_from_request
from clerk_backend_api.security import authenticate_request
from clerk_backend_api.security.types import AuthenticateRequestOptions

# Vector store and services
from services.vector_store import VectorStore
from services.youtube_captions import get_youtube_captions
from services.audio_extractor import extract_youtube_audio
from services.transcription_service import transcribe_audio
from services.embedding_service import generate_embeddings, chunk_text
from services.rag_service import answer_question_from_video

# Core helpers / models / utils
from core.responses import success_response, error_response
from core.exceptions import ValidationError, ResourceNotFoundError
from utils.validators import validate_youtube_url, validate_file_upload
from utils.decorators import rate_limit  # will adapt to FastAPI style below

from models.chat import create_chat, get_chat, add_to_chat, delete_chat
from models.user_chats import add_user_chat, get_user_chats, remove_user_chat, delete_all_user_chats
from models.history import save_history, get_all_history, get_history_by_video
from models.video import save_video, get_video_by_id, get_user_videos
from models.chunk import save_chunks, get_chunks_by_video

# Document processing
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    logger.warning("⚠️ PyPDF2 not installed")

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None
    logger.warning("⚠️ python-docx not installed")

# Gemini AI setup
try:
    import google.generativeai as genai
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        logger.info("✅ Gemini AI configured")
    else:
        genai = None
        logger.warning("⚠️ Gemini API key not found")
except ImportError:
    genai = None
    logger.warning("⚠️ google-generativeai library not installed")


def get_gemini_model():
    """Get configured Gemini model with working model name."""
    if not genai or not settings.GEMINI_API_KEY:
        raise ValidationError("AI service not available")
    return genai.GenerativeModel(
        model_name="gemini-flash-latest",
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 1024,
        },
    )


# ---------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)
logger.info("✅ CORS configured")

# Initialize Clerk client and vector store at startup
clerk_client = initialize_clerk()
if clerk_client:
    logger.info("✅ Clerk authentication initialized")
else:
    logger.warning("⚠️ Clerk not initialized")

app.state.vector_store = VectorStore()
logger.info("✅ Vector Store initialized")


# ---------------------------------------------------------------------
# Auth dependency (FastAPI-style replacement for require_auth + g)
# ---------------------------------------------------------------------

class AuthUser:
    def __init__(self, user_id: str, email: Optional[str], name: Optional[str]):
        self.user_id = user_id
        self.email = email
        self.name = name


async def get_current_user(request: Request) -> AuthUser:
    """FastAPI dependency to authenticate request and inject user."""
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided",
        )

    client = clerk_client
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    try:
        import httpx

        req = httpx.Request(
            "GET",
            "http://localhost",
            headers={"Authorization": f"Bearer {token}"},
        )

        options = AuthenticateRequestOptions(
            secret_key=settings.CLERK_SECRET_KEY,
        )
        request_state = authenticate_request(req, options)

        if not request_state.is_signed_in:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=request_state.error_reason or "Not signed in",
            )

        claims = getattr(request_state, "claims", None) or {}
        user_id = claims.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject (sub)",
            )

        user = client.users.get(user_id)
        email = (
            user.email_addresses[0].email_address
            if getattr(user, "email_addresses", [])
            else None
        )
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()

        return AuthUser(user_id=user.id, email=email, name=name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        )


# ---------------------------------------------------------------------
# Routers (replacement for Flask blueprints)
# ---------------------------------------------------------------------

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
chat_router = APIRouter(prefix="/api", tags=["chat"])
video_router = APIRouter(prefix="/api", tags=["video"])
document_router = APIRouter(prefix="/api", tags=["document"])
history_router = APIRouter(prefix="/api", tags=["history"])


# ---------------------------------------------------------------------
# AUTH ROUTES
# ---------------------------------------------------------------------

@auth_router.get("/me")
async def get_user_info(current_user: AuthUser = Depends(get_current_user)):
    user_data = {
        "userId": current_user.user_id,
        "email": current_user.email,
        "name": current_user.name,
    }
    return success_response(data=user_data, message="User info retrieved successfully")


@auth_router.get("/session/verify")
async def verify_session(current_user: AuthUser = Depends(get_current_user)):
    return success_response(
        data={
            "valid": True,
            "userId": current_user.user_id,
            "email": current_user.email,
        },
        message="Session is valid",
    )


# ---------------------------------------------------------------------
# CHAT ROUTES
# ---------------------------------------------------------------------

@chat_router.get("/chats")
async def get_chats(current_user: AuthUser = Depends(get_current_user)):
    try:
        chats = get_user_chats(current_user.user_id)
        return success_response(data={"chats": chats}, message="Chats retrieved successfully")
    except Exception as e:
        logger.error(f"Error fetching chats: {e}", exc_info=True)
        return error_response("Failed to fetch chats", 500)


@chat_router.delete("/chats")
async def delete_all_chats_route(current_user: AuthUser = Depends(get_current_user)):
    try:
        delete_all_user_chats(current_user.user_id)
        return success_response(message="All chats deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting chats: {e}", exc_info=True)
        return error_response("Failed to delete chats", 500)


@chat_router.get("/chat/{chat_id}")
async def get_single_chat_route(chat_id: str, current_user: AuthUser = Depends(get_current_user)):
    try:
        chat = get_chat(chat_id, current_user.user_id)
        if not chat:
            raise ResourceNotFoundError("Chat not found")
        return success_response(data=chat, message="Chat retrieved successfully")
    except ResourceNotFoundError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"Error fetching chat: {e}", exc_info=True)
        return error_response("Failed to fetch chat", 500)


@chat_router.delete("/chat/{chat_id}")
async def delete_single_chat_route(chat_id: str, current_user: AuthUser = Depends(get_current_user)):
    try:
        success = delete_chat(chat_id, current_user.user_id)
        if not success:
            raise ResourceNotFoundError("Chat not found")
        remove_user_chat(current_user.user_id, chat_id)
        return success_response(message="Chat deleted successfully")
    except ResourceNotFoundError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"Error deleting chat: {e}", exc_info=True)
        return error_response("Failed to delete chat", 500)


@chat_router.post("/create-chat")
async def create_new_chat_route(
    data: Dict[str, Any],
    current_user: AuthUser = Depends(get_current_user),
):
    try:
        title = data.get("title", "New Chat")
        initial_text = data.get("text")
        chat_id = create_chat(current_user.user_id, text=initial_text, title=title)
        add_user_chat(current_user.user_id, chat_id, title)
        return success_response(
            data={"chatId": chat_id, "title": title},
            message="Chat created successfully",
            status_code=201,
        )
    except Exception as e:
        logger.error(f"Error creating chat: {e}", exc_info=True)
        return error_response("Failed to create chat", 500)


@chat_router.post("/send-message")
async def send_message_route(
    data: Dict[str, Any],
    current_user: AuthUser = Depends(get_current_user),
):
    try:
        chat_id = data.get("chatId")
        text = data.get("text")

        chat = get_chat(chat_id, current_user.user_id)
        if not chat:
            raise ResourceNotFoundError("Chat not found")

        ai_response = "Sorry, I couldn't generate a response."

        if genai and settings.GEMINI_API_KEY:
            try:
                model = get_gemini_model()
                resp = model.generate_content(text)
                if hasattr(resp, "text") and resp.text:
                    ai_response = resp.text.strip()[: settings.MAX_AI_CHARS]
            except Exception as e:
                logger.error(f"AI generation error: {e}", exc_info=True)
                ai_response = f"AI Error: {str(e)}"

        add_to_chat(chat_id, current_user.user_id, question=text, answer=ai_response)

        return success_response(
            data={"user": text, "ai": ai_response},
            message="Message sent successfully",
        )
    except ResourceNotFoundError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        return error_response("Failed to send message", 500)


# ---------------------------------------------------------------------
# VIDEO ROUTES (RAG)
# ---------------------------------------------------------------------

@video_router.get("/videos")
async def get_videos_route(current_user: AuthUser = Depends(get_current_user)):
    try:
        videos = get_user_videos(current_user.user_id)
        videos_list = []
        for video in videos:
            video_dict = dict(video)
            if "_id" in video_dict:
                video_dict["_id"] = str(video_dict["_id"])
            if "createdAt" in video_dict:
                video_dict["createdAt"] = video_dict["createdAt"].isoformat()
            if "processedAt" in video_dict:
                video_dict["processedAt"] = video_dict["processedAt"].isoformat()
            videos_list.append(video_dict)
        return success_response(data={"videos": videos_list}, message="Videos retrieved successfully")
    except Exception as e:
        logger.error(f"Error fetching videos: {e}", exc_info=True)
        return error_response("Failed to fetch videos", 500)


@video_router.post("/youtube/process")
async def process_youtube_route(
    data: Dict[str, Any],
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
):
    try:
        url = data.get("url")
        video_id = validate_youtube_url(url)

        logger.info(f"🎬 Processing video: {video_id} for user: {current_user.user_id}")

        existing = get_video_by_id(current_user.user_id, video_id)
        if existing:
            return success_response(
                data={
                    "videoId": video_id,
                    "status": "already_processed",
                    "source": existing.get("source", "N/A"),
                    "chunkCount": len(get_chunks_by_video(video_id)),
                },
                message="Video already in knowledge base",
            )

        transcript = get_youtube_captions(video_id)
        audio_path = None
        source = "youtube_captions"

        if not transcript:
            logger.info(f"📥 Step 1/5: Extracting audio for {video_id}")
            audio_path = extract_youtube_audio(video_id)

            logger.info("🎤 Step 2/5: Transcribing audio")
            transcript = transcribe_audio(audio_path)
            source = "whisper_transcription"

        if not transcript:
            raise ValidationError("Failed to extract transcript from video")

        logger.info(f"✂️ Step 3/5: Chunking transcript ({len(transcript)} chars)")
        chunks = chunk_text(transcript)

        logger.info(f"🧠 Step 4/5: Generating embeddings for {len(chunks)} chunks")
        chunk_data = generate_embeddings(chunks, video_id)

        logger.info("💾 Step 5/5: Storing in vector database")
        request.app.state.vector_store.add_vectors(chunk_data)

        video_doc_id = save_video(
            user_id=current_user.user_id,
            video_id=video_id,
            url=url,
            transcript=transcript,
            audio_path=audio_path,
            source=source,
        )

        save_chunks(video_id, chunk_data)

        logger.info(
            f"✅ Video processed successfully: {video_id} | {len(chunks)} chunks | Source: {source}"
        )

        return success_response(
            data={
                "videoId": video_id,
                "status": "success",
                "chunkCount": len(chunks),
                "source": source,
                "transcriptPreview": transcript[:500] + "..."
                if len(transcript) > 500
                else transcript,
            },
            message=f"Video processed using {source.replace('_', ' ')}",
            status_code=201,
        )
    except ValidationError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"❌ Video processing error: {e}", exc_info=True)
        return error_response(f"Failed to process video: {str(e)}", 500)


@video_router.post("/youtube/{video_id}/ask")
async def ask_video_route(
    video_id: str,
    data: Dict[str, Any],
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
):
    try:
        question = data.get("question")

        video = get_video_by_id(current_user.user_id, video_id)
        if not video:
            raise ResourceNotFoundError("Video not found. Please process it first.")

        logger.info(f"❓ Question for {video_id}: {question}")

        model = get_gemini_model()

        answer, context_chunks = answer_question_from_video(
            video_id=video_id,
            question=question,
            vector_store=request.app.state.vector_store,
            model=model,
        )

        logger.info(f"✅ Answer generated using {len(context_chunks)} chunks")

        return success_response(
            data={
                "question": question,
                "answer": answer,
                "sourcesUsed": len(context_chunks),
                "contextPreview": [
                    c["text"][:200] + "..." for c in context_chunks[:2]
                ],
            },
            message="Answer generated successfully",
        )
    except (ValidationError, ResourceNotFoundError) as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"❌ RAG error: {e}", exc_info=True)
        return error_response(f"Failed to answer question: {str(e)}", 500)


@video_router.post("/youtube/{video_id}/summary")
async def generate_summary_route(
    video_id: str,
    data: Optional[Dict[str, Any]] = None,
    current_user: AuthUser = Depends(get_current_user),
):
    try:
        data = data or {}
        summary_type = data.get("type", "brief")

        video = get_video_by_id(current_user.user_id, video_id)
        if not video:
            raise ResourceNotFoundError("Video not found")

        transcript = video.get("transcript", "")
        if not transcript:
            raise ValidationError("Video transcript not available")

        model = get_gemini_model()

        prompts = {
            "brief": "Provide a concise 3-sentence summary:",
            "detailed": "Provide a comprehensive summary with main points:",
            "bullets": "Summarize as 5-7 bullet points:",
            "technical": "Provide a technical summary:",
        }

        prompt = f"{prompts.get(summary_type, prompts['brief'])}\n\n{transcript[:20000]}"

        logger.info(f"🤖 Generating {summary_type} summary for {video_id}")
        resp = model.generate_content(prompt)

        summary = resp.text.strip() if hasattr(resp, "text") else "Unable to generate summary"

        if not summary or summary == "Unable to generate summary":
            raise ValidationError("Failed to generate summary")

        save_history(
            user_id=current_user.user_id,
            video_id=video_id,
            title=f"{summary_type.title()} Summary - {video_id}",
            summary=summary,
            mode=f"Video Summary ({summary_type})",
        )

        logger.info(f"✅ {summary_type} summary generated")

        return success_response(
            data={"videoId": video_id, "summaryType": summary_type, "summary": summary},
            message="Summary generated successfully",
        )
    except (ValidationError, ResourceNotFoundError) as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"❌ Summary error: {e}", exc_info=True)
        return error_response(f"Failed to generate summary: {str(e)}", 500)


# ---------------------------------------------------------------------
# DOCUMENT ROUTES
# ---------------------------------------------------------------------

@document_router.post("/document")
async def process_document_route(
    request: Request,
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),
):
    try:
        validate_file_upload(file)
        filename = file.filename
        ext = filename.lower().split(".")[-1] if "." in filename else ""

        logger.info(f"📄 Processing document: {filename} ({ext})")

        text = ""
        page_count = 0

        if ext == "pdf":
            if not PyPDF2:
                raise ValidationError("PDF support not available")

            reader = PyPDF2.PdfReader(file.file)
            page_count = len(reader.pages)

            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text += f"\n--- Page {i+1} ---\n{page_text}"
                except Exception as e:
                    logger.warning(f"Error extracting page {i+1}: {e}")
                    continue

        elif ext == "docx":
            if not DocxDocument:
                raise ValidationError("DOCX support not available")

            doc = DocxDocument(file.file)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            text = "\n\n".join(paragraphs)

        elif ext == "txt":
            content = await file.read()
            text = content.decode("utf-8", errors="ignore")

        else:
            raise ValidationError(f"Unsupported file format: {ext}")

        text = text.strip()

        if not text:
            raise ValidationError("No text content found in document")

        logger.info(f"📝 Extracted {len(text)} characters from {filename}")

        model = get_gemini_model()

        truncated_text = text[:30000]

        prompt = f"""Analyze and summarize this document comprehensively.

**Document:** {filename}
**Type:** {ext.upper()}

Provide:
1. Main topic/purpose (2-3 sentences)
2. Key points (3-5 bullet points)
3. Important details or findings
4. Conclusion/takeaways

**Content:**
{truncated_text}
"""

        resp = model.generate_content(prompt)
        summary = resp.text.strip() if hasattr(resp, "text") else "Unable to generate summary"

        save_history(
            user_id=current_user.user_id,
            video_id=filename,
            title=f"Document: {filename}",
            summary=summary,
            mode="Document Summary",
        )

        logger.info(f"✅ Document summary generated for {filename}")

        return success_response(
            data={
                "filename": filename,
                "summary": summary,
                "metadata": {
                    "fileType": ext.upper(),
                    "textLength": len(text),
                    "pageCount": page_count if page_count > 0 else None,
                    "wasTruncated": len(text) > 30000,
                },
            },
            message="Document processed successfully",
        )
    except ValidationError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"❌ Document processing error: {e}", exc_info=True)
        return error_response(f"Failed to process document: {str(e)}", 500)


# ---------------------------------------------------------------------
# HISTORY ROUTES
# ---------------------------------------------------------------------

@history_router.get("/history")
async def get_history_route(current_user: AuthUser = Depends(get_current_user)):
    try:
        history = get_all_history(current_user.user_id)
        return success_response(data={"history": history}, message="History retrieved successfully")
    except Exception as e:
        logger.error(f"Error fetching history: {e}", exc_info=True)
        return error_response("Failed to fetch history", 500)


@history_router.get("/history/{video_id}")
async def get_video_history_route(
    video_id: str, current_user: AuthUser = Depends(get_current_user)
):
    try:
        history = get_history_by_video(current_user.user_id, video_id)
        if not history:
            raise ResourceNotFoundError("History not found")
        return success_response(data=history, message="History retrieved successfully")
    except ResourceNotFoundError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"Error fetching video history: {e}", exc_info=True)
        return error_response("Failed to fetch history", 500)


# ---------------------------------------------------------------------
# Health and root endpoints
# ---------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    db_healthy = db_connection.health_check()
    return JSONResponse(
        {
            "status": "healthy" if db_healthy else "degraded",
            "version": settings.APP_VERSION,
            "authentication": "clerk",
            "services": {
                "database": "connected" if db_healthy else "disconnected",
                "vectorStore": app.state.vector_store is not None,
                "ai": settings.GEMINI_API_KEY is not None,
                "whisper": True,
                "embeddings": True,
                "clerk": settings.CLERK_SECRET_KEY is not None,
            },
        },
        status_code=200 if db_healthy else 503,
    )


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "authentication": "clerk",
        "model": "gemini-flash-latest",
        "endpoints": {
            "health": "/api/health",
            "auth": "/api/auth/me",
            "docs": "https://github.com/your-repo",
        },
    }


# ---------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(video_router)
app.include_router(document_router)
app.include_router(history_router)
