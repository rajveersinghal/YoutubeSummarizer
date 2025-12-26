# backend/services/ai_service.py - WITH RAG FALLBACK & STABLE MODELS

import google.generativeai as genai
from typing import List, Dict, Optional
from config.settings import settings
from config.logging_config import logger
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings as ChromaSettings

class AIService:
    """AI Service using Google Gemini with RAG fallback"""
    
    def __init__(self):
        """Initialize Gemini AI and RAG"""
        self.gemini_available = False
        self.rag_available = False
        self.model_name = None
        
        # Try to initialize Gemini with multiple models
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # ✅ TRY MULTIPLE MODELS IN ORDER OF PREFERENCE
            models_to_try = [
                'gemini-1.5-flash',      # Stable, free tier
                'gemini-1.5-pro',        # More powerful
                'gemini-pro',            # Older but stable
                'gemini-2.0-flash-exp'   # Experimental (may fail)
            ]
            
            for model_name in models_to_try:
                try:
                    logger.info(f"🔍 Trying model: {model_name}")
                    self.model = genai.GenerativeModel(model_name)
                    
                    # Test the API
                    test_response = self.model.generate_content("Hello")
                    
                    if test_response and test_response.text:
                        self.gemini_available = True
                        self.model_name = model_name
                        logger.info(f"✅ Gemini AI initialized with model: {model_name}")
                        break
                        
                except Exception as e:
                    logger.warning(f"⚠️ Model {model_name} failed: {e}")
                    continue
            
            if not self.gemini_available:
                logger.warning("⚠️ All Gemini models failed")
                logger.info("🔄 Falling back to RAG mode")
                
        except Exception as e:
            logger.warning(f"⚠️ Gemini initialization failed: {e}")
            logger.info("🔄 Falling back to RAG mode")
        
        # Initialize RAG (local embeddings) as fallback
        try:
            logger.info("🔄 Initializing RAG...")
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            self.chroma_client = chromadb.Client(ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            ))
            self.collection = self.chroma_client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
            self.rag_available = True
            logger.info("✅ RAG initialized successfully")
        except Exception as e:
            logger.error(f"❌ RAG initialization failed: {e}")
            logger.warning("⚠️ No AI backend available!")
    
    async def generate_response(
        self, 
        message: str, 
        history: List[Dict] = None,
        context: Optional[str] = None,
        context_type: Optional[str] = None
    ) -> str:
        """
        Generate AI response with fallback to RAG
        """
        # Try Gemini first
        if self.gemini_available:
            try:
                return await self._generate_with_gemini(message, history, context, context_type)
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"⚠️ Gemini failed: {error_msg}")
                
                # Check if it's an API key error
                if "API_KEY_INVALID" in error_msg or "expired" in error_msg.lower():
                    logger.error("❌ API Key is invalid or expired")
                    self.gemini_available = False
                    logger.info("🔄 Falling back to RAG")
                elif "quota" in error_msg.lower():
                    logger.warning("⚠️ API quota exceeded, falling back to RAG")
                    self.gemini_available = False
                else:
                    logger.info("🔄 Falling back to RAG")
        
        # Fallback to RAG
        if self.rag_available:
            return await self._generate_with_rag(message, context, context_type)
        
        # Last resort - provide helpful error message
        return """⚠️ **AI Service Unavailable**

The AI service is currently unavailable. This could be due to:

1. **Invalid API Key**: Get a new key from https://aistudio.google.com/app/apikey
2. **API Quota Exceeded**: Wait for quota reset or upgrade your plan
3. **Model Access**: Try enabling the Generative Language API

**Troubleshooting:**
- Check your `.env` file has `GEMINI_API_KEY=your_key_here`
- Verify the API key is valid at Google AI Studio
- Make sure you have free quota remaining

For now, the system is running in offline mode with limited functionality."""
    
    async def _generate_with_gemini(
        self,
        message: str,
        history: List[Dict] = None,
        context: Optional[str] = None,
        context_type: Optional[str] = None
    ) -> str:
        """Generate response using Gemini"""
        try:
            # Build conversation history
            chat_history = []
            
            if history:
                for msg in history:
                    chat_history.append({
                        "role": msg.get("role"),
                        "parts": [msg.get("content")]
                    })
            
            # Add context if provided
            if context and context.strip():
                logger.info(f"📄 Adding {context_type or 'context'} ({len(context)} chars)")
                
                # Limit context size to avoid token limits
                max_context_length = 30000  # ~30k chars
                if len(context) > max_context_length:
                    logger.warning(f"⚠️ Context too large ({len(context)} chars), truncating to {max_context_length}")
                    context = context[:max_context_length] + "...\n\n[Content truncated due to length]"
                
                if context_type == "youtube" or context_type == "video":
                    context_message = f"""You are analyzing a YouTube video. Here is the complete transcript:

===== VIDEO TRANSCRIPT START =====
{context}
===== VIDEO TRANSCRIPT END =====

Based on this transcript, please answer the following question or provide the requested information."""
                
                elif context_type == "document":
                    context_message = f"""You are analyzing a document. Here is the complete document content:

===== DOCUMENT CONTENT START =====
{context}
===== DOCUMENT CONTENT END =====

Based on this document, please answer the following question or provide the requested information."""
                
                else:
                    context_message = f"""Here is some relevant context:

{context}

Based on this context, please answer the following question."""
                
                # Add context as system message
                chat_history.append({
                    "role": "user",
                    "parts": [context_message]
                })
                
                chat_history.append({
                    "role": "model",
                    "parts": ["I've read and understood the content. I'm ready to answer your questions about it."]
                })
            
            # Generate response
            logger.info(f"🤖 Generating response with {self.model_name} (history: {len(chat_history)} messages)")
            
            if chat_history:
                chat = self.model.start_chat(history=chat_history)
                response = chat.send_message(message)
            else:
                response = self.model.generate_content(message)
            
            response_text = response.text.strip()
            
            logger.info(f"✅ Response generated ({len(response_text)} chars)")
            
            return response_text
            
        except Exception as e:
            logger.error(f"❌ Gemini generation error: {e}", exc_info=True)
            raise
    
    async def _generate_with_rag(
        self, 
        message: str, 
        context: Optional[str] = None,
        context_type: Optional[str] = None
    ) -> str:
        """Generate response using RAG (local)"""
        try:
            logger.info("🔍 Using RAG for response generation")
            
            if context and context.strip():
                # Store context in vector DB temporarily
                doc_id = f"temp_{abs(hash(context))}"
                
                # Split context into chunks
                chunks = self._chunk_text(context, chunk_size=500)
                
                logger.info(f"📚 Created {len(chunks)} chunks from context")
                
                # Add to collection
                self.collection.add(
                    documents=chunks,
                    ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
                    metadatas=[{"source": "temp"} for _ in chunks]
                )
                
                # Query relevant chunks
                results = self.collection.query(
                    query_texts=[message],
                    n_results=min(5, len(chunks))
                )
                
                relevant_chunks = results['documents'][0] if results['documents'] else []
                
                # Generate response based on chunks
                if relevant_chunks:
                    if context_type == "youtube" or context_type == "video":
                        response = f"**📹 Video Analysis (Offline Mode)**\n\n"
                        response += f"Based on the video transcript, here are the relevant sections:\n\n"
                    elif context_type == "document":
                        response = f"**📄 Document Analysis (Offline Mode)**\n\n"
                        response += f"Based on the document content, here are the relevant sections:\n\n"
                    else:
                        response = f"**🔍 Content Analysis (Offline Mode)**\n\n"
                    
                    for i, chunk in enumerate(relevant_chunks, 1):
                        response += f"**Section {i}:**\n{chunk}\n\n"
                    
                    response += f"**Note:** This is a RAG-based response. For better AI-generated summaries, please ensure Gemini API is available."
                    
                    # Clean up temp docs
                    try:
                        self.collection.delete(where={"source": "temp"})
                    except:
                        pass
                    
                    return response
            
            # Default response without context
            return f"""**💭 Question:** {message}

⚠️ **Offline Mode**: I'm currently running in offline mode without AI capabilities.

To get AI-powered responses:
1. Get a Gemini API key from https://aistudio.google.com/app/apikey
2. Add it to your `.env` file: `GEMINI_API_KEY=your_key_here`
3. Restart the backend server

For document/video analysis, I can still show you relevant excerpts from the content."""
            
        except Exception as e:
            logger.error(f"❌ RAG generation error: {e}", exc_info=True)
            return "I apologize, but I'm unable to generate a response at the moment. Please check the system logs."
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    async def summarize_document(self, document_text: str, title: str = "document") -> str:
        """Summarize a document"""
        try:
            if self.gemini_available:
                prompt = f"""Please provide a comprehensive summary of this document.

Title: {title}

Provide:
1. A brief overview (2-3 sentences)
2. Key points and main ideas
3. Important details or conclusions"""
                
                # Limit document size
                max_length = 30000
                if len(document_text) > max_length:
                    document_text = document_text[:max_length] + "...\n\n[Document truncated]"
                
                return await self.generate_response(
                    prompt,
                    context=document_text,
                    context_type="document"
                )
            else:
                # RAG fallback
                chunks = self._chunk_text(document_text, chunk_size=1000)
                summary = f"**📄 Document: {title}**\n\n"
                summary += f"**Content Preview:**\n{chunks[0][:500] if chunks else 'No content'}...\n\n"
                summary += f"**Statistics:**\n"
                summary += f"- Total Length: {len(document_text):,} characters\n"
                summary += f"- Word Count: {len(document_text.split()):,} words\n"
                summary += f"- Sections: {len(chunks)}\n\n"
                summary += f"⚠️ **Note:** Running in offline mode. For AI-generated summaries, please configure Gemini API."
                return summary
                
        except Exception as e:
            logger.error(f"❌ Document summarization error: {e}")
            return "Failed to summarize document"
    
    async def summarize_video(self, transcript: str, title: str = "video") -> str:
        """Summarize a video transcript"""
        try:
            if self.gemini_available:
                prompt = f"""Please provide a comprehensive summary of this YouTube video.

Title: {title}

Based on the transcript, provide:
1. A brief overview of what the video is about
2. Main topics and key points discussed
3. Important takeaways or conclusions"""
                
                # Limit transcript size
                max_length = 30000
                if len(transcript) > max_length:
                    transcript = transcript[:max_length] + "...\n\n[Transcript truncated]"
                
                return await self.generate_response(
                    prompt,
                    context=transcript,
                    context_type="youtube"
                )
            else:
                # RAG fallback
                chunks = self._chunk_text(transcript, chunk_size=1000)
                summary = f"**📹 Video: {title}**\n\n"
                summary += f"**Transcript Preview:**\n{chunks[0][:500] if chunks else 'No transcript'}...\n\n"
                summary += f"**Statistics:**\n"
                summary += f"- Total Length: {len(transcript):,} characters\n"
                summary += f"- Word Count: {len(transcript.split()):,} words\n"
                summary += f"- Duration (estimated): {len(transcript.split()) // 150} minutes\n\n"
                summary += f"⚠️ **Note:** Running in offline mode. For AI-generated summaries, please configure Gemini API."
                return summary
                
        except Exception as e:
            logger.error(f"❌ Video summarization error: {e}")
            return "Failed to summarize video"
