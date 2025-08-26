#!/usr/bin/env python3
"""Basic test to verify core modules work."""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test that core modules can be imported."""
    try:
        from core.config import settings
        print("✓ Config module imported successfully")
        
        from rag.schemas import DocumentChunk, RetrievalResult
        print("✓ RAG schemas imported successfully")
        
        from rag.chunking import DocumentProcessor
        print("✓ Document processor imported successfully")
        
        from rag.fusion import FusionEngine
        print("✓ Fusion engine imported successfully")
        
        print("\n✓ All core modules imported successfully!")
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_schemas():
    """Test schema creation."""
    try:
        from rag.schemas import DocumentChunk, RetrievalResult
        
        # Test DocumentChunk
        chunk = DocumentChunk(
            doc_id="test",
            source="test.md",
            title="Test Document",
            chunk_id="test_chunk_0001",
            chunk_index=0,
            content="This is a test chunk.",
            content_hash="abc123"
        )
        print("✓ DocumentChunk created successfully")
        
        # Test RetrievalResult
        result = RetrievalResult(
            doc_id="test",
            chunk_id="test_chunk_0001",
            source="test.md",
            title="Test Document",
            content="This is a test chunk.",
            score=0.8,
            retriever="bm25"
        )
        print("✓ RetrievalResult created successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Schema test failed: {e}")
        return False

def test_fusion():
    """Test fusion logic."""
    try:
        from rag.fusion import FusionEngine
        from rag.schemas import RetrievalResult
        
        # Create test results
        bm25_results = [
            RetrievalResult(
                doc_id="doc1",
                chunk_id="chunk1",
                source="test.md",
                title="Test",
                content="Test content 1",
                score=0.8,
                retriever="bm25"
            )
        ]
        
        vector_results = [
            RetrievalResult(
                doc_id="doc1",
                chunk_id="chunk1",
                source="test.md",
                title="Test",
                content="Test content 1",
                score=0.9,
                retriever="vector"
            )
        ]
        
        # Test RRF fusion
        fused = FusionEngine.fuse_results(bm25_results, vector_results, "rrf")
        print(f"✓ RRF fusion created {len(fused.results)} results")
        
        return True
        
    except Exception as e:
        print(f"✗ Fusion test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing RAG Chatbot core modules...\n")
    
    tests = [
        test_imports,
        test_schemas,
        test_fusion
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 All tests passed! Core functionality is working.")
    else:
        print("❌ Some tests failed. Check the errors above.")
        sys.exit(1) 