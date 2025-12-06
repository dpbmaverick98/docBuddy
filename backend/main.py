"""
FastAPI main application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.journey import router as journey_router
from api.doc_summary import router as doc_summary_router
from api.step_qa import router as step_qa_router
from api.projects import router as projects_router

app = FastAPI(
    title="Docs Journey Builder API",
    description="Generate step-by-step journeys through documentation",
    version="0.1.0"
)

# CORS middleware (for frontend later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(journey_router)
app.include_router(doc_summary_router)
app.include_router(step_qa_router)
app.include_router(projects_router)


@app.get("/")
async def root():
    return {
        "message": "Docs Journey Builder API",
        "status": "running",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}

