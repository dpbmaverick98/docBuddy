# Quick Start Guide

## Day 1: Index Docs from llms.txt

### 1. Setup Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy `.env.example` to `.env` and add your keys:

```bash
cp .env.example .env
```

Required keys:
- `COHERE_API_KEY` - Get from https://cohere.com
- `ANTHROPIC_API_KEY` - Get from https://anthropic.com (for Day 2)
- `GOOGLE_AI_API_KEY` - Get from https://ai.google.dev (for Day 6)

### 3. Index Privy Docs

```bash
python indexer/index_docs.py --base-url https://docs.privy.io
```

This will:
1. Fetch `llms.txt` from Privy docs
2. Parse all doc links
3. Fetch all markdown content
4. Chunk by headings
5. Generate embeddings with Cohere
6. Store in ChromaDB

**Expected output:**
- ~200+ doc pages fetched
- ~500-1000 chunks created
- Stored in `./chroma_db/`

### 4. Verify Chunk Quality (Day 1.5 Checkpoint)

```bash
python indexer/verify_chunks.py
```

**What to check:**
- ✅ Chunks have meaningful headings
- ✅ Content is complete (not cut off mid-sentence)
- ✅ Chunk sizes are reasonable (200-2000 chars)
- ✅ Metadata is correct (doc paths, URLs)
- ✅ Search returns relevant results

**If chunks look bad:**
- Adjust `min_chunk_size` in `chunker.py`
- Check if HTML extraction is working (might need site-specific logic)
- Verify markdown parsing is correct

### 5. Test Search Manually

```python
# Quick test script
from indexer.vector_store import VectorStore
from dotenv import load_dotenv
load_dotenv()

store = VectorStore()
results = store.search("authentication", n_results=5)
for r in results:
    print(f"{r['metadata']['heading']}: {r['content'][:200]}...")
```

## Day 2: Generate Journey Endpoint

(Coming next - will add `/generate-journey` endpoint)

## Troubleshooting

### "COHERE_API_KEY not set"
- Make sure `.env` file exists in `backend/` directory
- Check that `python-dotenv` is installed
- Verify key is correct

### "Failed to fetch llms.txt"
- Check internet connection
- Verify URL is correct (should end with `/llms.txt`)
- Some sites might not have `llms.txt` (check manually)

### "No chunks found"
- Check if docs were fetched successfully
- Verify markdown parsing is working
- Check ChromaDB path (`./chroma_db/`)

### ChromaDB errors
- Delete `chroma_db/` folder and re-index
- Check disk space
- Verify ChromaDB version compatibility

