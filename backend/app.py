# app.py - UPDATED WITH CORRECT GEMINI MODEL
import os
from flask import Flask, jsonify, current_app
from flask_cors import CORS


# Configuration and Setup
from config.settings import settings
from config.logging_config import logger
from database.connection import db_connection


# Middleware
from middleware.error_handler import register_error_handlers
from middleware.request_logger import register_request_logger
from middleware.auth import initialize_clerk 


# Initialize AI Services
from services.vector_store import VectorStore

from services.youtube_captions import get_youtube_captions
from services.audio_extractor import extract_youtube_audio
from services.transcription_service import transcribe_audio
from services.embedding_service import generate_embeddings, chunk_text
from services.rag_service import answer_question_from_video

# AI Model Setup
try:
    import google.generativeai as genai
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        logger.info("✅ Gemini AI configured")
    else:
        genai = None
        logger.warning("⚠️  Gemini API key not found")
except ImportError:
    genai = None
    logger.warning("⚠️  google-generativeai library not installed")


# ---------------------------------------------------------------------
# Create Blueprints (Route Modules)
# ---------------------------------------------------------------------
from flask import Blueprint, request, g
from werkzeug.utils import secure_filename


from middleware.auth import require_auth
from core.responses import success_response, error_response
from core.exceptions import ValidationError, ResourceNotFoundError
from utils.validators import validate_youtube_url, validate_file_upload
from utils.decorators import rate_limit, validate_json


# Import model functions
from models.chat import create_chat, get_chat, add_to_chat, delete_chat
from models.user_chats import add_user_chat, get_user_chats, remove_user_chat, delete_all_user_chats
from models.history import save_history, get_all_history, get_history_by_video
from models.video import save_video, get_video_by_id, get_user_videos
from models.chunk import save_chunks, get_chunks_by_video


# Import service functions
from services.audio_extractor import extract_youtube_audio
from services.transcription_service import transcribe_audio
from services.embedding_service import generate_embeddings, chunk_text
from services.rag_service import answer_question_from_video


# Document processing
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    logger.warning("⚠️  PyPDF2 not installed")


try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None
    logger.warning("⚠️  python-docx not installed")


# ✅ ADDED: Helper function to get Gemini model
def get_gemini_model():
    """Get configured Gemini model with working model name"""
    return genai.GenerativeModel(
        model_name="gemini-flash-latest",  # ✅ Works with your API key
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 1024,
        }
    )


# ---------------------------------------------------------------------
# AUTH ROUTES BLUEPRINT (NEW - CLERK SPECIFIC)
# ---------------------------------------------------------------------
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_user_info():
    """Get current user information"""
    user_data = {
        'userId': g.user_id,
        'email': g.user_email,
        'name': g.user_name,
        'username': getattr(g, 'username', None),
        'imageUrl': getattr(g, 'user_image', None)
    }
    
    return success_response(
        data=user_data,
        message="User info retrieved successfully"
    )


@auth_bp.route('/session/verify', methods=['GET'])
@require_auth
def verify_session():
    """Verify if session is valid"""
    return success_response(
        data={
            "valid": True,
            "userId": g.user_id,
            "email": g.user_email
        },
        message="Session is valid"
    )


# ---------------------------------------------------------------------
# CHAT ROUTES BLUEPRINT
# ---------------------------------------------------------------------
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chats', methods=['GET'])
@require_auth
@rate_limit(max_requests=100)
def get_chats():
    """Get all chats for user"""
    try:
        user_id = g.user_id
        chats = get_user_chats(user_id)
        
        return success_response(
            data={"chats": chats},
            message="Chats retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error fetching chats: {e}")
        return error_response("Failed to fetch chats", 500)


@chat_bp.route('/chats', methods=['DELETE'])
@require_auth
@rate_limit(max_requests=10)
def delete_all_chats():
    """Delete all chats for user"""
    try:
        user_id = g.user_id
        delete_all_user_chats(user_id)
        
        return success_response(
            message="All chats deleted successfully"
        )
    except Exception as e:
        logger.error(f"Error deleting chats: {e}")
        return error_response("Failed to delete chats", 500)


