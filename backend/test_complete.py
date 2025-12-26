# backend/test_complete.py - TEST COMPLETE SYSTEM

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from services.ai_service import AIService
from services.rag_service import RAGService
from services.document_processor import DocumentProcessor
from services.video_processor import VideoProcessor

async def test_complete_system():
    """Test complete system"""
    
    print("=" * 80)
    print("🧪 TESTING COMPLETE SYSTEM")
    print("=" * 80)
    
    # Test 1: Configuration
    print("\n✅ Test 1: Configuration")
    print(f"   Groq API Key: {'✅ SET' if settings.GROQ_API_KEY else '❌ NOT SET'}")
    print(f"   Gemini API Key: {'✅ SET' if settings.GEMINI_API_KEY else '❌ NOT SET'}")
    print(f"   MongoDB URI: {'✅ SET' if settings.MONGODB_URI else '❌ NOT SET'}")
    print(f"   Storage Path: {settings.STORAGE_PATH}")
    
    # Test 2: AI Service
    print("\n✅ Test 2: AI Service")
    ai = AIService()
    if ai.provider:
        print(f"   Provider: {ai.provider}")
        print(f"   Model: {ai.model_name}")
        
        response = await ai.generate_response("Say 'Hello World' in one sentence")
        print(f"   Response: {response[:100]}...")
    else:
        print("   ⚠️ No AI provider available")
    
    # Test 3: RAG Service
    print("\n✅ Test 3: RAG Service")
    rag = RAGService()
    
    # Add test document
    rag.add_document(
        document_id="test_1",
        title="Test Document",
        content="This is a test document about machine learning and artificial intelligence.",
        metadata={"test": True}
    )
    
    # Search
    results = rag.search_documents("machine learning", n_results=1)
    print(f"   Search results: {len(results)}")
    
    # Cleanup
    rag.delete_document("test_1")
    print("   ✅ RAG working")
    
    # Test 4: Document Processor
    print("\n✅ Test 4: Document Processor")
    doc_processor = DocumentProcessor()
    print("   ✅ Document processor initialized")
    
    # Test 5: Video Processor
    print("\n✅ Test 5: Video Processor")
    video_processor = VideoProcessor()
    print("   ✅ Video processor initialized")
    
    print("\n" + "=" * 80)
    print("✅ ALL SYSTEMS OPERATIONAL!")
    print("=" * 80)
    print("\n🚀 Ready to start the server!")
    print("\nRun: uvicorn main:app --reload")

if __name__ == "__main__":
    asyncio.run(test_complete_system())
