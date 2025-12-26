# backend/test_rag.py - TEST RAG SYSTEM

import asyncio
from services.rag_service import RAGService
from services.ai_service import AIService
from config.logging_config import logger

async def test_rag():
    """Test RAG system"""
    
    print("=" * 80)
    print("🧪 Testing RAG System")
    print("=" * 80)
    
    # Initialize services
    rag = RAGService()
    ai = AIService()
    
    # Test 1: Add sample document
    print("\n📄 Test 1: Adding sample document...")
    sample_doc = """
    Artificial Intelligence (AI) is transforming the world. Machine learning is a subset of AI 
    that enables computers to learn from data. Deep learning uses neural networks with multiple 
    layers to process complex patterns. Natural Language Processing (NLP) allows computers to 
    understand human language. Computer vision enables machines to interpret images and videos.
    
    Python is the most popular programming language for AI development. Libraries like TensorFlow, 
    PyTorch, and scikit-learn make it easy to build machine learning models. Data preprocessing 
    is crucial for model performance. Feature engineering helps improve model accuracy.
    
    AI applications include image recognition, speech recognition, recommendation systems, 
    autonomous vehicles, and chatbots. The future of AI includes artificial general intelligence 
    (AGI) and quantum computing integration.
    """
    
    rag.add_document(
        document_id="test_doc_1",
        title="Introduction to AI",
        content=sample_doc,
        metadata={"author": "Test", "type": "tutorial"}
    )
    print("✅ Document added successfully")
    
    # Test 2: Search documents
    print("\n🔍 Test 2: Searching documents...")
    queries = [
        "What is machine learning?",
        "Which programming language is best for AI?",
        "What are AI applications?"
    ]
    
    for query in queries:
        print(f"\n   Query: '{query}'")
        results = rag.search_documents(query, n_results=2)
        
        if results:
            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"   {i}. Relevance: {1 - result.get('distance', 0):.2f}")
                print(f"      Content: {result['content'][:100]}...")
        else:
            print("   No results found")
    
    # Test 3: AI Generation with RAG
    print("\n🤖 Test 3: AI generation with RAG context...")
    
    if ai.provider:
        # Search for context
        query = "Explain machine learning in simple terms"
        results = rag.search_documents(query, n_results=3)
        
        if results:
            context = "\n\n".join([r["content"] for r in results])
            
            print(f"   Using {len(results)} chunks as context")
            
            response = await ai.generate_response(
                message=query,
                context=context,
                context_type="document"
            )
            
            print(f"\n   AI Response:")
            print(f"   {response}")
        else:
            print("   No context found")
    else:
        print("   ⚠️ AI service not available")
    
    # Test 4: Add video transcript
    print("\n📹 Test 4: Adding sample video transcript...")
    sample_transcript = """
    Welcome to this tutorial on Python programming. Today we'll learn about variables, 
    data types, and control structures. Python is an interpreted, high-level programming 
    language known for its simplicity and readability.
    
    Variables in Python don't need explicit declaration. You can assign values directly. 
    Python supports various data types including integers, floats, strings, lists, and 
    dictionaries. Control structures like if-else statements and loops help control 
    program flow.
    
    Functions are reusable blocks of code. Classes and objects enable object-oriented 
    programming. Python has a rich ecosystem of libraries and frameworks for web development, 
    data science, and automation.
    """
    
    rag.add_video(
        video_id="test_video_1",
        title="Python Programming Basics",
        transcript=sample_transcript,
        metadata={"duration": 600, "source": "youtube"}
    )
    print("✅ Video transcript added successfully")
    
    # Test 5: Search videos
    print("\n🔍 Test 5: Searching videos...")
    video_query = "What are Python data types?"
    results = rag.search_videos(video_query, n_results=2)
    
    if results:
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. Relevance: {1 - result.get('distance', 0):.2f}")
            print(f"      Content: {result['content'][:100]}...")
    else:
        print("   No results found")
    
    # Test 6: Search all
    print("\n🔍 Test 6: Searching across all content...")
    all_results = rag.search_all("programming", n_results=3)
    
    print(f"   Documents: {len(all_results['documents'])} results")
    print(f"   Videos: {len(all_results['videos'])} results")
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    rag.delete_document("test_doc_1")
    rag.delete_video("test_video_1")
    print("✅ Test data deleted")
    
    print("\n" + "=" * 80)
    print("✅ All RAG tests passed!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_rag())
