"""
Simplified FastAPI main for debugging
"""
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
    print("✅ Environment variables loaded from .env file")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

from fastapi import FastAPI

app = FastAPI(
    title="Docs Journey Builder API",
    description="Generate step-by-step journeys through documentation",
    version="0.1.0"
)

# Import routers
from api.projects import router as projects_router
app.include_router(projects_router, prefix="/api")

print("✅ Projects router included")

# Now try importing journey router
try:
    from api.journey import router as journey_router
    app.include_router(journey_router, prefix="/api")
    print("✅ Journey router included")
except Exception as e:
    print(f"❌ Error with journey router: {e}")
    import traceback
    traceback.print_exc()

@app.get("/")
def root():
    return {"message": "Docs Journey Builder API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

print("✅ App setup complete")

if __name__ == "__main__":
    import uvicorn
    print("Starting uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)