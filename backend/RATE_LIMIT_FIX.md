# Rate Limit Fix

## Problem
Cohere trial accounts have a rate limit of 100,000 tokens per minute. With 1624 chunks averaging ~2500 chars each, we're hitting this limit.

## Solution Applied

1. **Reduced batch size**: 100 → 50 chunks per batch
2. **Added delays**: 2 second delay between batches
3. **Retry logic**: Exponential backoff (60s, 120s, 240s) for rate limit errors
4. **Better error handling**: Clear messages when rate limits are hit

## Usage

The indexer now automatically handles rate limits:

```bash
python indexer/index_docs.py --base-url https://docs.privy.io
```

If you hit a rate limit:
- The script will wait and retry automatically
- If it fails after 3 retries, wait a few minutes and re-run
- The script checks for existing chunks, so you can resume safely

## Alternative: Upgrade Cohere Plan

For production use, consider upgrading to a paid Cohere plan with higher rate limits.

