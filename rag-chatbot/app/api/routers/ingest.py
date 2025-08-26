import os
import asyncio
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.api.deps import require_api_key
from app.rag.chunking import DocumentProcessor
from app.rag.retrievers.hybrid import HybridRetriever
from app.rag.schemas import IngestResponse
from app.services.document_intelligence import get_document_intelligence_service

router = APIRouter(prefix="/ingest", tags=["ingest"])

# Global retriever instance
_hybrid_retriever = None


def get_hybrid_retriever() -> HybridRetriever:
    """Get or create the hybrid retriever singleton."""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever


@router.post("/", response_model=IngestResponse)
@router.post("", response_model=IngestResponse)
async def ingest_documents(
    files: List[UploadFile] = File(...),
    api_key: str = Depends(require_api_key)
) -> IngestResponse:
    """Ingest documents into the RAG system."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per upload")
    
    processor = DocumentProcessor()
    retriever = get_hybrid_retriever()
    
    ingested = []
    skipped = []
    errors = []
    
    # Create temp directory for uploads in /tmp
    temp_dir = Path("/tmp/rag_uploads")
    temp_dir.mkdir(exist_ok=True)
    
    try:
        for file in files:
            try:
                # Validate file size (max 10MB per file)
                if file.size and file.size > 10 * 1024 * 1024:
                    errors.append(f"File {file.filename} too large (max 10MB)")
                    continue
                
                # Validate filename
                if not file.filename or file.filename.strip() == "":
                    errors.append("Invalid filename")
                    continue
                
                # Read file content
                content = await file.read()
                
                # Check actual file size
                if len(content) > 10 * 1024 * 1024:
                    errors.append(f"File {file.filename} too large (max 10MB)")
                    continue
                
                # Skip empty files
                if len(content) == 0:
                    skipped.append({
                        "filename": file.filename,
                        "reason": "Empty file"
                    })
                    continue
                
                # Save uploaded file
                file_path = temp_dir / file.filename
                with open(file_path, "wb") as f:
                    f.write(content)
                
                # Process file into chunks
                chunks = processor.process_file(file_path)
                
                if chunks:
                    # Add to retriever asynchronously for better performance
                    await retriever.add_documents(chunks)
                    
                    ingested.append({
                        "filename": file.filename,
                        "doc_id": chunks[0].doc_id,
                        "chunks": len(chunks),
                        "file_size": len(content),
                        "source": str(file_path)
                    })
                    
                    # Generate intelligence in background (non-blocking)
                    try:
                        intelligence_service = get_document_intelligence_service()
                        asyncio.create_task(
                            intelligence_service.analyze_document(chunks)
                        )
                    except Exception:
                        pass  # Don't fail the upload if intelligence generation fails
                else:
                    skipped.append({
                        "filename": file.filename,
                        "reason": "No content extracted"
                    })
                
                # Clean up temp file
                file_path.unlink()
                
            except Exception as e:
                errors.append(f"Failed to process {file.filename}: {str(e)}")
                # Clean up temp file if it exists
                temp_path = temp_dir / file.filename
                if temp_path.exists():
                    temp_path.unlink()
    
    finally:
        # Clean up temp directory
        if temp_dir.exists():
            for file_path in temp_dir.iterdir():
                file_path.unlink()
            temp_dir.rmdir()
    
    return IngestResponse(
        ingested=ingested,
        skipped=skipped,
        errors=errors
    ) 