@chat_bp.route('/chat/<chat_id>', methods=['GET'])
@require_auth
@rate_limit(max_requests=100)
def get_single_chat(chat_id):
    """Get specific chat by ID"""
    try:
        user_id = g.user_id
        chat = get_chat(chat_id, user_id)
        
        if not chat:
            raise ResourceNotFoundError("Chat not found")
        
        return success_response(
            data=chat,
            message="Chat retrieved successfully"
        )
    except ResourceNotFoundError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"Error fetching chat: {e}")
        return error_response("Failed to fetch chat", 500)


@chat_bp.route('/chat/<chat_id>', methods=['DELETE'])
@require_auth
@rate_limit(max_requests=20)
def delete_single_chat(chat_id):
    """Delete specific chat"""
    try:
        user_id = g.user_id
        success = delete_chat(chat_id, user_id)
        
        if not success:
            raise ResourceNotFoundError("Chat not found")
        
        remove_user_chat(user_id, chat_id)
        
        return success_response(
            message="Chat deleted successfully"
        )
    except ResourceNotFoundError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"Error deleting chat: {e}")
        return error_response("Failed to delete chat", 500)


@chat_bp.route('/create-chat', methods=['POST'])
@require_auth
@rate_limit(max_requests=50)
@validate_json('title')
def create_new_chat():
    """Create a new chat"""
    try:
        user_id = g.user_id
        data = request.get_json()
        
        title = data.get('title', 'New Chat')
        initial_text = data.get('text')
        
        chat_id = create_chat(user_id, text=initial_text, title=title)
        add_user_chat(user_id, chat_id, title)
        
        return success_response(
            data={"chatId": chat_id, "title": title},
            message="Chat created successfully",
            status_code=201
        )
    except Exception as e:
        logger.error(f"Error creating chat: {e}")
        return error_response("Failed to create chat", 500)


@chat_bp.route('/send-message', methods=['POST'])
@require_auth
@rate_limit(max_requests=60)
@validate_json('chatId', 'text')
def send_message():
    """Send message in chat and get AI response"""
    try:
        user_id = g.user_id
        data = request.get_json()
        
        chat_id = data.get('chatId')
        text = data.get('text')
        
        # Check chat exists
        chat = get_chat(chat_id, user_id)
        if not chat:
            raise ResourceNotFoundError("Chat not found")
        
        # Generate AI response
        ai_response = "Sorry, I couldn't generate a response."
        
        if genai and settings.GEMINI_API_KEY:
            try:
                model = get_gemini_model()  # ✅ FIXED: Use helper function
                resp = model.generate_content(text)
                
                if hasattr(resp, 'text') and resp.text:
                    ai_response = resp.text.strip()[:settings.MAX_AI_CHARS]
            except Exception as e:
                logger.error(f"AI generation error: {e}")
                ai_response = f"AI Error: {str(e)}"
        
        # Save to chat
        add_to_chat(chat_id, user_id, question=text, answer=ai_response)
        
        return success_response(
            data={"user": text, "ai": ai_response},
            message="Message sent successfully"
        )
        
    except ResourceNotFoundError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return error_response("Failed to send message", 500)


# ---------------------------------------------------------------------
# VIDEO ROUTES BLUEPRINT (RAG-BASED)
# ---------------------------------------------------------------------
video_bp = Blueprint('video', __name__)


@video_bp.route('/videos', methods=['GET'])
@require_auth
@rate_limit(max_requests=100)
def get_videos():
    """Get all processed videos for user"""
    try:
        user_id = g.user_id
        videos = get_user_videos(user_id)
        
        # Serialize videos
        videos_list = []
        for video in videos:
            video_dict = dict(video)
            if '_id' in video_dict:
                video_dict['_id'] = str(video_dict['_id'])
            if 'createdAt' in video_dict:
                video_dict['createdAt'] = video_dict['createdAt'].isoformat()
            if 'processedAt' in video_dict:
                video_dict['processedAt'] = video_dict['processedAt'].isoformat()
            videos_list.append(video_dict)
        
        return success_response(
            data={"videos": videos_list},
            message="Videos retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error fetching videos: {e}")
        return error_response("Failed to fetch videos", 500)



# app.py - process_youtube function (complete fixed version)

