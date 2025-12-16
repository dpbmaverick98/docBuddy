"""
FastAPI main application
"""
try:
    from dotenv import load_dotenv
    import os
    # Load .env from backend directory explicitly
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path=dotenv_path)
    print(f"✅ Environment variables loaded from {dotenv_path}")
    # Debug: check ChromaDB path
    import os
    chroma_path = os.getenv('CHROMA_DB_PATH', 'NOT_SET')
    print(f"🗄️  CHROMA_DB_PATH: {chroma_path}")
    print(f"📁 Current working directory: {os.getcwd()}")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"🚨 Global exception handler: {type(exc).__name__}: {str(exc)}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

