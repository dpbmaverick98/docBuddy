"""
Quick test script to verify indexer works
Run this before full indexing to catch issues early
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from indexer.llms_parser import fetch_llms_txt, parse_llms_txt
from indexer.doc_fetcher import fetch_all_docs
from indexer.chunker import split_by_headings, get_chunk_stats


async def test_llms_parsing():
    """Test llms.txt parsing"""
    print("🧪 Testing llms.txt parsing...")
    
    base_url = "https://docs.privy.io"
    content = await fetch_llms_txt(base_url)
    doc_links = parse_llms_txt(content, base_url)
    
    print(f"✅ Parsed {len(doc_links)} links")
    print(f"   Sample: {doc_links[0]['title']} -> {doc_links[0]['url']}")
    
    return doc_links


async def test_doc_fetching(doc_links):
    """Test fetching a few docs"""
    print("\n🧪 Testing doc fetching (first 3 docs)...")
    
    test_docs = doc_links[:3]
    fetched = await fetch_all_docs(test_docs, max_concurrent=3)
    
    print(f"✅ Fetched {len(fetched)}/{len(test_docs)} docs")
    
    if fetched:
        doc = fetched[0]
        print(f"   Sample doc: {doc['title']}")
        print(f"   Content length: {len(doc['content'])} chars")
        print(f"   Content preview: {doc['content'][:200]}...")
    
    return fetched


def test_chunking(docs):
    """Test chunking"""
    print("\n🧪 Testing chunking...")
    
    if not docs:
        print("❌ No docs to chunk")
        return
    
    doc = docs[0]
    chunks = split_by_headings(doc['content'], doc['path'])
    stats = get_chunk_stats(chunks)
    
    print(f"✅ Created {stats['total_chunks']} chunks")
    print(f"   Avg size: {stats['avg_size']:.0f} chars")
    print(f"   Size range: {stats['min_size']} - {stats['max_size']} chars")
    
    if chunks:
        print(f"\n   Sample chunk:")
        print(f"   Heading: {chunks[0]['heading']}")
        print(f"   Content: {chunks[0]['content'][:150]}...")
    
    return chunks


async def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Testing Indexer Components")
    print("=" * 60)
    
    try:
        # Test 1: Parse llms.txt
        doc_links = await test_llms_parsing()
        
        # Test 2: Fetch docs
        docs = await test_doc_fetching(doc_links)
        
        # Test 3: Chunking
        if docs:
            chunks = test_chunking(docs)
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("💡 Ready to run full indexing:")
        print("   python indexer/index_docs.py --base-url https://docs.privy.io")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