@video_bp.route('/youtube/process', methods=['POST'])
@require_auth
@rate_limit(max_requests=10)
@validate_json('url')
def process_youtube():
    """Process YouTube video: captions → transcription → embedding → store"""
    try:
        user_id = g.user_id
        data = request.get_json()
        
        url = data.get('url')
        video_id = validate_youtube_url(url)
        
        logger.info(f"🎬 Processing video: {video_id} for user: {user_id}")
        
        # Check if already processed
        existing = get_video_by_id(user_id, video_id)
        if existing:
            return success_response(
                data={
                    "videoId": video_id,
                    "status": "already_processed",
                    "source": existing.get('source', 'N/A'),
                    "chunkCount": len(get_chunks_by_video(video_id))
                },
                message="Video already in knowledge base"
            )
        
        # Phase 1: Try YouTube Captions First (INSTANT!)
        transcript = get_youtube_captions(video_id)
        audio_path = None
        source = "youtube_captions"
        
        if not transcript:
            # Phase 2: No captions - Fall back to audio transcription
            logger.info(f"📥 Step 1/5: Extracting audio for {video_id}")
            audio_path = extract_youtube_audio(video_id)
            
            logger.info(f"🎤 Step 2/5: Transcribing audio")
            transcript = transcribe_audio(audio_path)
            source = "whisper_transcription"
        
        if not transcript:
            raise ValidationError("Failed to extract transcript from video")
        
        # Phase 3: Chunk & Embed
        logger.info(f"✂️  Step 3/5: Chunking transcript ({len(transcript)} chars)")
        chunks = chunk_text(transcript)
        
        logger.info(f"🧠 Step 4/5: Generating embeddings for {len(chunks)} chunks")
        chunk_data = generate_embeddings(chunks, video_id)
        
        logger.info(f"💾 Step 5/5: Storing in vector database")
        current_app.vector_store.add_vectors(chunk_data)
        
        # Save to MongoDB - ✅ FIXED
        video_doc_id = save_video(
            user_id=user_id,
            video_id=video_id,
            url=url,
            transcript=transcript,
            audio_path=audio_path,
            source=source  # ✅ Pass source directly
        )
        
        save_chunks(video_id, chunk_data)
        
        logger.info(f"✅ Video processed successfully: {video_id} | {len(chunks)} chunks | Source: {source}")
        
        return success_response(
            data={
                "videoId": video_id,
                "status": "success",
                "chunkCount": len(chunks),
                "source": source,
                "transcriptPreview": transcript[:500] + "..." if len(transcript) > 500 else transcript
            },
            message=f"Video processed using {source.replace('_', ' ')}",
            status_code=201
        )
        
    except ValidationError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"❌ Video processing error: {e}", exc_info=True)
        return error_response(f"Failed to process video: {str(e)}", 500)

    
@video_bp.route('/youtube/<video_id>/ask', methods=['POST'])
@require_auth
@rate_limit(max_requests=30)
@validate_json('question')
def ask_video(video_id):
    """Ask question about video using RAG"""
    try:
        user_id = g.user_id
        data = request.get_json()
        question = data.get('question')
        
        # Verify video exists
        video = get_video_by_id(user_id, video_id)
        if not video:
            raise ResourceNotFoundError("Video not found. Please process it first.")
        
        logger.info(f"❓ Question for {video_id}: {question}")
        
        # Get AI model
        if not genai or not settings.GEMINI_API_KEY:
            raise ValidationError("AI service not available")
        
        model = get_gemini_model()  # ✅ FIXED: Use helper function
        
        # Use RAG to answer
        answer, context_chunks = answer_question_from_video(
            video_id=video_id,
            question=question,
            vector_store=current_app.vector_store,
            model=model
        )
        
        logger.info(f"✅ Answer generated using {len(context_chunks)} chunks")
        
        return success_response(
            data={
                "question": question,
                "answer": answer,
                "sourcesUsed": len(context_chunks),
                "contextPreview": [c['text'][:200] + "..." for c in context_chunks[:2]]
            },
            message="Answer generated successfully"
        )
        
    except (ValidationError, ResourceNotFoundError) as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"❌ RAG error: {e}", exc_info=True)
        return error_response(f"Failed to answer question: {str(e)}", 500)


