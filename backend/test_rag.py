"""
Test script for new RAG improvements
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.journey_generator import JourneyGenerator
from services.intent_extractor import IntentExtractor
from dotenv import load_dotenv

load_dotenv()


def test_intent_extraction():
    """Test intent extraction"""
    print("=" * 60)
    print("🧪 Testing Intent Extraction")
    print("=" * 60)
    
    extractor = IntentExtractor()
    
    test_queries = [
        "I want to set up authentication with Google in React",
        "How do I configure gas sponsorship for advanced users?",
        "Create a wallet integration in Next.js"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        intent = extractor.extract_intent(query)
        print(f"   Goal: {intent.get('goal')}")
        print(f"   Complexity: {intent.get('complexity')}")
        print(f"   Platform: {intent.get('platform')}")
        print(f"   Keywords: {intent.get('keywords', [])[:3]}")


def test_rag_journey():
    """Test journey generation with RAG"""
    print("\n" + "=" * 60)
    print("🧪 Testing RAG-Powered Journey Generation")
    print("=" * 60)
    
    try:
        # Test with RAG enabled
        print("\n✅ Testing with LlamaIndex RAG...")
        generator = JourneyGenerator(use_rag=True, temperature=0.7)
        journey = generator.generate_journey(
            "I want to set up authentication",
            max_steps=5
        )
        
        if 'error' in journey:
            print(f"❌ Error: {journey['error']}")
            return
        
        print(f"\n✅ Generated Journey:")
        print(f"   Goal: {journey['goal']}")
        print(f"   Intent: {journey.get('intent', {}).get('goal', 'N/A')}")
        print(f"   Steps: {journey['total_steps']}")
        print(f"   Time: {journey['estimated_time']}")
        
        print(f"\n📋 Steps:")
        for step in journey['steps'][:3]:  # Show first 3
            print(f"   {step.get('step_number')}. {step.get('title')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to non-RAG
        print("\n⚠️  Falling back to non-RAG mode...")
        try:
            generator = JourneyGenerator(use_rag=False)
            journey = generator.generate_journey("set up authentication", max_steps=3)
            print(f"✅ Fallback worked: {journey.get('total_steps', 0)} steps")
        except Exception as e2:
            print(f"❌ Fallback also failed: {e2}")


if __name__ == "__main__":
    test_intent_extraction()
    test_rag_journey()

