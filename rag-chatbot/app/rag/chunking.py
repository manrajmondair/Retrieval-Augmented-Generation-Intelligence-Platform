import hashlib
import re
from pathlib import Path
from typing import List, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredFileLoader,
)
from langchain.schema import Document
from app.rag.schemas import DocumentChunk


class DocumentProcessor:
    """Process documents into chunks with metadata."""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from various file formats."""
        suffix = file_path.suffix.lower()
        
        try:
            if suffix == ".pdf":
                loader = PyPDFLoader(str(file_path))
            elif suffix == ".md":
                # Simple markdown file reading
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content
            else:
                loader = UnstructuredFileLoader(str(file_path))
            
            if suffix != ".md":
                documents = loader.load()
                return "\n\n".join(doc.page_content for doc in documents)
            else:
                return content
        except Exception as e:
            raise ValueError(f"Failed to extract text from {file_path}: {e}")
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        return text.strip()
    
    def generate_chunk_id(self, doc_id: str, chunk_index: int) -> str:
        """Generate a unique chunk ID."""
        return f"{doc_id}_chunk_{chunk_index:04d}"
    
    def generate_content_hash(self, content: str) -> str:
        """Generate a hash of the content for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def process_file(self, file_path: Path, doc_id: Optional[str] = None) -> List[DocumentChunk]:
        """Process a file into chunks."""
        if doc_id is None:
            doc_id = file_path.stem
        
        # Extract and clean text
        raw_text = self.extract_text(file_path)
        cleaned_text = self.clean_text(raw_text)
        
        # Split into chunks
        chunks = self.text_splitter.split_text(cleaned_text)
        
        # Convert to DocumentChunk objects
        document_chunks = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = self.generate_chunk_id(doc_id, i)
            content_hash = self.generate_content_hash(chunk_text)
            
            chunk = DocumentChunk(
                doc_id=doc_id,
                source=str(file_path),
                title=file_path.stem,
                chunk_id=chunk_id,
                chunk_index=i,
                content=chunk_text,
                content_hash=content_hash,
                metadata={
                    "file_size": file_path.stat().st_size,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk_text),
                }
            )
            document_chunks.append(chunk)
        
        return document_chunks 