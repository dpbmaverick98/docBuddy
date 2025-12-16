"""
Journey generation API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from services.journey_generator import JourneyGenerator

router = APIRouter(prefix="/api/journey", tags=["journey"])


class JourneyRequest(BaseModel):
    query: str
    max_steps: Optional[int] = 10
    project: str = "polymarket"  # Default to Polymarket
    model: Optional[str] = "claude"  # Add model parameter


class JourneyResponse(BaseModel):
    goal: str
    intent: Optional[Dict[str, Any]] = None
    steps: List[dict]
    total_steps: int
    estimated_time: str
    enhanced_context: Optional[Dict[str, Any]] = None


@router.post("/generate", response_model=JourneyResponse)
async def generate_journey(request: JourneyRequest):
    """
    Generate a step-by-step journey from user query

    Example:
        POST /api/journey/generate
        {
            "query": "I want to set up authentication",
            "max_steps": 5,
            "project": "privy",
            "model": "hf-k2"
        }
    """
    try:
        # Convert project name to collection name
        collection_name = request.project.lower().replace(' ', '_')

        # Use optimized defaults: RAG enabled, temperature 0.7 for balanced creativity
        generator = JourneyGenerator(
            collection_name=collection_name,
            use_rag=True,
            temperature=0.7,
            model_name=request.model
        )
        journey = generator.generate_journey(
            user_query=request.query,
            max_steps=request.max_steps
        )
        
        if 'error' in journey:
            raise HTTPException(status_code=400, detail=journey['error'])

        # Debug: Check journey structure before returning
        print(f"🔍 Returning journey with {len(journey.get('steps', []))} steps")
        print(f"🔍 Journey keys: {list(journey.keys())}")
        print(f"🔍 Enhanced context keys: {list(journey.get('enhanced_context', {}).keys())}")

        # Test JSON serialization
        import json
        try:
            json_str = json.dumps(journey, default=str)
            print(f"✅ JSON serialization successful, length: {len(json_str)} chars")
            print(f"📊 Response size: {len(json_str)/1024:.1f} KB")
        except Exception as json_error:
            print(f"❌ JSON serialization failed: {json_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"JSON serialization error: {str(json_error)}")

        print("🏁 About to return journey response")
        return journey
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating journey: {str(e)}")

