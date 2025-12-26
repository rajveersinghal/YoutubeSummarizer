# backend/services/ai_service.py - GROQ + GEMINI SUPPORT

import os
from typing import List, Dict, Optional
from config.settings import settings
from config.logging_config import logger

# Try importing different AI libraries
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except:
    GROQ_AVAILABLE = False
    logger.warning("⚠️ Groq not installed. Install: pip install groq")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except:
    GEMINI_AVAILABLE = False
    logger.warning("⚠️ Gemini not installed. Install: pip install google-generativeai")

class AIService:
    """AI Service supporting multiple LLM providers"""
    
    def __init__(self):
        """Initialize AI service with multiple providers"""
        self.provider = None
        self.model_name = None
        self.groq_client = None
        self.gemini_model = None
        
        # Try to initialize BOTH providers
        self._init_groq()
        self._init_gemini()
        
        # Set primary provider
        if self.groq_client:
            self.provider = "groq"
            logger.info(f"🚀 Primary provider: Groq ({self.model_name})")
        elif self.gemini_model:
            self.provider = "gemini"
            logger.info(f"🤖 Primary provider: Gemini ({self.model_name})")
        else:
            logger.error("❌ No AI provider available!")
            logger.info("💡 Get free API keys:")
            logger.info("   - Groq (RECOMMENDED): https://console.groq.com/keys")
            logger.info("   - Gemini: https://aistudio.google.com/app/apikey")
    
    def _init_groq(self):
        """Initialize Groq"""
        if not GROQ_AVAILABLE:
            return
        
        if not hasattr(settings, 'GROQ_API_KEY') or not settings.GROQ_API_KEY:
            logger.info("ℹ️ Groq API key not configured")
            return
        
        try:
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
            
            # Test the API
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": "Hello"}],
                model="llama-3.3-70b-versatile",
                max_tokens=10
            )
            
            self.model_name = "llama-3.3-70b-versatile"
            logger.info(f"✅ Groq initialized with {self.model_name}")
            
        except Exception as e:
            logger.warning(f"⚠️ Groq initialization failed: {e}")
            self.groq_client = None
    
    def _init_gemini(self):
        """Initialize Gemini"""
        if not GEMINI_AVAILABLE:
            return
        
        if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
            logger.info("ℹ️ Gemini API key not configured")
            return
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Try multiple models
            models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro', 'gemini-2.0-flash-exp']
            
            for model in models:
                try:
                    test_model = genai.GenerativeModel(model)
                    response = test_model.generate_content("Hello")
                    
                    if response and response.text:
                        self.gemini_model = test_model
                        
                        # Store model name for later use
                        if not self.model_name:
                            self.model_name = model
                        
                        self.gemini_model_name = model
                        logger.info(f"✅ Gemini initialized with {model}")
                        return
                        
                except Exception as e:
                    logger.debug(f"Model {model} failed: {e}")
                    continue
            
            logger.warning("⚠️ All Gemini models failed")
            
        except Exception as e:
            logger.warning(f"⚠️ Gemini initialization failed: {e}")
            self.gemini_model = None
    
    async def generate_response(
        self, 
        message: str, 
        history: List[Dict] = None,
        context: Optional[str] = None,
        context_type: Optional[str] = None
    ) -> str:
        """Generate AI response with automatic fallback"""
        try:
            # Try Groq first (faster)
            if self.groq_client:
                try:
                    return await self._generate_groq(message, history, context, context_type)
                except Exception as e:
                    logger.warning(f"⚠️ Groq failed: {e}")
                    logger.info("🔄 Falling back to Gemini...")
            
            # Fallback to Gemini
            if self.gemini_model:
                try:
                    return await self._generate_gemini(message, history, context, context_type)
                except Exception as e:
                    logger.error(f"❌ Gemini also failed: {e}")
            
            # Both failed
            return "⚠️ AI service temporarily unavailable. Please try again later."
            
        except Exception as e:
            logger.error(f"❌ AI generation error: {e}", exc_info=True)
            return f"⚠️ Error: {str(e)}"
    
    async def _generate_groq(
        self,
        message: str,
        history: List[Dict] = None,
        context: Optional[str] = None,
        context_type: Optional[str] = None
    ) -> str:
        """Generate with Groq"""
        try:
            logger.info(f"🚀 Generating with Groq ({self.model_name})")
            
            messages = []
            
            # Add context if provided
            if context and context.strip():
                logger.info(f"📄 Adding {context_type or 'context'} ({len(context)} chars)")
                
                # Limit context
                max_length = 30000
                if len(context) > max_length:
                    context = context[:max_length] + "...\n[Content truncated]"
                
                if context_type == "youtube" or context_type == "video":
                    system_msg = f"""You are analyzing a YouTube video. Here is the transcript:

{context}

Answer questions based on this transcript."""
                
                elif context_type == "document":
                    system_msg = f"""You are analyzing a document. Here is the content:

{context}

Answer questions based on this document."""
                
                else:
                    system_msg = f"Context: {context}"
                
                # Add as user/assistant pair (Groq doesn't support system role well)
                messages.append({
                    "role": "user",
                    "content": f"[CONTEXT]\n{system_msg}"
                })
                messages.append({
                    "role": "assistant",
                    "content": "I've read and understood the context. I'm ready to answer your questions."
                })
            
            # Add history
            if history:
                for msg in history[-10:]:  # Last 10 messages
                    role = msg.get("role")
                    if role == "assistant":
                        role = "assistant"
                    elif role == "model":
                        role = "assistant"
                    else:
                        role = "user"
                    
                    messages.append({
                        "role": role,
                        "content": msg.get("content")
                    })
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Generate response
            response = self.groq_client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                temperature=0.7,
                max_tokens=2000,
            )
            
            result = response.choices[0].message.content
            logger.info(f"✅ Groq response ({len(result)} chars)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Groq error: {e}")
            raise
    
    async def _generate_gemini(
        self,
        message: str,
        history: List[Dict] = None,
        context: Optional[str] = None,
        context_type: Optional[str] = None
    ) -> str:
        """Generate with Gemini"""
        try:
            logger.info(f"🤖 Generating with Gemini ({self.gemini_model_name})")
            
            chat_history = []
            
            # Add context if provided
            if context and context.strip():
                logger.info(f"📄 Adding {context_type or 'context'} ({len(context)} chars)")
                
                # Limit context
                max_length = 30000
                if len(context) > max_length:
                    context = context[:max_length] + "...\n[Content truncated]"
                
                if context_type == "youtube" or context_type == "video":
                    context_msg = f"""You are analyzing a YouTube video. Here is the transcript:

{context}

Answer questions based on this transcript."""
                
                elif context_type == "document":
                    context_msg = f"""You are analyzing a document. Here is the content:

{context}

Answer questions based on this document."""
                
                else:
                    context_msg = context
                
                chat_history.append({"role": "user", "parts": [context_msg]})
                chat_history.append({"role": "model", "parts": ["I've read and understood the content. I'm ready to answer your questions."]})
            
            # Add history
            if history:
                for msg in history[-10:]:
                    role = msg.get("role")
                    if role == "assistant":
                        role = "model"
                    
                    chat_history.append({
                        "role": role,
                        "parts": [msg.get("content")]
                    })
            
            # Generate response
            if chat_history:
                chat = self.gemini_model.start_chat(history=chat_history)
                response = chat.send_message(message)
            else:
                response = self.gemini_model.generate_content(message)
            
            result = response.text.strip()
            logger.info(f"✅ Gemini response ({len(result)} chars)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Gemini error: {e}")
            raise
    
    async def summarize_document(self, document_text: str, title: str = "document") -> str:
        """Summarize document"""
        prompt = f"""Provide a comprehensive summary of this document titled "{title}".

Include:
1. Brief overview (2-3 sentences)
2. Key points and main ideas
3. Important details or conclusions"""
        
        return await self.generate_response(
            prompt,
            context=document_text[:30000],
            context_type="document"
        )
    
    async def summarize_video(self, transcript: str, title: str = "video") -> str:
        """Summarize video"""
        prompt = f"""Provide a comprehensive summary of this YouTube video titled "{title}".

Include:
1. What the video is about
2. Main topics and key points
3. Important takeaways"""
        
        return await self.generate_response(
            prompt,
            context=transcript[:30000],
            context_type="youtube"
        )
