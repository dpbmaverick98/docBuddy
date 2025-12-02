# Docs Journey Builder

A documentation onboarding system that creates step-by-step journeys through docs based on user goals.

## Architecture

- **Backend**: Python (FastAPI) - indexing, journey generation, Q&A
- **Frontend**: Next.js + React - chat interface, canvas visualization
- **Vector DB**: ChromaDB (self-hosted)
- **Embeddings**: Cohere embed-multilingual-v3.0
- **LLM**: Claude 3.5 Sonnet (planning) + Gemini Flash (Q&A)

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Copy env.example to .env and add your API keys
cp env.example .env
# Edit .env and add: COHERE_API_KEY, ANTHROPIC_API_KEY, GOOGLE_AI_API_KEY
```

### Index Docs from llms.txt

```bash
python backend/indexer/index_docs.py --base-url https://docs.privy.io
```

### Verify Chunks

```bash
python backend/indexer/verify_chunks.py
```

### Run Backend API

```bash
cd backend
uvicorn main:app --reload
```

### Run Frontend

```bash
cd frontend
bun install
bun run dev
```

Visit http://localhost:3000

## Project Structure

```
backend/
  indexer/          # llms.txt parser, doc fetcher, chunker
  api/              # FastAPI endpoints
  services/         # Journey generation, Q&A
  db/               # ChromaDB setup

frontend/
  app/              # Next.js app directory
  components/       # React components
  lib/              # Utilities
```

## Development Plan

**Week 1: Core**
- Day 1: llms.txt indexer → ChromaDB ✅
- Day 2: /generate-journey endpoint ✅
- Day 3: Simple vertical timeline UI ✅
- Day 4: Click step → show doc summary ✅
- Day 5: Add Redis for state
- Day 6: /ask endpoint with step context
- Day 7: Deploy backend

## API Endpoints

### Generate Journey
```bash
POST /api/journey/generate
Content-Type: application/json

{
  "query": "I want to set up authentication",
  "max_steps": 5
}
```

