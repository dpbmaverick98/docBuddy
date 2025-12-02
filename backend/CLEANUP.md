# Collection Cleanup & Telemetry Fix

## Changes Made

### 1. Collection Cleanup
- Added `clear_collection()` method to VectorStore
- Indexer now prompts: Clear, Add, or Skip when existing chunks found
- Added `--clear` CLI flag for non-interactive clearing

### 2. Telemetry Errors Fixed
- Disabled ChromaDB telemetry via environment variables
- Set before ChromaDB imports to prevent errors
- Applied to all scripts (index_docs.py, verify_chunks.py, vector_store.py)

## Usage

### Clear and Re-index
```bash
# Option 1: Use --clear flag
python indexer/index_docs.py --base-url https://docs.privy.io --clear

# Option 2: Interactive prompt (when existing chunks found)
python indexer/index_docs.py --base-url https://docs.privy.io
# Then choose 'c' to clear
```

### Manual Collection Clear
```python
from indexer.vector_store import VectorStore
store = VectorStore(collection_name="docs")
store.clear_collection()
```

## Telemetry Fix

The telemetry errors were caused by ChromaDB trying to send telemetry events with incorrect function signatures. We now disable telemetry completely by setting:
- `ANONYMIZED_TELEMETRY=False`
- `CHROMA_TELEMETRY_DISABLED=1`

These are set before any ChromaDB imports to ensure they take effect.

