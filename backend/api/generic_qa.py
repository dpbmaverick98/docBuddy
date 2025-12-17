"""
Generic Q&A API endpoint
Answers single questions using RAG pipeline with optional context
Returns answers similar to step details format
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from services.generic_qa import GenericQAService

router = APIRouter(prefix="/api/docsbuddy", tags=["docsbuddy"])


class QASource(BaseModel):
    doc_path: str
    doc_url: str
    doc_title: str
    heading: str
    content: str
    score: float


class QARequest(BaseModel):
    question: str
    project: str = "polymarket"
    context: Optional[str] = None
    model: str = "hf-k2-openai"  # Default to K2


class QAResponse(BaseModel):
    answer: str
    sources: List[QASource]
    confidence_score: float


@router.post("/ask", response_model=QAResponse)
async def ask_question(request: QARequest):
    """
    Answer a single question using RAG pipeline with optional context

    Example:
        POST /api/docsbuddy/ask
        {
            "question": "How do I implement authentication?",
            "project": "polymarket",
            "context": "Previous chat response or user journey...",
            "model": "hf-k2-openai"
        }
    """
    try:
        # Initialize service with requested model (defaults to K2)
        qa_service = GenericQAService(model_name=request.model)

        # Get answer from service
        result = qa_service.answer_question(
            question=request.question,
            project=request.project,
            context=request.context
        )

        # Convert sources to proper format
        sources = []
        for source_data in result["sources"]:
            source = QASource(
                doc_path=source_data["doc_path"],
                doc_url=source_data["doc_url"],
                doc_title=source_data["doc_title"],
                heading=source_data["heading"],
                content=source_data["content"],
                score=source_data["score"]
            )
            sources.append(source)

        return QAResponse(
            answer=result["answer"],
            sources=sources,
            confidence_score=result["confidence_score"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")