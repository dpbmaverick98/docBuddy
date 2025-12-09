"""
Documentation summary API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from services.doc_summarizer import DocSummarizer
import time
import uuid

router = APIRouter(prefix="/api/docs", tags=["docs"])


class SummaryRequest(BaseModel):
    doc_paths: List[str]
    max_length: Optional[int] = 300
    step_title: Optional[str] = None
    step_description: Optional[str] = None
    step_number: Optional[int] = None
    enhanced_context: Optional[Dict] = None
    model: Optional[str] = "claude"


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
            "max_length": 300,
            "model": "hf-k2-openai"
        }
    """
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    try:
        print(f"📥 [Request {request_id}] Received summary request for {len(request.doc_paths)} docs, model: {request.model}")
        print(f"📥 [Request {request_id}] Step: {request.step_title}")
        
        summarizer = DocSummarizer(model_name=request.model)
        summaries = summarizer.get_summaries(
            doc_paths=request.doc_paths,
            max_length=request.max_length,
            step_title=request.step_title,
            step_description=request.step_description,
            step_number=request.step_number,
            enhanced_context=request.enhanced_context
        )
        
        elapsed = time.time() - start_time
        print(f"✅ [Request {request_id}] Generated {len(summaries)} summaries in {elapsed:.2f}s")
        
        return SummaryResponse(summaries=summaries)
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ [Request {request_id}] Error after {elapsed:.2f}s: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating summaries: {str(e)}")