@video_bp.route('/youtube/<video_id>/summary', methods=['POST'])
@require_auth
@rate_limit(max_requests=20)
def generate_summary(video_id):
    """Generate custom summary - FIXED"""
    try:
        user_id = g.user_id
        data = request.get_json() or {}
        summary_type = data.get('type', 'brief')
        
        # Get video
        video = get_video_by_id(user_id, video_id)
        if not video:
            raise ResourceNotFoundError("Video not found")
        
        transcript = video.get('transcript', '')
        if not transcript:
            raise ValidationError("Video transcript not available")
        
        if not genai or not settings.GEMINI_API_KEY:
            raise ValidationError("AI service not available")
        
        # Optimized prompts
        prompts = {
            "brief": "Provide a concise 3-sentence summary:",
            "detailed": "Provide a comprehensive summary with main points:",
            "bullets": "Summarize as 5-7 bullet points:",
            "technical": "Provide a technical summary:"
        }
        
        prompt = f"{prompts.get(summary_type, prompts['brief'])}\n\n{transcript[:20000]}"
        
        # ✅ FIXED: Use helper function with working model
        model = get_gemini_model()
        
        logger.info(f"🤖 Generating {summary_type} summary for {video_id}")
        resp = model.generate_content(prompt)
        
        summary = resp.text.strip() if hasattr(resp, 'text') else "Unable to generate summary"
        
        if not summary or summary == "Unable to generate summary":
            raise ValidationError("Failed to generate summary")
        
        # Save to history
        save_history(
            user_id=user_id,
            video_id=video_id,
            title=f"{summary_type.title()} Summary - {video_id}",
            summary=summary,
            mode=f"Video Summary ({summary_type})"
        )
        
        logger.info(f"✅ {summary_type} summary generated")
        
        return success_response(
            data={"videoId": video_id, "summaryType": summary_type, "summary": summary},
            message="Summary generated successfully"
        )
        
    except (ValidationError, ResourceNotFoundError) as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"❌ Summary error: {e}", exc_info=True)
        return error_response(f"Failed to generate summary: {str(e)}", 500)



# ---------------------------------------------------------------------
# DOCUMENT ROUTES BLUEPRINT
# ---------------------------------------------------------------------
document_bp = Blueprint('document', __name__)


@document_bp.route('/document', methods=['POST'])
@require_auth
@rate_limit(max_requests=20)
def process_document():
    """Process document upload and generate summary"""
    try:
        user_id = g.user_id
        
        if 'file' not in request.files:
            raise ValidationError("No file provided")
        
        file = request.files['file']
        validate_file_upload(file)
        
        filename = secure_filename(file.filename)
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        logger.info(f"📄 Processing document: {filename} ({ext})")
        
        text = ""
        page_count = 0
        
        # Extract text based on file type
        if ext == 'pdf':
            if not PyPDF2:
                raise ValidationError("PDF support not available")
            
            reader = PyPDF2.PdfReader(file.stream)
            page_count = len(reader.pages)
            
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text += f"\n--- Page {i+1} ---\n{page_text}"
                except Exception as e:
                    logger.warning(f"Error extracting page {i+1}: {e}")
                    continue
        
        elif ext == 'docx':
            if not DocxDocument:
                raise ValidationError("DOCX support not available")
            
            doc = DocxDocument(file)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            text = "\n\n".join(paragraphs)
        
        elif ext == 'txt':
            text = file.read().decode('utf-8', errors='ignore')
        
        else:
            raise ValidationError(f"Unsupported file format: {ext}")
        
        text = text.strip()
        
        if not text:
            raise ValidationError("No text content found in document")
        
        logger.info(f"📝 Extracted {len(text)} characters from {filename}")
        
        # Generate summary
        if not genai or not settings.GEMINI_API_KEY:
            raise ValidationError("AI service not available")
        
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
        
        model = get_gemini_model()  # ✅ FIXED: Use helper function
        resp = model.generate_content(prompt)
        
        summary = resp.text.strip() if hasattr(resp, 'text') else "Unable to generate summary"
        
        # Save to history
        save_history(
            user_id=user_id,
            video_id=filename,
            title=f"Document: {filename}",
            summary=summary,
            mode="Document Summary"
        )
        
        logger.info(f"✅ Document summary generated for {filename}")
        
        return success_response(
            data={
                "filename": filename,
                "summary": summary,
                "metadata": {
                    "fileType": ext.UPPER(),
                    "textLength": len(text),
                    "pageCount": page_count if page_count > 0 else None,
                    "wasTruncated": len(text) > 30000
                }
            },
            message="Document processed successfully"
        )
        
    except ValidationError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"❌ Document processing error: {e}", exc_info=True)
        return error_response(f"Failed to process document: {str(e)}", 500)


