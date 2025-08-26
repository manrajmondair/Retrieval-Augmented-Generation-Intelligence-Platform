from abc import ABC, abstractmethod
from typing import List
from app.rag.schemas import DocumentChunk, RetrievalResult


class BaseRetriever(ABC):
    """Base interface for all retrievers."""
    
    @abstractmethod
    async def add_documents(self, chunks: List[DocumentChunk]) -> None:
        """Add documents to the retriever index."""
        pass
    
    @abstractmethod
    async def retrieve(self, query: str, top_k: int) -> List[RetrievalResult]:
        """Retrieve documents for a query."""
        pass
    
    @abstractmethod
    async def delete_documents(self, doc_ids: List[str]) -> None:
        """Delete documents from the retriever index."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all documents from the retriever index."""
        pass
    
    @abstractmethod
    async def is_ready(self) -> bool:
        """Check if the retriever is ready to serve requests."""
        pass 