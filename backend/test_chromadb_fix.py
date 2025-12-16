#!/usr/bin/env python3
"""
Test ChromaDB fix without requiring API keys
"""
import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Mock the Cohere API key to test ChromaDB fix
os.environ['COHERE_API_KEY'] = 'test_key'

try:
    print("Testing ChromaDB connection after fix...")
    from indexer.vector_store import VectorStore
    
    # This should work now without the schema error
    vs = VectorStore(collection_name='test_collection')
    
    print("✅ ChromaDB connection successful!")
    print(f"✅ Collection created/retrieved: {vs.collection_name}")
    print(f"✅ Collection stats: {vs.get_stats()}")
    
    # Test basic functionality
    print("\nTesting basic search (will fail due to fake API key, but that's expected)...")
    try:
        results = vs.search("test query", n_results=1)
        print(f"Search results: {results}")
    except Exception as e:
        print(f"Expected search error (fake API key): {type(e).__name__}")
    
    print("\n✅ ChromaDB fix successful - no more schema errors!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()