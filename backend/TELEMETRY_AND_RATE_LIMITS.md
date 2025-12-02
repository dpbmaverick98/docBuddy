# Telemetry Errors & Rate Limits Explained

## 1. Telemetry Errors (Harmless)

**What you're seeing:**
```
Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given
```

**What it means:**
- ChromaDB tries to send anonymous usage data
- There's a bug in ChromaDB's telemetry code (version 0.4.18)
- The errors are **harmless** - they don't affect functionality
- ChromaDB still works perfectly, it just can't send telemetry

**Why it happens:**
- ChromaDB 0.4.18 has a telemetry bug
- We've disabled telemetry via environment variables
- But ChromaDB still tries to send it and fails

**Fix applied:**
- Suppressed warnings using Python's `warnings` module
- Set logging level to ERROR for telemetry
- These messages should now be hidden

**Note:** These errors don't affect indexing or search functionality at all.

---

## 2. Rate Limit (Cohere API)

**What you're seeing:**
```
⚠️  Rate limit hit. Waiting 60s before retry 2/3...
```

**What it means:**
- Cohere trial accounts have a **100,000 tokens per minute** limit
- You're indexing 1624 chunks × ~2500 chars = ~4M characters
- That's roughly **1M tokens** (rough estimate: 4 chars = 1 token)
- So you're hitting the rate limit

**Why it happens:**
- Trial accounts have lower limits
- We're processing a lot of content (1624 chunks)
- Even with 50-chunk batches, we're sending many requests

**What's happening:**
1. Batch 15 tries to embed 50 chunks
2. Cohere says "rate limit exceeded"
3. Script waits 60 seconds (exponential backoff)
4. Retries the same batch
5. If it fails 3 times, stops with an error

**Solutions:**

### Option 1: Wait and Resume (Current)
- The script will retry automatically
- If it fails after 3 retries, wait 5-10 minutes
- Re-run: `python indexer/index_docs.py --base-url https://docs.privy.io`
- It will resume from where it left off (already indexed chunks are saved)

### Option 2: Smaller Batches
- Edit `vector_store.py` line 106:
  ```python
  vector_store.add_chunks(all_chunks, batch_size=25, delay_between_batches=3.0)
  ```
- Smaller batches = fewer tokens per request
- Longer delays = more time between requests

### Option 3: Upgrade Cohere Plan
- Paid plans have higher rate limits
- $29/month plan: 1M tokens/minute
- $299/month plan: 10M tokens/minute

### Option 4: Index in Stages
- Index fewer docs at a time
- Process 200-300 docs per run
- Spread indexing over multiple sessions

---

## Current Status

Your indexing is working! The rate limit retry is doing its job:
- ✅ 14 batches completed (700 chunks indexed)
- ⚠️  Batch 15 hit rate limit → waiting 60s → will retry
- 📊 Progress: ~43% complete (700/1624 chunks)

**Recommendation:** Let it finish. The retry logic will handle rate limits. If it fails after 3 retries, wait 5 minutes and re-run - it will resume safely.

