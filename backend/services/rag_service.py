# services/rag_service.py - FASTAPI ASYNC VERSION (COMPLETE)
import asyncio
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import google.generativeai as genai

from services.embedding_service import embedding_service, get_embedding_model
from models.chunk import get_chunks_by_video
from config.settings import settings
from config.logging_config import logger


# ============================================================================
# GEMINI CONFIGURATION
# ============================================================================

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)


def get_gemini_model():
    """
    Get configured Gemini model
    
    Returns:
        Configured GenerativeModel instance
    """
    try:
        return genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config={
                "temperature": settings.GEMINI_TEMPERATURE,
                "max_output_tokens": settings.GEMINI_MAX_OUTPUT_TOKENS,
            }
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini model: {e}")
        raise


# ============================================================================
# RAG SERVICE
# ============================================================================

class RAGService:
    """Retrieval-Augmented Generation service"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.default_top_k = settings.TOP_K_CHUNKS
    
    async def search_relevant_chunks(
        self,
        video_id: str,
        question: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks using semantic similarity
        
        Args:
            video_id: Video ID
            question: User question
            top_k: Number of chunks to retrieve
        
        Returns:
            List of relevant chunks with similarity scores
        """
        try:
            top_k = top_k or self.default_top_k
            
            logger.info(f"🔍 Searching for relevant chunks in video {video_id}")
            
            # Generate question embedding
            question_embedding = await self.embedding_service.generate_single_embedding(question)
            
            # Get all chunks for video
            chunks = await get_chunks_by_video(video_id, include_embeddings=True)
            
            if not chunks:
                logger.warning(f"⚠️  No chunks found for video {video_id}")
                return []
            
            # Extract embeddings
            chunk_embeddings = [np.array(chunk['embedding']) for chunk in chunks]
            
            # Find similar chunks
            similar_indices = self.embedding_service.find_similar_chunks(
                question_embedding,
                chunk_embeddings,
                top_k=top_k
            )
            
            # Format results
            relevant_chunks = []
            for idx, similarity in similar_indices:
                chunk = chunks[idx].copy()
                chunk['similarity'] = similarity
                # Remove embedding from response to reduce size
                chunk.pop('embedding', None)
                relevant_chunks.append(chunk)
            
            logger.info(f"✅ Found {len(relevant_chunks)} relevant chunks")
            return relevant_chunks
            
        except Exception as e:
            logger.error(f"❌ Chunk search failed: {e}")
            raise
    
    def build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Build context string from chunks
        
        Args:
            chunks: List of chunk dictionaries
        
        Returns:
            Formatted context string
        """
        if not chunks:
            return ""
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            text = chunk.get('text', '')
            similarity = chunk.get('similarity', 0)
            context_parts.append(f"[Context {i}] (Relevance: {similarity:.2f})\n{text}")
        
        return "\n\n".join(context_parts)
    
    def create_rag_prompt(
        self,
        question: str,
        context: str,
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Create RAG prompt for Gemini
        
        Args:
            question: User question
            context: Retrieved context
            system_instruction: Optional system instruction
        
        Returns:
            Formatted prompt
        """
        default_instruction = """You are a helpful AI assistant. Answer the question based ONLY on the provided context from the video transcript. 
If the answer cannot be found in the context, say "I cannot find that information in the video."
Provide concise, accurate answers in 2-3 sentences."""
        
        instruction = system_instruction or default_instruction
        
        prompt = f"""{instruction}

Context from video transcript:
{context}

Question: {question}

Answer:"""
        
        return prompt
    
    async def generate_answer_async(
        self,
        prompt: str,
        model: Optional[Any] = None
    ) -> str:
        """
        Generate answer using Gemini (async)
        
        Args:
            prompt: Input prompt
            model: Optional Gemini model instance
        
        Returns:
            Generated answer
        """
        try:
            if model is None:
                model = get_gemini_model()
            
            logger.info("🤖 Generating answer with Gemini...")
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                model.generate_content,
                prompt
            )
            
            answer = response.text.strip() if hasattr(response, 'text') else "Unable to generate answer"
            
            logger.info(f"✅ Answer generated: {len(answer)} characters")
            return answer
            
        except Exception as e:
            logger.error(f"❌ Answer generation failed: {e}")
            raise
    
    async def answer_question_from_video(
        self,
        video_id: str,
        question: str,
        top_k: int = None,
        model: Optional[Any] = None,
        include_context: bool = True
    ) -> Dict[str, Any]:
        """
        Answer question using RAG
        
        Args:
            video_id: Video ID
            question: User question
            top_k: Number of chunks to retrieve
            model: Optional Gemini model
            include_context: Whether to include context in response
        
        Returns:
            Dictionary with answer and metadata
        """
        try:
            logger.info(f"❓ Answering question for video {video_id}")
            
            # Search relevant chunks
            relevant_chunks = await self.search_relevant_chunks(
                video_id,
                question,
                top_k
            )
            
            if not relevant_chunks:
                return {
                    "answer": "No relevant information found in the video.",
                    "confidence": 0.0,
                    "sources": [],
                    "context": ""
                }
            
            # Build context
            context = self.build_context(relevant_chunks)
            
            # Create prompt
            prompt = self.create_rag_prompt(question, context)
            
            # Generate answer
            answer = await self.generate_answer_async(prompt, model)
            
            # Calculate average confidence
            avg_similarity = sum(c.get('similarity', 0) for c in relevant_chunks) / len(relevant_chunks)
            
            result = {
                "answer": answer,
                "confidence": float(avg_similarity),
                "sources": [
                    {
                        "chunkIndex": chunk.get('chunkIndex'),
                        "text": chunk.get('text'),
                        "similarity": chunk.get('similarity')
                    }
                    for chunk in relevant_chunks
                ]
            }
            
            if include_context:
                result["context"] = context
            
            logger.info("✅ RAG question answered successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ RAG error: {e}")
            return {
                "answer": f"Error: {str(e)}",
                "confidence": 0.0,
                "sources": [],
                "context": ""
            }
    
    async def answer_multiple_questions(
        self,
        video_id: str,
        questions: List[str],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Answer multiple questions for a video
        
        Args:
            video_id: Video ID
            questions: List of questions
            top_k: Number of chunks per question
        
        Returns:
            List of answer dictionaries
        """
        try:
            logger.info(f"❓ Answering {len(questions)} questions for video {video_id}")
            
            # Process all questions concurrently
            tasks = [
                self.answer_question_from_video(video_id, q, top_k, include_context=False)
                for q in questions
            ]
            
            results = await asyncio.gather(*tasks)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Multiple questions error: {e}")
            return []
    
    async def summarize_video(
        self,
        video_id: str,
        max_chunks: int = 10,
        model: Optional[Any] = None
    ) -> str:
        """
        Generate video summary using top chunks
        
        Args:
            video_id: Video ID
            max_chunks: Maximum chunks to use
            model: Optional Gemini model
        
        Returns:
            Video summary
        """
        try:
            logger.info(f"📝 Generating summary for video {video_id}")
            
            # Get chunks
            chunks = await get_chunks_by_video(video_id)
            
            if not chunks:
                return "No content available for summarization."
            
            # Take first N chunks
            selected_chunks = chunks[:max_chunks]
            context = "\n\n".join([c['text'] for c in selected_chunks])
            
            prompt = f"""Summarize the following video transcript in 3-4 sentences:

{context}

Summary:"""
            
            summary = await self.generate_answer_async(prompt, model)
            
            logger.info("✅ Summary generated")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Summarization failed: {e}")
            return f"Error generating summary: {str(e)}"
    
    async def chat_with_video(
        self,
        video_id: str,
        messages: List[Dict[str, str]],
        top_k: int = None
    ) -> str:
        """
        Chat with video using conversation history
        
        Args:
            video_id: Video ID
            messages: List of message dicts with 'role' and 'content'
            top_k: Number of chunks to retrieve
        
        Returns:
            AI response
        """
        try:
            logger.info(f"💬 Chat with video {video_id}")
            
            # Get last user message
            last_message = messages[-1]['content'] if messages else ""
            
            # Search relevant chunks
            relevant_chunks = await self.search_relevant_chunks(
                video_id,
                last_message,
                top_k
            )
            
            # Build context
            context = self.build_context(relevant_chunks)
            
            # Build conversation history
            history = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in messages[:-1]
            ])
            
            prompt = f"""You are chatting about a video. Use the context below and conversation history to answer.

Context from video:
{context}

Conversation history:
{history}

User: {last_message}
Assistant:"""
            
            response = await self.generate_answer_async(prompt)
            
            logger.info("✅ Chat response generated")
            return response
            
        except Exception as e:
            logger.error(f"❌ Chat failed: {e}")
            return f"Error: {str(e)}"


# ============================================================================
# GLOBAL RAG SERVICE INSTANCE
# ============================================================================

rag_service = RAGService()


# ============================================================================
# CONVENIENCE FUNCTIONS (Backward Compatibility)
# ============================================================================

def answer_question_from_video(
    video_id: str,
    question: str,
    vector_store=None,
    model=None,
    top_k: int = 5
) -> Tuple[str, List[Dict]]:
    """
    Answer question using RAG (sync wrapper for backward compatibility)
    
    Args:
        video_id: Video ID
        question: User question
        vector_store: (Deprecated) Not used anymore
        model: Optional Gemini model
        top_k: Number of chunks to retrieve
    
    Returns:
        Tuple of (answer, context_chunks)
    """
    try:
        logger.info(f"❓ Answering question for video {video_id}")
        
        # Get embedding
        embedding_model = get_embedding_model()
        question_embedding = embedding_model.encode([question])[0]
        
        # Get chunks from database (sync version)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        chunks = loop.run_until_complete(get_chunks_by_video(video_id, include_embeddings=True))
        
        if not chunks:
            logger.warning(f"No relevant chunks found for video {video_id}")
            return "No relevant information found in the video.", []
        
        # Extract embeddings
        chunk_embeddings = [np.array(chunk['embedding']) for chunk in chunks]
        
        # Find similar chunks
        from sklearn.metrics.pairwise import cosine_similarity
        
        similarities = cosine_similarity(
            question_embedding.reshape(1, -1),
            np.array(chunk_embeddings)
        )[0]
        
        # Get top k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        context_chunks = []
        for idx in top_indices:
            chunk = chunks[idx].copy()
            chunk['similarity'] = float(similarities[idx])
            chunk.pop('embedding', None)
            context_chunks.append(chunk)
        
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


async def answer_question_async(
    video_id: str,
    question: str,
    top_k: int = 5,
    model=None
) -> Dict[str, Any]:
    """
    Answer question using RAG (async wrapper)
    
    Args:
        video_id: Video ID
        question: User question
        top_k: Number of chunks to retrieve
        model: Optional Gemini model
    
    Returns:
        Dictionary with answer and metadata
    """
    return await rag_service.answer_question_from_video(
        video_id,
        question,
        top_k,
        model
    )


async def summarize_video_async(
    video_id: str,
    max_chunks: int = 10
) -> str:
    """
    Generate video summary (async wrapper)
    
    Args:
        video_id: Video ID
        max_chunks: Maximum chunks to use
    
    Returns:
        Video summary
    """
    return await rag_service.summarize_video(video_id, max_chunks)


async def chat_with_video_async(
    video_id: str,
    messages: List[Dict[str, str]],
    top_k: int = 5
) -> str:
    """
    Chat with video (async wrapper)
    
    Args:
        video_id: Video ID
        messages: Conversation history
        top_k: Number of chunks to retrieve
    
    Returns:
        AI response
    """
    return await rag_service.chat_with_video(video_id, messages, top_k)


            
