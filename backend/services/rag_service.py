# services/rag_service.py
from typing import List, Dict, Tuple
import numpy as np
from services.embedding_service import get_embedding_model
from config.logging_config import logger
import google.generativeai as genai
from config.settings import settings

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

def get_gemini_model():
    """Get configured Gemini model - using latest available"""
    return genai.GenerativeModel(
        model_name="gemini-flash-latest",  # ✅ Works with your API key
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 1024,
        }
    )

def answer_question_from_video(
    video_id: str,
    question: str,
    vector_store,
    model=None,
    top_k: int = 5
) -> Tuple[str, List[Dict]]:
    """Answer question using RAG"""
    try:
        logger.info(f"❓ Answering question for video {video_id}")
        
        # Get embedding
        embedding_model = get_embedding_model()
        question_embedding = embedding_model.encode([question])[0]
        
        # Search vector store
        context_chunks = vector_store.search(video_id, question_embedding, top_k)
        
        if not context_chunks:
            logger.warning(f"No relevant chunks found for video {video_id}")
            return "No relevant information found in the video.", []
        
        logger.info(f"Found {len(context_chunks)} relevant chunks")
        
        # Build context
        context = "\n\n".join([chunk["text"] for chunk in context_chunks])
        
        # Create prompt
        prompt = f"""Answer based on this video transcript:

{context}

Question: {question}

Answer in 2-3 sentences:"""
        
        # Generate answer
        if model is None:
            model = get_gemini_model()
        
        response = model.generate_content(prompt)
        answer = response.text.strip() if hasattr(response, 'text') else "Unable to generate answer"
        
        logger.info(f"✅ Answer generated")
        
        return answer, context_chunks
        
    except Exception as e:
        logger.error(f"❌ RAG error: {e}")
        return f"Error: {str(e)}", []
