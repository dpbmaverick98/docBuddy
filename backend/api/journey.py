"""
Journey generation API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from services.journey_generator import JourneyGenerator

router = APIRouter(prefix="/api/journey", tags=["journey"])


class JourneyRequest(BaseModel):
    query: str
    max_steps: Optional[int] = 10
    project: str = "privy"  # Default to your current project


class JourneyResponse(BaseModel):
    goal: str
    steps: List[dict]
    total_steps: int
    estimated_time: str


@router.post("/generate", response_model=JourneyResponse)
async def generate_journey(request: JourneyRequest):
    """
    Generate a step-by-step journey from user query

    Example:
        POST /api/journey/generate
        {
            "query": "I want to set up authentication",
            "max_steps": 5,
            "project": "privy"
        }
    """
    try:
        # Convert project name to collection name
        collection_name = request.project.lower().replace(' ', '_')

        # Use optimized defaults: RAG enabled, temperature 0.7 for balanced creativity
        generator = JourneyGenerator(
            collection_name=collection_name,
            use_rag=True,
            temperature=0.7
        )
        journey = generator.generate_journey(
            user_query=request.query,
            max_steps=request.max_steps
        )
        
        if 'error' in journey:
            raise HTTPException(status_code=400, detail=journey['error'])
        
        return journey
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating journey: {str(e)}")