# ---------------------------------------------------------------------
# HISTORY ROUTES BLUEPRINT
# ---------------------------------------------------------------------
history_bp = Blueprint('history', __name__)


@history_bp.route('/history', methods=['GET'])
@require_auth
@rate_limit(max_requests=100)
def get_history():
    """Get all history for user"""
    try:
        user_id = g.user_id
        history = get_all_history(user_id)
        
        return success_response(
            data={"history": history},
            message="History retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return error_response("Failed to fetch history", 500)


@history_bp.route('/history/<video_id>', methods=['GET'])
@require_auth
@rate_limit(max_requests=100)
def get_video_history(video_id):
    """Get history for specific video"""
    try:
        user_id = g.user_id
        history = get_history_by_video(user_id, video_id)
        
        if not history:
            raise ResourceNotFoundError("History not found")
        
        return success_response(
            data=history,
            message="History retrieved successfully"
        )
    except ResourceNotFoundError as e:
        return error_response(e.message, e.status_code)
    except Exception as e:
        logger.error(f"Error fetching video history: {e}")
        return error_response("Failed to fetch history", 500)


# ---------------------------------------------------------------------
# APPLICATION FACTORY
# ---------------------------------------------------------------------
def create_app():
    """Create and configure Flask application"""
    
    logger.info(f"🚀 Initializing {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = settings.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = settings.UPLOAD_MAX_SIZE
    
    # CORS
    CORS(app, 
         origins=settings.ALLOWED_ORIGINS,
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         expose_headers=["Content-Type", "Authorization"])
    
    logger.info("✅ CORS configured")
    
    # Initialize Clerk
    try:
        initialize_clerk()
        logger.info("✅ Clerk authentication initialized")
    except Exception as e:
        logger.warning(f"⚠️  Clerk initialization skipped: {e}")
    
    # Initialize Vector Store
    app.vector_store = VectorStore()
    logger.info("✅ Vector Store initialized")
    
    # Register middleware
    register_error_handlers(app)
    register_request_logger(app)
    logger.info("✅ Middleware registered")
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(video_bp, url_prefix='/api')
    app.register_blueprint(document_bp, url_prefix='/api')
    app.register_blueprint(history_bp, url_prefix='/api')
    logger.info("✅ Routes registered")
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """System health check"""
        db_healthy = db_connection.health_check()
        
        return jsonify({
            "status": "healthy" if db_healthy else "degraded",
            "version": settings.APP_VERSION,
            "authentication": "clerk",
            "services": {
                "database": "connected" if db_healthy else "disconnected",
                "vectorStore": app.vector_store is not None,
                "ai": settings.GEMINI_API_KEY is not None,
                "whisper": True,
                "embeddings": True,
                "clerk": settings.CLERK_SECRET_KEY is not None
            }
        }), 200 if db_healthy else 503
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "authentication": "clerk",
            "model": "gemini-flash-latest",  # ✅ ADDED
            "endpoints": {
                "health": "/api/health",
                "auth": "/api/auth/me",
                "docs": "https://github.com/your-repo"
            }
        })
    
    logger.info(f"✅ {settings.APP_NAME} initialized successfully")
    
    return app


# ---------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------
if __name__ == "__main__":
    try:
        # Validate configuration
        settings.validate()
        logger.info("✅ Configuration validated")
        
        # Create app
        app = create_app()
        
        # Run server
        logger.info("=" * 60)
        logger.info(f"🌐 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        logger.info(f"📍 Server: {settings.HOST}:{settings.PORT}")
        logger.info(f"🐛 Debug Mode: {settings.DEBUG}")
        logger.info(f"🔐 Authentication: Clerk")
        logger.info(f"🤖 AI Model: gemini-flash-latest")  # ✅ FIXED
        logger.info(f"💾 Database: {settings.MONGODB_DB_NAME}")
        logger.info("=" * 60)
        
        app.run(
            host=settings.HOST,
            port=settings.PORT,
            debug=settings.DEBUG
        )
        
    except Exception as e:
        logger.critical(f"❌ Failed to start application: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        try:
            db_connection.close()
            logger.info("Database connection closed")
        except:
            pass
