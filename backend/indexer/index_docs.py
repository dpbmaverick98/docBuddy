"""
Main script to index docs from llms.txt
"""
import asyncio
import sys
import os
from pathlib import Path

# Disable ChromaDB telemetry before any imports
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "1"

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from indexer.llms_parser import fetch_llms_txt, parse_llms_txt
from indexer.doc_fetcher import fetch_all_docs
from indexer.chunker import split_by_headings, get_chunk_stats
from indexer.vector_store import VectorStore
from services.x402_client import X402Client
from dotenv import load_dotenv

# Load .env from backend directory regardless of working directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))


async def index_docs_from_llms_txt(base_url: str, project_name: str = None):
    """
    Complete pipeline: llms.txt → fetch docs → chunk → embed → store

    Args:
        base_url: Base URL of docs site (e.g., https://docs.privy.io)
        project_name: Project identifier for collection naming
    """
    # Generate collection name from project
    collection_name = project_name.lower().replace(' ', '_') if project_name else "docs"
    print(f"🚀 Starting indexing for {base_url} (project: {project_name})")
    print("=" * 60)

    # Initialize x402 client for paid embeddings (only if payments enabled)
    use_x402 = os.getenv('USE_X402_PAYMENTS', 'false').lower() == 'true'
    x402_client = X402Client() if use_x402 else None
    
    # Step 1: Parse llms.txt
    print("\n📄 Step 1: Fetching llms.txt...")
    try:
        llms_content = await fetch_llms_txt(base_url)
        print(f"✅ Fetched llms.txt ({len(llms_content)} chars)")
    except Exception as e:
        print(f"❌ Failed to fetch llms.txt: {e}")
        return
    
    # Step 2: Parse links
    print("\n🔗 Step 2: Parsing doc links...")
    doc_links = parse_llms_txt(llms_content, base_url)
    print(f"✅ Found {len(doc_links)} documentation pages")
    
    if len(doc_links) == 0:
        print("❌ No doc links found in llms.txt")
        return
    
    # Show first few links
    print("\n📋 Sample links:")
    for link in doc_links[:5]:
        print(f"  - {link['title']}: {link['url']}")
    if len(doc_links) > 5:
        print(f"  ... and {len(doc_links) - 5} more")
    
    # Step 3: Fetch all docs
    print(f"\n📥 Step 3: Fetching {len(doc_links)} docs...")
    docs = await fetch_all_docs(doc_links, max_concurrent=20)
    print(f"✅ Successfully fetched {len(docs)} docs")
    
    if len(docs) == 0:
        print("❌ No docs fetched successfully")
        return
    
    # Step 4: Chunk each doc
    print(f"\n✂️  Step 4: Chunking documents...")
    all_chunks = []
    for doc in docs:
        chunks = split_by_headings(doc['content'], doc['path'])
        for chunk in chunks:
            chunk['doc_url'] = doc['url']
            chunk['doc_title'] = doc['title']
        all_chunks.extend(chunks)
    
    stats = get_chunk_stats(all_chunks)
    print(f"✅ Created {stats['total_chunks']} chunks")
    print(f"   Average size: {stats['avg_size']:.0f} chars")
    print(f"   Size range: {stats['min_size']} - {stats['max_size']} chars")
    
    # Step 5: Store in vector DB
    print(f"\n💾 Step 5: Storing in vector database...")
    try:
        vector_store = VectorStore(collection_name=collection_name, x402_client=x402_client)
        
        # Check if collection already has chunks
        existing_count = vector_store.get_stats()['total_chunks']
        if existing_count > 0:
            print(f"⚠️  Collection already has {existing_count} chunks")
            print("   Options:")
            print("   [c] Clear and re-index (recommended)")
            print("   [a] Add to existing")
            print("   [s] Skip")
            response = input("   Choose (c/a/s): ").lower().strip()
            
            if response == 'c':
                print("   Clearing existing chunks...")
                vector_store.clear_collection()
            elif response == 'a':
                print("   Adding to existing chunks...")
            else:
                print("   Skipping indexing")
                return
        
        # Use smaller batch size and delays to avoid rate limits
        vector_store.add_documents(all_chunks, batch_size=50, delay_between_batches=2.0)
        
        # Show final stats
        final_stats = vector_store.get_stats()
        print(f"\n📊 Final Statistics:")
        print(f"   Collection: {final_stats['collection_name']}")
        print(f"   Total chunks indexed: {final_stats['total_chunks']}")
        
    except Exception as e:
        print(f"❌ Error storing in vector DB: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("✅ Indexing complete!")
    print(f"\n💡 Next steps:")
    print(f"   1. Run: python backend/indexer/verify_chunks.py")
    print(f"   2. Check chunk quality manually")
    print(f"   3. Proceed to journey generation")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Index docs from llms.txt")
    parser.add_argument(
        "--base-url",
        type=str,
        required=True,
        help="Base URL of docs site (e.g., https://docs.privy.io)"
    )
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="Project name (e.g., 'privy', 'stripe', 'aws')"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing collection before indexing"
    )

    args = parser.parse_args()

    # If --clear flag is set, clear collection first
    if args.clear:
        from indexer.vector_store import VectorStore
        collection_name = args.project.lower().replace(' ', '_')
        store = VectorStore(collection_name=collection_name)
        store.clear_collection()
        print("✅ Collection cleared\n")

    asyncio.run(index_docs_from_llms_txt(args.base_url, args.project))

