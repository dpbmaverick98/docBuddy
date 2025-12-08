"""
Documentation summary API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from services.doc_summarizer import DocSummarizer

router = APIRouter(prefix="/api/docs", tags=["docs"])


class SummaryRequest(BaseModel):
    doc_paths: List[str]
    max_length: Optional[int] = 300
    step_title: Optional[str] = None
    step_description: Optional[str] = None
    step_number: Optional[int] = None
    enhanced_context: Optional[Dict] = None


class SummaryResponse(BaseModel):
    summaries: List[dict]


@router.post("/summaries", response_model=SummaryResponse)
async def get_doc_summaries(request: SummaryRequest):
    """
    Get summaries for multiple documentation paths
    
    Example:
        POST /api/docs/summaries
        {
            "doc_paths": ["/wallets/gas-and-asset-management/gas/overview.md"],
            "max_length": 300
        }
    """
    try:
        summarizer = DocSummarizer()
        summaries = summarizer.get_summaries(
            doc_paths=request.doc_paths,
            max_length=request.max_length,
            step_title=request.step_title,
            step_description=request.step_description,
            step_number=request.step_number,
            enhanced_context=request.enhanced_context
        )
        
        return SummaryResponse(summaries=summaries)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summaries: {str(e)}")

