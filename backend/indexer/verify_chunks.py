"""
Manual verification script to check chunk quality
"""
import sys
import os
from pathlib import Path

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "1"

sys.path.insert(0, str(Path(__file__).parent.parent))

from indexer.vector_store import VectorStore
from dotenv import load_dotenv

load_dotenv()


def verify_chunks(collection_name: str = "docs", sample_size: int = 10):
    """
    Verify chunk quality by sampling chunks and showing their content
    
    Args:
        collection_name: ChromaDB collection name
        sample_size: Number of chunks to sample
    """
    print("🔍 Verifying chunk quality...")
    print("=" * 60)
    
    try:
        vector_store = VectorStore(collection_name=collection_name)
        stats = vector_store.get_stats()
        
        print(f"\n📊 Collection Stats:")
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Total chunks: {stats['total_chunks']}")
        
        if stats['total_chunks'] == 0:
            print("\n❌ No chunks found in collection")
            return
        
        # Get sample chunks
        print(f"\n📋 Sampling {min(sample_size, stats['total_chunks'])} chunks...")
        print("=" * 60)
        
        # Query with a generic search to get some results
        results = vector_store.search("documentation", n_results=sample_size)
        
        if not results:
            print("❌ No results returned from search")
            return
        
        for i, result in enumerate(results, 1):
            print(f"\n{'─' * 60}")
            print(f"Chunk {i}/{len(results)}")
            print(f"{'─' * 60}")
            print(f"📄 Doc: {result['metadata'].get('doc_title', 'Unknown')}")
            print(f"📍 Path: {result['metadata'].get('doc_path', 'Unknown')}")
            print(f"📑 Heading: {result['metadata'].get('heading', 'Unknown')}")
            print(f"🔗 URL: {result['metadata'].get('doc_url', 'N/A')}")
            if result.get('distance'):
                print(f"📊 Distance: {result['distance']:.4f}")
            
            print(f"\n📝 Content preview (first 500 chars):")
            content = result['content']
            preview = content[:500] + "..." if len(content) > 500 else content
            print(f"{preview}")
            
            print(f"\n📏 Content length: {len(content)} chars")
        
        print(f"\n{'─' * 60}")
        print("\n✅ Verification complete!")
        print("\n💡 Check:")
        print("   - Are headings meaningful?")
        print("   - Is content complete (not cut off)?")
        print("   - Are chunks appropriately sized?")
        print("   - Is metadata correct?")
        
        # Test search
        print(f"\n🔎 Testing search functionality...")
        test_queries = [
            "authentication",
            "getting started",
            "API reference"
        ]
        
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            search_results = vector_store.search(query, n_results=3)
            if search_results:
                print(f"   Found {len(search_results)} results:")
                for r in search_results:
                    print(f"     - {r['metadata'].get('heading', 'Unknown')} "
                          f"({r['metadata'].get('doc_title', 'Unknown')})")
            else:
                print(f"   No results found")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify chunk quality")
    parser.add_argument(
        "--collection",
        type=str,
        default="docs",
        help="ChromaDB collection name (default: docs)"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=10,
        help="Number of chunks to sample (default: 10)"
    )
    
    args = parser.parse_args()
    
    verify_chunks(args.collection, args.sample_size)

