"""
Step Q&A API endpoint
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.step_qa import StepQAService

router = APIRouter(prefix="/api/journey", tags=["journey"])


class StepQARequest(BaseModel):
    step_title: str
    step_description: str
    context: str
    question: str
    model: Optional[str] = "claude"


class StepQAResponse(BaseModel):
    answer: str


@router.post("/ask-step", response_model=StepQAResponse)
async def ask_step_question(request: StepQARequest):
    """
    Answer questions about a specific step
    
    Example:
        POST /api/journey/ask-step
        {
            "step_title": "Set up Google authentication",
            "step_description": "Configure Google OAuth...",
            "context": "Summary of relevant docs...",
            "question": "How do I configure this?"
        }
    """
    try:
        qa_service = StepQAService(model_name=request.model)
        answer = qa_service.answer_question(
            step_title=request.step_title,
            step_description=request.step_description,
            context=request.context,
            question=request.question
        )
        
        return StepQAResponse(answer=answer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")

