"""
Evaluation datasets and test cases for RAG system benchmarking.
"""
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class EvalExample:
    """Single evaluation example."""
    question: str
    expected_answer: str
    context_docs: List[str]
    category: str
    difficulty: str
    
    
class EvalDatasets:
    """Collection of evaluation datasets for RAG benchmarking."""
    
    @staticmethod
    def get_qa_dataset() -> List[EvalExample]:
        """Get question-answering evaluation dataset."""
        return [
            EvalExample(
                question="What vector stores are supported by the system?",
                expected_answer="The system supports Qdrant, Chroma, and Pinecone vector stores.",
                context_docs=["FAQ document with vector store information"],
                category="factual",
                difficulty="easy"
            ),
            EvalExample(
                question="How do I authenticate with the API?",
                expected_answer="To authenticate, include the header `x-api-key` with your configured API key.",
                context_docs=["FAQ document with authentication instructions"],
                category="procedural", 
                difficulty="easy"
            ),
            EvalExample(
                question="What security measures does the company require?",
                expected_answer="The company requires multi-factor authentication (MFA) on all accounts and adherence to data privacy standards.",
                context_docs=["Company policies document"],
                category="policy",
                difficulty="medium"
            ),
            EvalExample(
                question="What is the leave policy for vacation and sick days?",
                expected_answer="Paid time off includes vacation, sick leave, and parental leave according to the company handbook.",
                context_docs=["Company policies document"],
                category="policy",
                difficulty="medium"
            ),
            EvalExample(
                question="What happens if there's a security incident?",
                expected_answer="Employees must report security incidents within 24 hours according to company policy.",
                context_docs=["Company policies document"],
                category="policy",
                difficulty="hard"
            ),
            EvalExample(
                question="Can I use Elasticsearch as a vector store?",
                expected_answer="No, Elasticsearch is not listed as a supported vector store. The system supports Qdrant, Chroma, and Pinecone only.",
                context_docs=["FAQ document"],
                category="factual",
                difficulty="medium"
            ),
            EvalExample(
                question="What is the company's data retention policy?",
                expected_answer="I don't have enough information to answer this question based on the available documents.",
                context_docs=[],
                category="unknown",
                difficulty="hard"
            ),
            EvalExample(
                question="How many vector stores can I use simultaneously?",
                expected_answer="Based on the available information, the system configuration allows selecting one vector store at a time (Qdrant, Chroma, or Pinecone).",
                context_docs=["FAQ document", "Configuration documentation"],
                category="technical",
                difficulty="hard"
            ),
            EvalExample(
                question="What programming languages are supported for API clients?",
                expected_answer="I don't have enough information to answer this question based on the available documents.",
                context_docs=[],
                category="unknown",
                difficulty="medium"
            ),
            EvalExample(
                question="Does the system support real-time streaming responses?",
                expected_answer="Yes, the system supports streaming responses through Server-Sent Events for real-time communication.",
                context_docs=["Technical documentation"],
                category="technical",
                difficulty="medium"
            )
        ]
    
    @staticmethod
    def get_hallucination_dataset() -> List[EvalExample]:
        """Get dataset specifically designed to test hallucination resistance."""
        return [
            EvalExample(
                question="What is the company's remote work policy?",
                expected_answer="I don't have enough information to answer this question based on the available documents.",
                context_docs=[],
                category="hallucination_test",
                difficulty="medium"
            ),
            EvalExample(
                question="How many employees work at the company?",
                expected_answer="I don't have enough information to answer this question based on the available documents.",
                context_docs=[],
                category="hallucination_test",
                difficulty="easy"
            ),
            EvalExample(
                question="What is the company's annual revenue?",
                expected_answer="I don't have enough information to answer this question based on the available documents.",
                context_docs=[],
                category="hallucination_test",
                difficulty="easy"
            ),
            EvalExample(
                question="Does the system support MongoDB as a vector store?",
                expected_answer="No, MongoDB is not listed as a supported vector store. The system supports Qdrant, Chroma, and Pinecone only.",
                context_docs=["FAQ document"],
                category="hallucination_test",
                difficulty="medium"
            ),
            EvalExample(
                question="What is the maximum file size for document uploads?",
                expected_answer="I don't have enough information to answer this question based on the available documents.",
                context_docs=[],
                category="hallucination_test",
                difficulty="medium"
            )
        ]
    
    @staticmethod
    def get_reasoning_dataset() -> List[EvalExample]:
        """Get dataset that tests reasoning and inference capabilities."""
        return [
            EvalExample(
                question="If I need to store my documents securely and ensure user authentication, what should I implement?",
                expected_answer="Based on company policies, you should implement multi-factor authentication (MFA) on all accounts, adhere to data privacy standards, and ensure security incidents are reported within 24 hours.",
                context_docs=["Company policies document", "FAQ document"],
                category="reasoning",
                difficulty="hard"
            ),
            EvalExample(
                question="Which vector store would be best for a production deployment requiring high availability?",
                expected_answer="The system supports Qdrant, Chroma, and Pinecone. However, I don't have specific information about their availability characteristics to make a recommendation.",
                context_docs=["FAQ document"],
                category="reasoning",
                difficulty="hard"
            ),
            EvalExample(
                question="What steps should I take if I suspect a security breach?",
                expected_answer="According to company policy, you must report security incidents within 24 hours and follow the established data privacy standards.",
                context_docs=["Company policies document"],
                category="reasoning",
                difficulty="medium"
            )
        ]
    
    @staticmethod
    def get_all_datasets() -> Dict[str, List[EvalExample]]:
        """Get all evaluation datasets."""
        return {
            "qa": EvalDatasets.get_qa_dataset(),
            "hallucination": EvalDatasets.get_hallucination_dataset(),
            "reasoning": EvalDatasets.get_reasoning_dataset()
        }