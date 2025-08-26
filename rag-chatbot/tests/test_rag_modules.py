import pytest
from app.rag.schemas import DocumentChunk, RetrievalResult
from app.rag.fusion import FusionEngine


def test_document_chunk_creation():
    """Test DocumentChunk creation."""
    chunk = DocumentChunk(
        doc_id="test",
        source="test.md",
        title="Test Document",
        chunk_id="test_chunk_0001",
        chunk_index=0,
        content="This is a test chunk.",
        content_hash="abc123"
    )
    
    assert chunk.doc_id == "test"
    assert chunk.content == "This is a test chunk."
    assert chunk.chunk_id == "test_chunk_0001"


def test_retrieval_result_creation():
    """Test RetrievalResult creation."""
    result = RetrievalResult(
        doc_id="test",
        chunk_id="test_chunk_0001",
        source="test.md",
        title="Test Document",
        content="This is a test chunk.",
        score=0.8,
        retriever="bm25"
    )
    
    assert result.doc_id == "test"
    assert result.score == 0.8
    assert result.retriever == "bm25"


def test_fusion_rrf():
    """Test RRF fusion."""
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
    
    fused = FusionEngine.fuse_results(bm25_results, vector_results, "rrf")
    
    assert len(fused.results) == 1
    assert fused.fusion_method == "rrf"
    assert fused.retrieval_debug["bm25_count"] == 1
    assert fused.retrieval_debug["vector_count"] == 1


def test_fusion_weighted():
    """Test weighted fusion."""
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
    
    fused = FusionEngine.fuse_results(
        bm25_results, vector_results, "weighted",
        bm25_weight=0.4, vector_weight=0.6
    )
    
    assert len(fused.results) == 1
    assert fused.fusion_method == "weighted"
    assert fused.fusion_params["bm25_weight"] == 0.4
    assert fused.fusion_params["vector_weight"] == 0.6


def test_deduplication():
    """Test result deduplication."""
    results = [
        RetrievalResult(
            doc_id="doc1",
            chunk_id="chunk1",
            source="test.md",
            title="Test",
            content="Test content",
            score=0.8,
            retriever="bm25"
        ),
        RetrievalResult(
            doc_id="doc1",
            chunk_id="chunk1",  # Same chunk_id
            source="test.md",
            title="Test",
            content="Test content",
            score=0.9,
            retriever="vector"
        )
    ]
    
    deduplicated = FusionEngine.deduplicate_results(results)
    assert len(deduplicated) == 1 