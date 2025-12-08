"""
Test script for Cohere ranking optimizations
Tests query expansion, reranking, and contextual compression
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.rag_engine import RAGEngine
from services.intent_extractor import IntentExtractor
from dotenv import load_dotenv

load_dotenv()


def test_query_expansion():
    """Test Cohere query expansion"""
    print("=" * 60)
    print("🧪 Testing Query Expansion")
    print("=" * 60)

    rag = RAGEngine(collection_name="docs")

    test_queries = [
        "authentication setup",
        "gas sponsorship",
        "wallet connection"
    ]

    for query in test_queries:
        print(f"\n📝 Original Query: '{query}'")
        try:
            expanded = rag.expand_query(query)
            print(f"   🔍 Expanded to {len(expanded)} queries:")
            for i, eq in enumerate(expanded, 1):
                print(f"      {i}. '{eq}'")
        except Exception as e:
            print(f"   ❌ Error: {e}")


def test_reranking():
    """Test Cohere reranking"""
    print("\n" + "=" * 60)
    print("🧪 Testing Cohere Reranking")
    print("=" * 60)

    rag = RAGEngine(collection_name="docs")

    query = "authentication setup"

    try:
        print(f"\n📝 Query: '{query}'")

        # Get results with reranking
        results = rag.query(query, top_k=5, use_cohere_optimizations=True)

        print(f"   📊 Retrieved {len(results)} results:")
        for i, result in enumerate(results, 1):
            score = result.get('relevance_score', result.get('score', 0))
            title = result.get('doc_title', 'Unknown')
            print(".3f")

    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_contextual_compression():
    """Test contextual compression"""
    print("\n" + "=" * 60)
    print("🧪 Testing Contextual Compression")
    print("=" * 60)

    rag = RAGEngine(collection_name="docs")

    query = "authentication setup"

    try:
        print(f"\n📝 Query: '{query}'")

        # Get some documents first
        results = rag.query(query, top_k=3, use_cohere_optimizations=False)

        if results:
            docs = [r.get('content', '') for r in results]
            print(f"   📄 Got {len(docs)} documents")

            # Test compression
            compressed = rag.compress_context(query, docs)

            print("   🗜️  Compression results:")
            for i, (orig, comp) in enumerate(zip(docs, compressed), 1):
                orig_len = len(orig)
                comp_len = len(comp)
                ratio = comp_len / orig_len if orig_len > 0 else 0
                print(".1f")

    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_full_pipeline():
    """Test the complete pipeline with intent + optimizations"""
    print("\n" + "=" * 60)
    print("🧪 Testing Full Pipeline (Intent + Cohere Optimizations)")
    print("=" * 60)

    try:
        # Extract intent
        intent_extractor = IntentExtractor()
        query = "I want to set up authentication with Google in React"

        print(f"\n📝 Query: '{query}'")

        intent = intent_extractor.extract_intent(query)
        print("   🎯 Intent extracted:")
        print(f"      Goal: {intent.get('goal')}")
        print(f"      Complexity: {intent.get('complexity')}")
        print(f"      Platform: {intent.get('platform')}")
        print(f"      Keywords: {intent.get('keywords', [])[:3]}")

        # Test RAG with intent and optimizations
        rag = RAGEngine(collection_name="docs")
        results = rag.query_with_intent(query, intent, top_k=5, use_cohere_optimizations=True)

        print(f"\n   📊 RAG Results ({len(results)} docs):")
        for i, result in enumerate(results[:3], 1):  # Show top 3
            score = result.get('relevance_score', result.get('score', 0))
            title = result.get('doc_title', 'Unknown')
            content_preview = result.get('content', '')[:100]
            print(".3f")
            print(f"         \"{content_preview}...\"")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_optimization_comparison():
    """Compare results with and without Cohere optimizations"""
    print("\n" + "=" * 60)
    print("🧪 Comparing With vs Without Cohere Optimizations")
    print("=" * 60)

    rag = RAGEngine(collection_name="docs")
    query = "authentication setup"

    try:
        print(f"\n📝 Query: '{query}'")

        # Without optimizations
        print("\n   🚫 Without optimizations:")
        results_no_opt = rag.query(query, top_k=3, use_cohere_optimizations=False)
        for i, result in enumerate(results_no_opt, 1):
            score = result.get('score', 0)
            title = result.get('doc_title', 'Unknown')
            print(".3f")

        # With optimizations
        print("\n   ✅ With Cohere optimizations:")
        results_with_opt = rag.query(query, top_k=3, use_cohere_optimizations=True)
        for i, result in enumerate(results_with_opt, 1):
            score = result.get('relevance_score', result.get('score', 0))
            title = result.get('doc_title', 'Unknown')
            print(".3f")

    except Exception as e:
        print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    print("🚀 Testing Cohere Ranking Optimizations")
    print("Make sure your COHERE_API_KEY is set in .env")

    test_query_expansion()
    test_reranking()
    test_contextual_compression()
    test_full_pipeline()
    test_optimization_comparison()

    print("\n" + "=" * 60)
    print("✅ Cohere optimization tests completed!")
    print("=" * 60)
