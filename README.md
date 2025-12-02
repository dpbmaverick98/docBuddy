# Docs Journey Builder

A documentation onboarding system that creates step-by-step journeys through docs based on user goals.

## Architecture

- **Backend**: Python (FastAPI) - indexing, journey generation, Q&A
- **Frontend**: Next.js + React - chat interface, timeline visualization
- **Vector DB**: ChromaDB (self-hosted)
- **RAG Framework**: LlamaIndex (context optimization, post-processing)
- **Embeddings**: Cohere embed-multilingual-v3.0
- **LLM**: Claude Sonnet 4.5 (journey generation, summaries, Q&A)
- **Features**: Intent extraction, prompt chaining, temperature control

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

### Get Doc Summaries
```bash
POST /api/docs/summaries
Content-Type: application/json

{
  "doc_paths": ["/wallets/gas-and-asset-management/gas/overview.md"],
  "max_length": 3000
}
```

### Ask Step Question
```bash
POST /api/journey/ask-step
Content-Type: application/json

{
  "step_title": "Set up authentication",
  "step_description": "Configure Google OAuth...",
  "context": "Summary of relevant docs...",
  "question": "How do I configure this?"
}
```

